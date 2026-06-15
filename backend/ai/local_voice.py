"""LocalVoiceSession — %100 local sesli döngü. Gemini Live'ın yerini alır.

Akış:  Mikrofon → (wake word) → Whisper STT → Gemma (tool-calling) →
        [ToolExecutor | start_gemini_task=CLI dispatch] → Kokoro TTS → Hoparlör

Gemini Live'dan FARKI: ses buluta gitmez. Kulak=faster-whisper, beyin=Gemma(Ollama),
ağız=Kokoro — hepsi gömülü. Mevcut tool sistemi (tool_registry + ToolExecutor) ve
worker (start_gemini_task) AYNEN yeniden kullanılır — Gemma sadece Gemini'nin yerine
function-caller olur. Jarvan TR+EN anlar, HER ZAMAN İngilizce konuşur.

Pipeline (main.py) LiveSession ile aynı arayüzle çağırır:
    LocalVoiceSession(system_prompt, on_log, should_stop, send_video, conversation_memory).run()
"""

from __future__ import annotations

import asyncio
import functools
import json
import threading
import time
from typing import Callable

import numpy as np
import pyaudio

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_MS,
    VOICE_SILENCE_MS, VOICE_RMS_GATE, WAKE_WORD, VOSK_MODEL_PATH, UNLOAD_ON_SLEEP,
)
from ai.gemma_brain import GemmaBrain, GemmaError
from ai.voice_stt import stt
from ai.voice_tts import tts
from ai.wake_word import WakeWordEngine
from orchestration.tool_registry import FUNCTION_DECLARATIONS
from orchestration.tool_executor import ToolExecutor, ExecutorContext
from workers.gemini_cli_worker import set_notification_queue, clear_notification_queue

CHUNK = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)  # 512 @ 16kHz/32ms

# Endpointing (enerji tabanlı, silero yok — bağımlılıksız). Ayarlar config/.env'den.
RMS_GATE = VOICE_RMS_GATE      # int16 RMS — üstü konuşma sayılır
SILENCE_MS = VOICE_SILENCE_MS  # konuşmadan sonra bu kadar sessizlik → cümle bitti
MAX_UTTER_MS = 20000           # tek cümle üst sınırı
MAX_TOOL_ROUNDS = 5     # tool→sonuç→tekrar Gemma döngüsü limiti

SYSTEM_PROMPT = """You are Jarvan, the user's JARVIS-style local AI butler.
The user (Burak) may speak Turkish OR English — you understand both perfectly.

HARD RULES:
- ALWAYS reply in ENGLISH, even if the user spoke Turkish. Never answer in Turkish.
- Be concise, calm, lightly witty (a JARVIS butler). Spoken aloud — keep it short.
- PLAIN SPOKEN TEXT ONLY: no emojis, no markdown (* _ # ` -), no bullet lists, no symbols.
  Write as you would speak. When listing things, say them in a natural sentence.
- For heavy work call `start_gemini_task` with a clear English task and pick the right
  `target` brain, then tell the user you started it:
  - target="gpt" (Codex): precise coding, bug fixing, writing tests, terminal work. DEFAULT for code.
  - target="gemini" (agy): current news/prices, web research, long-document or multimodal analysis.
  - target="claude": big multi-file refactor, architecture, understanding a whole codebase (paid/experimental — only when truly needed).
  Rule of thumb: code → gpt, research/news → gemini. When unsure, use gpt.
- CRITICAL — never fake a dispatch: to start a background task you MUST actually emit the
  `start_gemini_task` tool call THIS turn. NEVER say "I started/initiated/engaged/tasked"
  an agent in words without the real tool call in the same turn. If the user asks for
  several tasks at once, emit ONE `start_gemini_task` tool call per task in this turn
  (e.g. an architecture task → target="claude" AND a research task → target="gemini").
  Only after the tool calls may you tell the user you started them.
- For real-time/system facts (weather, screen, files, mail, spotify…) call the matching
  tool. Never invent live data.
- For chat, greetings, quick reasoning → just answer in English. No tool needed.
- When you call a tool, do not narrate the mechanics; speak naturally about the result.
- SLEEP: if the user says they want you to sleep / stop / goodbye (Turkish: "uyu",
  "uyuyabilirsin", "kendini kapat", "dinlen", "hoşçakal"; English: "go to sleep",
  "sleep now", "that's all"), you MUST call the `sleep_mode` tool. Say a short English
  farewell first (e.g. "Going to sleep, sir."), then call sleep_mode.
- MUSIC (Spotify): pass the song/playlist name EXACTLY as the user said it — do NOT
  translate, correct, or guess spelling. Put the artist name in the `artist` field and
  only the song name in `track` (e.g. user: "Model'in Pembe Mezarlık şarkısı" →
  track="Pembe Mezarlık", artist="Model"). If the tool says it couldn't match, ask the
  user to clarify the name instead of insisting.
"""


