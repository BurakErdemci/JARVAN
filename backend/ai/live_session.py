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

from workers.gemini_cli_worker import set_notification_queue, clear_notification_queue
from ai.wake_word import WakeWordEngine
from ai.memory_manager import MemoryManager
from ai.memory_core import get_memory_core
from ai.briefing_agent import get_briefing_agent
from datetime import datetime

from orchestration.tool_registry import (
    FUNCTION_DECLARATIONS,
    TOOL_IMPL,
    RESEARCH_HINT,
    TOOL_CONFIRMATION_HINT,
    VISION_BEHAVIOR_HINT_FALLBACK,
    VISION_BEHAVIOR_HINT_PROACTIVE,
    COMPUTER_USE_HINT,
    LEARNING_PROTOCOL_HINT,
)
from orchestration.tool_executor import ToolExecutor, ExecutorContext

MODEL_NATIVE_AUDIO = "gemini-2.5-flash-native-audio-latest"
MODEL_FLASH_LIVE = "gemini-3.1-flash-live-preview"

VISION_MODELS = ("gemini-3.1-pro", "gemini-3.1-flash-lite")
SUMMARY_MODELS = ("gemini-3.1-flash-lite", "gemini-3.1-pro")
VOICE_NAME = "Kore"
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000
INPUT_CHUNK_MS = 32
INPUT_CHUNK = int(INPUT_SAMPLE_RATE * INPUT_CHUNK_MS / 1000)
OUTPUT_COOLDOWN_S = 0.4  # Daha hızlı dinleme moduna geçiş


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
        self.playback_end_time = 0.0
        self._inflight_tools: set[str] = set()  # duplicate tool call koruması
        self._tool_cooldown: dict[str, float] = {}  # son tamamlanma zamanı
        self.is_asleep = True  # 7/24 dinleme modu için uyku durumu (Default Uyku)
        # Hafıza Yöneticisi
        self.memory_manager = MemoryManager()
        self.memory_summary = self.memory_manager.get_summary_for_prompt()
        self.last_research_result = None
        self.audio_queue = asyncio.Queue()  # Ses kuyruğu
        self.playback_end_time = 0.0
        self.full_session_transcript = []  # Otonom öğrenme için tüm oturum dökümü

        # Wake Word Motoru (Yerel)
        try:
            self.ww_engine = WakeWordEngine("models/vosk-tr", sample_rate=INPUT_SAMPLE_RATE)
        except Exception as e:
            self.on_log("error", f"WakeWord motoru başlatılamadı: {e}", None)
            self.ww_engine = None

        self.client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )

        # ToolExecutor kurulumu
        ctx = ExecutorContext(
            on_log=self.on_log,
            inflight_tools=self._inflight_tools,
            tool_cooldown=self._tool_cooldown,
            get_last_research=lambda: self.last_research_result,
            get_transcript=lambda: self.full_session_transcript,
            clear_transcript=lambda: self.full_session_transcript.clear(),
            set_asleep=lambda val: setattr(self, "is_asleep", val),
            describe_screen=self._describe_screen,
        )
        self._executor = ToolExecutor(ctx)

    async def run(self):
        active_model = MODEL_FLASH_LIVE

        # Zaman ve Hafıza Entegrasyonu (Grounding)
        now = datetime.now()
        time_context = (
            f"\n[ZAMAN FARKINDALIĞI]\n"
            f"Şu anki tarih: {now.strftime('%d %B %Y, %A')}\n"
            f"Şu anki saat: {now.strftime('%H:%M')}\n"
            f"Yıl: {now.year}\n"
        )

        # ChromaDB'den bilinçaltı hafızayı getir
        subconscious_memory = get_memory_core().get_session_context()
        memory_context = (
            f"\n[BİLİNÇALTI HAFIZA VE İÇGÖRÜLER]\n{subconscious_memory}\n"
            "\nÖNEMLİ HAFIZA KULLANIM KURALI: Bu hafıza kayıtları geçmiş deneyimlerdir — "
            "mevcut konuşmaya ait somut bilgilerle (tarih, fiyat, yer) ASLA çeliştirilmez. "
            "Kullanıcı yeni bir konu açtığında hafızadaki eski planları o konuya YÜKLEME. "
            "Örnek: Hafızada 'Barselona Temmuz planı' varken kullanıcı 'Balkan tatili' soruyorsa "
            "Barselona tarihini Balkan sorusuna uygulamak YASAK.\n"
        )

        # Başlangıç talimatlarına Zaman ve Hafıza Özetini ekle
        system_instruction = (
            time_context
            + memory_context
            + "\n" + self.system_prompt
            + "\n\n" + self.memory_summary
            + "\n\n[UYKU MODU KURALLARI]\n"
            "Sen 7/24 uyanık kalabilen bir asistansın. Kullanıcı 'uyu', 'kendini kapat', 'hoşçakal', 'dinlenmeye geç' gibi veda cümleleri kurarsa "
            "mutlaka `sleep_mode()` aracını çağır. Uyumadan önce kullanıcıya çok kısa ve net şekilde veda et "
            "(Örn: 'Tamamdır kendimi kapatıyorum, hoşçakal.'). Sakın veda ederken 'beni uyandır', 'uyan de' gibi tetikleyici kelimeleri KULLANMA. "
            "Uyku modundayken sesin Gemini'ye gitmeyecek, sadece yerel olarak 'Uyan' demeni bekleyeceğim."
            + (VISION_BEHAVIOR_HINT_PROACTIVE if self.send_video else VISION_BEHAVIOR_HINT_FALLBACK)
            + TOOL_CONFIRMATION_HINT
            + RESEARCH_HINT
            + COMPUTER_USE_HINT
            + LEARNING_PROTOCOL_HINT
            + "\n\n[SPOTIFY İPUCU]\n"
            "Kullanıcı 'bunun adı ne bilmiyom playlistimi çal' gibi tuhaf cümleler kurabilir. "
            "Bu cümlelerin içindeki 'bunun adı ne bilmiyom' ifadesi aslında çalma listesinin gerçek adıdır. "
            "Bu tarz durumları bir kafa karışıklığı sanma ve kullanıcının belirttiği ismi aynen `track` parametresine yaz."
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
                {"function_declarations": FUNCTION_DECLARATIONS},
            ],
        }

        try:
            async with self.client.aio.live.connect(model=active_model, config=config) as session:
                self.on_log("system", f"Live bağlandı ({active_model}) — ses: {VOICE_NAME}.", None)
                if self.is_asleep:
                    self.on_log("system", "Jarvan 7/24 dinleme modunda. 'Uyan' diyerek uyandırabilirsin.", None)

                notification_queue = asyncio.Queue()
                set_notification_queue(notification_queue)

                # Dosya transfer bildirimleri için callback bağla
                from tools.device_transfer import set_incoming_callback
                async def _on_transfer(path, manifest):
                    from_dev = manifest.get("from", "diğer cihaz")
                    fname = manifest.get("file", path.name)
                    msg_txt = manifest.get("message", "")
                    size_kb = manifest.get("size_kb", 0)
                    delivered = manifest.get("delivered_to", "")
                    note = f" Not: {msg_txt}" if msg_txt else ""
                    location = f" İndirmeler/Jarvan klasörüne kaydedildi." if delivered else ""
                    await session.send(
                        input=(
                            f"[SİSTEM: {from_dev}'dan '{fname}' dosyası geldi ({size_kb} KB).]{note}{location}\n"
                            f"Kullanıcıya bunu doğal ve kısa bir şekilde sesli bildir."
                        ),
                        end_of_turn=True,
                    )
                set_incoming_callback(_on_transfer)

                # Briefing arka planda hazırla — "Uyan" gelince hazır olsun
                asyncio.create_task(get_briefing_agent().prefetch())

                tasks = [
                    asyncio.create_task(self._mic_loop(session)),
                    asyncio.create_task(self._receive_loop(session)),
                    asyncio.create_task(self._stop_watcher()),
                    asyncio.create_task(self._notification_loop(session, notification_queue)),
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
        finally:
            clear_notification_queue()

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
                loop_start = time.monotonic()
                data = await asyncio.to_thread(stream.read, INPUT_CHUNK, False)

                # --- Wake Word / Sleep Logic ---
                if self.is_asleep:
                    if self.ww_engine:
                        result = self.ww_engine.process_data(data)
                        if result == "uyan":
                            self.on_log("system", "Wake Word yakalandı: UYAN!", None)
                            self.is_asleep = False
                            try:
                                # Cache'den anlık al — prefetch session açılınca yapıldı
                                briefing = get_briefing_agent().get_cached()

                                if briefing:
                                    wake_msg = (
                                        f"Kullanıcı seni 'Uyan' diyerek uyandırdı. "
                                        f"Önce 'Selam Burak!' diye selamla, "
                                        f"ardından şu brifing maddelerini doğal bir dille söyle:\n{briefing}"
                                    )
                                    self.on_log("system", "Brifing var, enjekte ediliyor.", None)
                                else:
                                    wake_msg = "Kullanıcı seni 'Uyan' diyerek uyandırdı. Sadece 'Selam Burak, nasıl yardımcı olabilirim?' diyerek onu karşıla."

                                await session.send_realtime_input(text=wake_msg)
                            except Exception as e:
                                self.on_log("error", f"Selam tetikleme hatası (devam ediliyor): {e}", None)
                    continue # Uyku modundayken sesi buluta gönderme

                if self.is_speaking or (time.monotonic() - self.last_output_time < OUTPUT_COOLDOWN_S):
                    continue

                # --- Lag Monitoring ---
                loop_end = time.monotonic()
                
                # Sesi gönderirken mic döngüsünü (PyAudio buffer) bloklamamak için asenkron task kullanıyoruz
                # Böylece ses girişinde veya çıkışında takılma (kayma) engellenir.
                asyncio.create_task(session.send_realtime_input(
                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}")
                ))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Mic loop: {e}", None)
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

    async def _playback_loop(self, out_stream):
        """Sesi arka planda kuyruktan çeker ve hoparlöre gönderir (Bloklamaz)."""
        try:
            while not self.should_stop():
                audio_data = await self.audio_queue.get()
                if audio_data:
                    self.is_speaking = True
                    self.last_output_time = time.monotonic()
                    # Sesi parçalar halinde yaz
                    await asyncio.to_thread(out_stream.write, audio_data)
                    self.audio_queue.task_done()

                    # Kuyruk boşaldıysa ve ses bittiyse sessizliğe dön (Echo Prevention)
                    if self.audio_queue.empty():
                        await asyncio.sleep(0.3)  # Kısa bir tampon bekleme
                        if self.audio_queue.empty():
                            self.is_speaking = False
        except Exception as e:
            self.on_log("error", f"Playback loop hatası: {e}", None)

    async def _receive_loop(self, session):
        p = pyaudio.PyAudio()
        out_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
        )
        # Ses oynatma döngüsünü başlat
        playback_task = asyncio.create_task(self._playback_loop(out_stream))

        in_buf = ""
        out_buf = ""
        try:
            while not self.should_stop():
                async for response in session.receive():
                    if self.should_stop():
                        break

                    if response.data:
                        # Sesi kuyruğa at, bekleme!
                        await self.audio_queue.put(response.data)

                    tc = getattr(response, "tool_call", None)
                    if tc and getattr(tc, "function_calls", None):
                        # Gecikme YOK! Aracı hemen çalıştır.
                        # Mikrofon zaten is_speaking yüzünden playback_loop tarafından kapalı tutuluyor.
                        task = asyncio.create_task(self._handle_tool_calls(session, tc.function_calls))
                        task.add_done_callback(
                            lambda t: self.on_log("error", f"tool task hata: {t.exception()}", None)
                            if not t.cancelled() and t.exception() else None
                        )
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
                            self.full_session_transcript.append(f"Kullanıcı: {user_text}")
                            in_buf = ""
                        if out_buf.strip():
                            import re
                            clean_out = re.sub(r"<ctrl\d+>", "", out_buf).strip()
                            if clean_out:
                                self.on_log("jarvan", clean_out, "live")
                                self.full_session_transcript.append(f"JARVAN: {clean_out}")
                            out_buf = ""

                    if getattr(sc, "interrupted", False):
                        self.is_speaking = False
                        self.last_output_time = time.monotonic()
                        if out_buf.strip():
                            import re
                            clean_out = re.sub(r"<ctrl\d+>", "", out_buf).strip()
                            if clean_out:
                                self.on_log("jarvan", clean_out + " …", "live")
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
        return await self._executor.handle(function_calls, session)

    async def _notification_loop(self, session, queue: asyncio.Queue) -> None:
        """Gemini CLI işleri bitince Jarvan'a otomatik bildirir."""
        try:
            while True:
                notif = await queue.get()
                job_id = notif["job_id"]
                status = notif["status"]
                content = notif["content"]

                if self.is_asleep:
                    # Uyku modunda sessizce logla, konuşma
                    self.on_log("system", f"[gemini_cli] {job_id} bitti ({status}) — Jarvan uyuyor, bildirim bekliyor.", None)
                    continue

                self.on_log("system", f"[gemini_cli] {job_id} bitti, Jarvan'a bildiriliyor.", None)

                if status == "done":
                    # Sonucun ilk 800 karakterini ver, geri kalanı varsa belirt
                    preview = content[:800]
                    overflow = f"\n(Toplam {len(content)} karakter, ilk 800 gösterildi.)" if len(content) > 800 else ""
                    msg = (
                        f"[SİSTEM: Arka plan görevi '{job_id}' tamamlandı.]\n"
                        f"Kullanıcıya sonucu doğal bir şekilde sesli olarak özetle. "
                        f"'Görevin bitti' veya 'Tamamlandı' ile başla.\n"
                        f"Sonuç:\n{preview}{overflow}"
                    )
                else:
                    msg = (
                        f"[SİSTEM: Arka plan görevi '{job_id}' hata ile sonuçlandı.]\n"
                        f"Kullanıcıya kısaca hata olduğunu söyle.\n"
                        f"Hata: {content[:300]}"
                    )

                try:
                    await session.send(input=msg, end_of_turn=True)
                except Exception as e:
                    self.on_log("error", f"Bildirim gönderilemedi: {e}", None)

        except asyncio.CancelledError:
            pass

    async def _describe_screen(self) -> str:
        from screen.capture import capture_screenshot_pil

        self.on_log("system", "Ekran analiz ediliyor…", None)
        img = await asyncio.to_thread(capture_screenshot_pil)
        img.thumbnail((720, 720))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=75)
        jpeg = buf.getvalue()

        prompt = (
            "Ekranda net görüneni 2-3 cümle teknik Türkçe özetle. "
            "Spekülasyon yok, sadece görülen. Araç/pencere adı, hata mesajı, "
            "kod veya UI elementi varsa belirt."
        )

        vision_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
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
                    config=vision_config,
                )
                description = (response.text or "").strip()
                if description:
                    break
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if any(t in msg for t in ("quota", "429", "exhausted", "rate", "503", "unavailable", "overload")):
                    continue
                raise

        if not description:
            self.on_log("error", f"Vision başarısız: {last_err}", None)
            return ""

        self.on_log("system", f"[ekran] {description}", None)
        return description

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
