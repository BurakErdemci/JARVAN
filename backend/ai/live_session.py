"""Gemini Live — native audio dialog + on-demand ekran analizi."""
import asyncio
import io
import os
import re
import sys
import time
from typing import Callable

import pyaudio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

from google import genai
from google.genai import types

from tools.app_control import open_app, close_app
from tools.whatsapp import send_whatsapp

FUNCTION_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Kullanıcının bilgisayarında bir uygulamayı veya oyunu açar. Örnek: 'not defteri aç', 'chrome aç', 'CS2 aç'.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Açılacak uygulamanın adı (not defteri, chrome, vscode, cs2, spotify vb.)",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "close_app",
        "description": "Açık bir uygulamayı kapatır. Örnek: 'chrome kapat', 'spotify kapat'.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Kapatılacak uygulamanın adı",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "send_whatsapp",
        "description": "Kullanıcının WhatsApp'ından kendisine veya belirtilen numaraya mesaj gönderir. Numara verilmezse .env'deki MY_WHATSAPP'a gider.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Gönderilecek mesaj metni",
                },
                "phone": {
                    "type": "string",
                    "description": "İsteğe bağlı hedef numara (ülke koduyla, + olmadan). Boş bırakılırsa kendine gider.",
                },
            },
            "required": ["message"],
        },
    },
]

TOOL_IMPL = {
    "open_app": lambda args: open_app(args.get("name", "")),
    "close_app": lambda args: close_app(args.get("name", "")),
    "send_whatsapp": lambda args: send_whatsapp(args.get("message", ""), args.get("phone")),
}

MODEL_NATIVE_AUDIO = "gemini-2.5-flash-native-audio-latest"
MODEL_FLASH_LIVE = "gemini-3.1-flash-live-preview"

VISION_MODELS = ("gemini-3.1-flash-lite-preview", "gemini-3-flash-preview")
VOICE_NAME = "Kore"
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
INPUT_CHUNK_MS = 32
INPUT_CHUNK = int(INPUT_SAMPLE_RATE * INPUT_CHUNK_MS / 1000)
OUTPUT_COOLDOWN_S = 0.8  # Jarvan konuşurken + bittikten sonra kısa sessizlik (Yankıyı engellemek için 0.8'e çıkarıldı)

VISION_TRIGGER_RE = re.compile(
    r"\b(bak\w*|gör\w*|ekran\w*|şurd[ae]|şurad[ae]|burd[ae]|burad[ae])\b",
    re.IGNORECASE,
)

TOOL_CONFIRMATION_HINT = (
    "\n\n[ARAÇ KULLANIM KURALLARI]\n"
    "- `open_app` ve `close_app`: düşük riskli, doğrudan çağırabilirsin.\n"
    "- `send_whatsapp` VE dış dünyaya görünen her türlü aksiyon: ÖNCE ONAY AL. "
    "Önce 'X numarasına (veya kendine) şu mesajı atıyorum: \"...\" — onaylıyor musun?' diye net bir cümle kur. "
    "Kullanıcı 'evet', 'tamam', 'at', 'gönder', 'onaylıyorum' gibi NET onay vermeden aracı ÇAĞIRMA. "
    "'Belki', 'bilmiyorum', 'şey' gibi belirsiz cevaplar → tekrar sor.\n"
    "- Kullanıcı 'iptal', 'dur', 'boşver' derse aracı çağırma, kısaca 'tamam iptal ettim' de."
)

VISION_BEHAVIOR_HINT_FALLBACK = (
    "\n\n[ÇOK ÖNEMLİ] Kullanıcının ekranını saniye saniye GÖREMİYORSUN. "
    "Kullanıcı 'ekranda ne var?' diye sorduğunda mekaniğin ekran fotoğrafı çekmesi 2-3 saniye sürer. "
    "Bu yüzden ZAMAN KAZANMAK adına SADECE 'Hemen bakıyorum...' veya 'Bir saniye...' gibi çok kısa bir şey söyle ve anında SUS (Cümleyi bitir ki mekanik sana fotoğrafı ulaştırabilsin). "
    "ASLA o an sallayarak (tahmin yürüterek) ekranda ne olduğunu anlatmaya çalışma! "
    "Kısa bir süre sonra sana [Gizli Sistem Bildirimi] içinde ekranın metni ulaştığında doğrudan 'Ekranda şu an ... görüyorum' diyerek oradan oku."
)