def _ollama_tools() -> list[dict]:
    """tool_registry'nin Gemini-format şemalarını Ollama tool formatına çevirir."""
    return [
        {"type": "function", "function": {
            "name": d["name"],
            "description": d.get("description", ""),
            "parameters": d.get("parameters", {"type": "object", "properties": {}}),
        }}
        for d in FUNCTION_DECLARATIONS
    ]


class LocalVoiceSession:
    def __init__(
        self,
        system_prompt: str = "",        # Pipeline mod-promptu geçer; biz İngilizce-çıkış promptumuzu kullanırız
        on_log: Callable[[str, str, str | None], None] = lambda *a: None,
        should_stop: Callable[[], bool] = lambda: False,
        send_video: bool = False,
        conversation_memory: list[dict] | None = None,
        is_muted: Callable[[], bool] = lambda: False,
        on_task: Callable[[dict], None] = lambda t: None,
    ) -> None:
        self.on_log = on_log
        self.should_stop = should_stop
        self.is_muted = is_muted
        self.on_task = on_task
        self.conversation_memory = conversation_memory or []
        self._respond_lock = asyncio.Lock()  # mic + chatbox aynı anda _respond çağırmasın
        self.is_asleep = True
        self.is_speaking = False
        self._pending_unload = False  # uyku: veda bitince boşalt (hemen değil)
        self._inflight: set[str] = set()
        self._cooldown: dict[str, float] = {}
        self.brain = GemmaBrain()
        self.tools = _ollama_tools()
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Wake word (Vosk, config'den: varsayılan "wake up" + İngilizce model).
        # Model yoksa uyanık başla (sürekli dinleme — graceful fallback).
        try:
            self.ww = WakeWordEngine(VOSK_MODEL_PATH, sample_rate=AUDIO_SAMPLE_RATE, wake_word=WAKE_WORD)
        except Exception as e:
            self.on_log("error", f"WakeWord başlatılamadı ({VOSK_MODEL_PATH}), uyanık başlanıyor: {e}", None)
            self.ww = None
            self.is_asleep = False

        # ToolExecutor — Gemini'siz, see_screen local modda degrade.
        ctx = ExecutorContext(
            on_log=self.on_log,
            inflight_tools=self._inflight,
            tool_cooldown=self._cooldown,
            get_last_research=lambda: None,
            get_transcript=lambda: [],
            clear_transcript=lambda: None,
            set_asleep=self._set_asleep,
            describe_screen=self._describe_screen,
        )
        self._executor = ToolExecutor(ctx)

    async def _describe_screen(self) -> str:
        """Ekran görüntüsü → gemma4 vision (local). 'Jarvan şuna bak' için."""
        import io
        from screen.capture import capture_screenshot_pil
        self.on_log("system", "Ekran analiz ediliyor (gemma vision)…", None)

        def _cap_and_ask() -> str:
            img = capture_screenshot_pil()
            img.thumbnail((1024, 1024))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=80)
            prompt = (
                "Describe what is on this screen in 2-3 short English sentences. "
                "Mention app/window names, error messages, code or UI elements if visible. "
                "Only state what you actually see — do not guess."
            )
            return self.brain.describe_image(buf.getvalue(), prompt)

        try:
            desc = await asyncio.to_thread(_cap_and_ask)
        except Exception as e:
            self.on_log("error", f"Ekran analizi hatası: {e}", None)
            return ""
        if desc:
            self.on_log("system", f"[ekran] {desc}", None)
        return desc

    # ─── Ana döngü ──────────────────────────────────────────────────
    async def run(self) -> None:
        # Modelleri arka planda ısıt (ilk cevapta gecikme olmasın)
        asyncio.create_task(asyncio.to_thread(self._warmup))

        if not self.brain.health():
            self.on_log("error", "Ollama/Gemma erişilemiyor — `ollama serve` çalışıyor mu?", None)

        notif_q: asyncio.Queue = asyncio.Queue()
        set_notification_queue(notif_q)
        notif_task = asyncio.create_task(self._notification_loop(notif_q))

        pa = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt16, channels=AUDIO_CHANNELS,
                         rate=AUDIO_SAMPLE_RATE, input=True, frames_per_buffer=CHUNK)
        self.on_log("system", f"Local sesli döngü hazır. '{WAKE_WORD}' diyerek başlat." if self.is_asleep
                    else "Local sesli döngü hazır (uyanık).", None)
        try:
            while not self.should_stop():
                if self.is_muted():
                    await asyncio.sleep(0.1)
                    continue
                if self.is_asleep:
                    await self._listen_for_wake(stream)
                    continue
                pcm = await asyncio.to_thread(self._record_utterance, stream)
                if not pcm or self.should_stop():
                    continue
                text = await asyncio.to_thread(stt.transcribe_pcm, pcm)
                if not text:
                    continue
                self.on_log("user", text, None)
                await self._respond(text)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.on_log("error", f"Local voice döngü hatası: {e}", None)
        finally:
            notif_task.cancel()
            clear_notification_queue()
            stream.stop_stream(); stream.close(); pa.terminate()

    def _warmup(self) -> None:
        # STT + TTS hep ısınsın (hafif, uyandığında anında lazım).
        try:
            stt.warmup()
            tts.warmup()
        except Exception as e:
            self.on_log("error", f"STT/TTS ısıtma hatası: {e}", None)
        # Beyin (ağır): uykuda boşalt-modunda uyanık değilsek YÜKLEME — ilk 'wake up'ta
        # yüklenecek. Uyanık başlıyorsak (wake word yok) hemen ısıt.
        if not (self.is_asleep and UNLOAD_ON_SLEEP):
            self._warm_brain()

    def _warm_brain(self) -> None:
        """Gemma'yı num_ctx=8192 + tool'larla yükle (Ollama'ya resident yap)."""
        try:
            self.brain.chat([{"role": "user", "content": "hi"}], tools=self.tools)
        except Exception as e:
            self.on_log("error", f"Beyin yükleme hatası: {e}", None)

    def _set_asleep(self, val: bool) -> None:
        """sleep_mode tool'u buraya bağlı. Boşaltmayı HEMEN yapma — önce veda + işlem
        bitsin; tur sonunda (_respond_inner sonu) boşalt. Yoksa veda için Gemma yeniden
        yüklenir (~8.6s), takılmış gibi olur."""
        self.is_asleep = bool(val)
        if val and UNLOAD_ON_SLEEP:
            self._pending_unload = True

    # ─── Wake word ──────────────────────────────────────────────────
    async def _listen_for_wake(self, stream) -> None:
        data = await asyncio.to_thread(stream.read, CHUNK, False)
        if self.ww is None:
            self.is_asleep = False
            return
        if self.ww.process_data(data):
            self.is_asleep = False
            self.on_log("system", f"Wake word: {WAKE_WORD.upper()}!", None)
            # Beyni arka planda yükle (uykuda boşaltıldıysa) — greeting çalarken hazırlanır.
            if UNLOAD_ON_SLEEP:
                asyncio.create_task(asyncio.to_thread(self._warm_brain))
            greeting = "Good evening, sir. How may I assist you?"
            self.on_log("jarvan", greeting, "local")
            await asyncio.to_thread(self._speak, greeting)

    # ─── Utterance yakalama (enerji endpointing) ────────────────────
    def _record_utterance(self, stream) -> bytes:
        frames: list[bytes] = []
        silence_run = 0.0
        spoke = False
        elapsed = 0.0
        chunk_ms = AUDIO_CHUNK_MS
        while elapsed < MAX_UTTER_MS:
            if self.should_stop() or self.is_muted():
                break
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            elapsed += chunk_ms
            rms = _rms_int16(data)
            if rms >= RMS_GATE:
                spoke = True
                silence_run = 0.0
            elif spoke:
                silence_run += chunk_ms
                if silence_run >= SILENCE_MS:
                    break
            else:
                # henüz konuşma yok — baştaki sessizliği biriktirme (buffer şişmesin)
                if len(frames) > 20:
                    frames.pop(0)
        return b"".join(frames) if spoke else b""

    # ─── Gemma + tool döngüsü ───────────────────────────────────────
    async def _respond(self, user_text: str) -> None:
        async with self._respond_lock:
            await self._respond_inner(user_text)

    async def _respond_inner(self, user_text: str) -> None:
        self.messages.append({"role": "user", "content": user_text})
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                msg = await asyncio.to_thread(
                    functools.partial(self.brain.chat, self.messages, tools=self.tools))
                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    self.messages.append({
                        "role": "assistant",
                        "content": msg.get("content", ""),
                        "tool_calls": tool_calls,
                    })
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        args = fn.get("arguments", {}) or {}
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except Exception:
                                args = {}
                        result = await self._executor.execute_one(name, args)
                        self.messages.append({
                            "role": "tool",
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                        self._maybe_emit_task(name, args, result)
                    continue  # tool sonuçlarıyla Gemma'ya tekrar dön (özetlesin)
                answer = (msg.get("content") or "").strip()
                if answer:
                    self.messages.append({"role": "assistant", "content": answer})
                    self.on_log("jarvan", answer, "local")
                    await asyncio.to_thread(self._speak, answer)
                break
        except GemmaError as e:
            self.on_log("error", f"Gemma hatası: {e}", None)
        # Bağlam şişmesin: son ~20 mesajı tut (system hariç)
        if len(self.messages) > 21:
            self.messages = [self.messages[0]] + self.messages[-20:]

        # Uyku istendiyse: tüm cevap/veda söylendi → ŞİMDİ Gemma'yı boşalt.
        if self._pending_unload:
            self._pending_unload = False
            self.on_log("system", "Uyku — Gemma boşaltılıyor, RAM/VRAM serbest.", None)
            threading.Thread(target=self.brain.unload, daemon=True).start()

    def _maybe_emit_task(self, name: str, args: dict, result: dict) -> None:
        """Arka plan CLI işi (start_gemini_task) başlayınca task panelini bilgilendir."""
        if name != "start_gemini_task" or not isinstance(result, dict):
            return
        job_id = result.get("job_id")
        if not job_id:
            return
        title = (args.get("prompt", "") or "").strip().splitlines()[0][:60] or "Arka plan görevi"
        # Hangi beyin: gpt(Codex) | gemini(agy) | claude — panelde göster.
        target = (args.get("target") or "gpt").lower()
        target_label = {"gpt": "codex", "gemini": "agy", "claude": "claude"}.get(target, target)
        self.on_task({
            "id": job_id,
            "title": title,
            "target": target_label,
            "status": "running",
            "detail": "Ajana gönderildi, çalışıyor…",
            "steps": [{"ts": int(time.time() * 1000), "text": f"Görev {target_label} beynine gönderildi."}],
        })

    # ─── TTS ────────────────────────────────────────────────────────
    def _speak(self, text: str) -> None:
        self.is_speaking = True
        try:
            tts.speak(text, should_stop=self.should_stop)
        except Exception as e:
            self.on_log("error", f"TTS hatası: {e}", None)
        finally:
            self.is_speaking = False

    # ─── Worker bildirimleri (arka plan CLI işi bitince) ────────────
    async def _notification_loop(self, q: asyncio.Queue) -> None:
        try:
            while True:
                notif = await q.get()
                job_id = notif["job_id"]; status = notif["status"]; content = notif["content"]
                # Task panelini güncelle (uyku/uyanık fark etmez)
                ok = status == "done"
                self.on_task({
                    "id": job_id,
                    "status": "done" if ok else "error",
                    "detail": "Tamamlandı." if ok else "Hata ile sonuçlandı.",
                    "result": content[:4000] if ok else None,
                    "error": None if ok else content[:1000],
                    "steps": [{"ts": int(time.time() * 1000),
                               "text": "Sonuç alındı." if ok else "Görev hata verdi."}],
                })
                if self.is_asleep:
                    self.on_log("system", f"[job] {job_id} bitti ({status}) — Jarvan uyuyor.", None)
                    continue
                # Gemma sonucu İngilizce özetlesin, sonra Kokoro seslendirsin.
                preview = content[:1500]
                prompt = (
                    f"[SYSTEM: background task '{job_id}' finished with status '{status}'.] "
                    f"Summarize this result for the user in ONE or two short English sentences, "
                    f"starting with 'Done' or 'Heads up'. Result:\n{preview}"
                )
                try:
                    msg = await asyncio.to_thread(self.brain.chat, [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}])
                    summary = (msg.get("content") or "").strip() or f"Background task {job_id} finished."
                except Exception:
                    summary = f"Background task {job_id} finished ({status})."
                self.on_log("jarvan", summary, "local")
                await asyncio.to_thread(self._speak, summary)
        except asyncio.CancelledError:
            pass


def _rms_int16(data: bytes) -> float:
    if not data:
        return 0.0
    a = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    if a.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(a * a)))