VISION_BEHAVIOR_HINT_PROACTIVE = (
    "\n\n[ÇOK ÖNEMLİ] ŞU ANDA ekrana 1 FPS hızında SÜREKLİ VİDEO YAYINI İLE bağlanmış durumdasın. Kullanıcının bilgisayar ekranını saniye saniye canlı izliyorsun! "
    "Eğer kullanıcı 'şu animasyon bozuk mu?' veya 'ekranımda ne görüyorsun' gibi bir şey sorarsa, hemen o saniye ne görüyorsan söyle. Ekstra bir bekleme veya fotoğraf çekme kuralı yok, doğrudan gördüğünden bahset."
)


class LiveSession:
    def __init__(
        self,
        system_prompt: str,
        on_log: Callable[[str, str, str | None], None],
        should_stop: Callable[[], bool],
        send_video: bool = False,
        conversation_memory: list[dict] = None,
    ):
        self.system_prompt = system_prompt
        self.on_log = on_log
        self.should_stop = should_stop
        self.send_video = send_video
        self.conversation_memory = conversation_memory or []
        self.last_output_time = 0.0
        self.is_speaking = False
        self.vision_in_flight = False
        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )

    async def run(self):
        active_model = MODEL_FLASH_LIVE if self.send_video else MODEL_NATIVE_AUDIO
        system_instruction = (
            self.system_prompt
            + (VISION_BEHAVIOR_HINT_PROACTIVE if self.send_video else VISION_BEHAVIOR_HINT_FALLBACK)
            + TOOL_CONFIRMATION_HINT
        )
        
        if self.conversation_memory:
            mem_text = "\n".join([f"{m['role']}: {m['text']}" for m in self.conversation_memory])
            system_instruction += (
                "\n\n[ÇOK ÖNEMLİ - GEÇMİŞ SOHBET HAFIZAN]\n"
                "Kullanıcı UI üzerinden geçiş veya mod değişikliği yaptığı için bağlantın saniyeler önce resetlendi. Ancak sohbet kesintisiz devam ediyor. "
                "İşte yeniden bağlanmadan önceki son konuşmalarınızın dökümü. Doğrudan bu konuşmanın devamıymış gibi davran, kendini baştan tanıtma:\n"
                f"{mem_text}\n"
                "-----------------------------------\n\n"
            )

        config = {
            "response_modalities": ["AUDIO"],
            "system_instruction": system_instruction,
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": VOICE_NAME}
                },
                "language_code": "tr-TR",
            },
            "input_audio_transcription": {},
            "output_audio_transcription": {},
            "tools": [
                {"google_search": {}},
                {"function_declarations": FUNCTION_DECLARATIONS},
            ],
        }

        try:
            async with self.client.aio.live.connect(model=active_model, config=config) as session:
                self.on_log("system", f"Live bağlandı ({active_model}) — ses: {VOICE_NAME}.", None)

                tasks = [
                    asyncio.create_task(self._mic_loop(session)),
                    asyncio.create_task(self._receive_loop(session)),
                    asyncio.create_task(self._stop_watcher()),
                ]
                
                if self.send_video:
                    tasks.append(asyncio.create_task(self._video_loop(session)))

                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for t in pending:
                    t.cancel()
                for t in pending:
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass
        except Exception as e:
            self.on_log("error", f"Live hatası: {e}", None)

    async def _stop_watcher(self):
        while not self.should_stop():
            await asyncio.sleep(0.1)

    async def _mic_loop(self, session):
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=INPUT_CHUNK,
        )
        try:
            while not self.should_stop():
                data = await asyncio.to_thread(stream.read, INPUT_CHUNK, False)
                if self.is_speaking or (time.monotonic() - self.last_output_time < OUTPUT_COOLDOWN_S):
                    continue
                await session.send_realtime_input(
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}")
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Mic loop: {e}", None)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

    async def _receive_loop(self, session):
        p = pyaudio.PyAudio()
        out_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
        )
        in_buf = ""
        out_buf = ""
        try:
            while not self.should_stop():
                async for response in session.receive():
                    if self.should_stop():
                        break

                    if response.data:
                        self.is_speaking = True
                        self.last_output_time = time.monotonic()
                        await asyncio.to_thread(out_stream.write, response.data)
                        self.last_output_time = time.monotonic()

                    tc = getattr(response, "tool_call", None)
                    if tc and getattr(tc, "function_calls", None):
                        await self._handle_tool_calls(session, tc.function_calls)
                        continue

                    sc = getattr(response, "server_content", None)
                    if sc is None:
                        continue

                    it = getattr(sc, "input_transcription", None)
                    if it and getattr(it, "text", None):
                        in_buf += it.text

                    ot = getattr(sc, "output_transcription", None)
                    if ot and getattr(ot, "text", None):
                        out_buf += ot.text

                    if getattr(sc, "turn_complete", False):
                        self.is_speaking = False
                        self.last_output_time = time.monotonic()
                        user_text = in_buf.strip()
                        if user_text:
                            self.on_log("user", user_text, None)
                            in_buf = ""
                            if (not self.send_video) and VISION_TRIGGER_RE.search(user_text):
                                asyncio.create_task(self._probe_vision(session, user_text))
                        if out_buf.strip():
                            self.on_log("jarvan", out_buf.strip(), "live")
                            out_buf = ""

                    if getattr(sc, "interrupted", False):
                        self.is_speaking = False
                        self.last_output_time = time.monotonic()
                        if out_buf.strip():
                            self.on_log("jarvan", out_buf.strip() + " …", "live")
                            out_buf = ""
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Receive loop: {e}", None)
        finally:
            if in_buf.strip():
                self.on_log("user", in_buf.strip(), None)
            if out_buf.strip():
                self.on_log("jarvan", out_buf.strip(), "live")
            out_stream.stop_stream()
            out_stream.close()
            p.terminate()

    async def _handle_tool_calls(self, session, function_calls):
        responses = []
        for fc in function_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            impl = TOOL_IMPL.get(name)
            if impl is None:
                result = {"ok": False, "error": f"bilinmeyen tool: {name}"}
            else:
                self.on_log("system", f"[tool] {name}({args})", None)
                try:
                    result = await asyncio.to_thread(impl, args)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                self.on_log("system", f"[tool sonuç] {result}", None)

            responses.append(types.FunctionResponse(
                id=fc.id,
                name=name,
                response=result,
            ))

        await session.send_tool_response(function_responses=responses)

    async def _probe_vision(self, session, user_text: str):
        if self.vision_in_flight:
            return
        self.vision_in_flight = True
        try:
            from screen.capture import capture_screenshot_pil

            self.on_log("system", "Ekran analiz ediliyor…", None)
            img = await asyncio.to_thread(capture_screenshot_pil)
            img.thumbnail((1280, 1280))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=80)
            jpeg = buf.getvalue()

            prompt = (
                f'Kullanıcı şunu söyledi: "{user_text}". '
                "Ekranda net görüneni 2-3 cümle teknik Türkçe özetle. "
                "Spekülasyon yok, sadece görülen. Araç/pencere adı, hata mesajı, "
                "kod veya UI elementi varsa belirt."
            )

            description = ""
            last_err: Exception | None = None
            for model in VISION_MODELS:
                try:
                    response = await self.client.aio.models.generate_content(
                        model=model,
                        contents=[
                            types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
                            prompt,
                        ],
                    )
                    description = (response.text or "").strip()
                    if description:
                        break
                except Exception as e:
                    last_err = e
                    msg = str(e).lower()
                    if "quota" in msg or "429" in msg or "exhausted" in msg or "rate" in msg:
                        continue
                    raise

            if not description:
                self.on_log("error", f"Vision başarısız: {last_err}", None)
                return

            self.on_log("system", f"[ekran] {description}", None)

            await session.send_client_content(
                turns=[{
                    "role": "user",
                    "parts": [{
                        "text": f"[Gizli Sistem Bildirimi: Gözlerinle az önce şunları gördün: '{description}'] Lütfen az önce sorulan soruya doğrudan bu gördüklerini söylüyormuşçasına ('Ekranda ... var' şeklinde) cevap ver. Sana fotoğraf yollandığını vs söyleme."
                    }],
                }],
                turn_complete=True,
            )
        except Exception as e:
            self.on_log("error", f"Vision probe: {e}", None)
        finally:
            self.vision_in_flight = False

    async def _video_loop(self, session):
        try:
            from screen.capture import capture_screenshot_pil
            self.on_log("system", "Gerçek zamanlı ekran yayını (1 FPS) başladı.", None)
            while not self.should_stop():
                img = await asyncio.to_thread(capture_screenshot_pil)
                
                # Çözünürlüğü çok büyütmemek lazım, 2 FPS olduğu için ağa bindirmesin
                img.thumbnail((720, 720))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=60)
                jpeg = buf.getvalue()

                await session.send_realtime_input(
                    video=types.Blob(mime_type="image/jpeg", data=jpeg)
                )
                
                await asyncio.sleep(1.0)  # Canlı akış = Saniyede 1 kare (1 FPS)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Video loop: {e}", None)
