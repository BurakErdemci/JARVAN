import sys
import os

# Child process'lere miras kalması için import'lardan önce set et
os.environ["PYTHONIOENCODING"] = "utf-8"

# ChromaDB gRPC fork loglarını sustur
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = ""

# Windows cp1252 → emoji/unicode logları kırar; UTF-8'e zorla
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import json
import threading
import queue
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_MS
from modes.detector import get_active_mode

CHUNK = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)


class PipelineEvent:
    def __init__(self, type: str, **data):
        self.type = type
        self.data = data

    def to_dict(self):
        return {"type": self.type, **self.data}


class Pipeline:
    """Ses pipeline'ını ayrı thread'de yönetir, event'leri queue'ya basar."""

    def __init__(self, event_queue: queue.Queue):
        self.q = event_queue
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self.running = False
        self.live_enabled = True
        self.proactive_enabled = False
        self.conversation_memory: list[dict] = []

    def emit(self, type: str, **data):
        self.q.put(PipelineEvent(type, **data))

    def start(self):
        if self.running:
            return
            
        # Vosk Model Check
        model_p = os.path.join(os.path.dirname(__file__), "models", "vosk-tr")
        if not os.path.exists(model_p):
            self.emit("log", level="error", text="⚠️ Vosk modeli (vosk-tr) bulunamadı! Yerel uyandırma 'Uyan Jarvan' çalışmayabilir.")
        else:
            self.emit("log", level="system", text="✅ Wake Word (Yerel Dinleme) sistemi hazır.")

        self.stop_flag.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.running = True
        self.emit("status", running=True, live=self.live_enabled, proactive=self.proactive_enabled)

    def stop(self):
        if not self.running:
            return
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=5)
        self.running = False
        self.emit("status", running=False, live=self.live_enabled, proactive=self.proactive_enabled)


    def set_proactive(self, enabled: bool):
        if self.proactive_enabled == enabled:
            return
        self.proactive_enabled = enabled
        if self.running and self.live_enabled:
            self.emit("log", level="system", text=f"Proaktif {'açılıyor' if enabled else 'kapatılıyor'}, Live yeniden başlatılıyor...")
            self.stop()
            self.start()
        else:
            self.emit("status", running=self.running, live=self.live_enabled, proactive=enabled)
            self.emit("log", level="system", text=f"Proaktif yorum {'açık' if enabled else 'kapalı'}")

    def set_live(self, enabled: bool):
        if self.live_enabled == enabled:
            return
        self.live_enabled = enabled
        if self.running:
            self.emit("log", level="system", text=f"Live {'açılıyor' if enabled else 'kapatılıyor'}, pipeline yeniden başlatılıyor...")
            self.stop()
            if enabled:
                self.start()
        self.emit("status", running=self.running, live=self.live_enabled, proactive=self.proactive_enabled)

    def _emit_log(self, level: str, text: str, provider: str | None = None):
        if level in ("user", "jarvan"):
            role = "KULLANICI" if level == "user" else "SEN (JARVAN)"
            self.conversation_memory.append({"role": role, "text": text})
            if len(self.conversation_memory) > 20:
                self.conversation_memory.pop(0)

        if provider:
            self.emit("log", level=level, text=text, provider=provider)
        else:
            self.emit("log", level=level, text=text)

    def _run(self):
        if self.live_enabled:
            self._run_live()
        else:
            self.emit("log", level="system", text="Live kapalı. Pipeline başlatılmadı.")

    def _run_live(self):
        import asyncio
        import time
        from ai.live_session import LiveSession

        MAX_RETRIES = 5
        retries = 0
        try:
            mode_name, system_prompt = get_active_mode()
            self.emit("mode", name=mode_name)

            while not self.stop_flag.is_set():
                session = LiveSession(
                    system_prompt=system_prompt,
                    on_log=self._emit_log,
                    should_stop=self.stop_flag.is_set,
                    send_video=self.proactive_enabled,
                    conversation_memory=self.conversation_memory,
                )

                start_ts = time.monotonic()
                try:
                    asyncio.run(session.run())
                except Exception as e:
                    self.emit("log", level="error", text=f"Live pipeline hatası: {e}")

                if self.stop_flag.is_set():
                    break

                ran_for = time.monotonic() - start_ts
                if ran_for > 30:
                    retries = 0

                retries += 1
                if retries > MAX_RETRIES:
                    self.emit("log", level="error", text=f"Live {MAX_RETRIES} kez üst üste çöktü — otomatik yeniden bağlanma durduruldu.")
                    break

                self.emit("log", level="system", text=f"Live bağlantısı koptu, {retries}. yeniden bağlanma (hafıza korundu)...")
                time.sleep(min(2 * retries, 8))
        finally:
            self.emit("log", level="system", text="Live oturum kapandı.")



class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


event_queue: queue.Queue = queue.Queue()
pipeline = Pipeline(event_queue)
manager = ConnectionManager()


async def event_pump():
    loop = asyncio.get_event_loop()
    while True:
        try:
            event = await loop.run_in_executor(None, event_queue.get, True, 0.5)
        except queue.Empty:
            continue
        if event is None:
            continue
        await manager.broadcast(event.to_dict())


async def _nightly_scheduler():
    """Her gece 23:xx'de hafıza sync + Drive yedek çalıştırır.
    Backend o saatte kapalıysa açılışta bugünün sync'ini hemen yapar."""
    import platform
    from datetime import datetime, date
    from tools.memory_sync import nightly_sync, _load_json, STATE_FILE

    IS_MAC = platform.system() == "Darwin"

    def _last_sync_date():
        state = _load_json(STATE_FILE)
        if not state or "last_sync" not in state:
            return None
        try:
            return datetime.fromisoformat(state["last_sync"]).date()
        except Exception:
            return None

    async def _run_sync():
        try:
            result = await asyncio.to_thread(nightly_sync)
            print(f"[sync] {result}", flush=True)
        except Exception as e:
            print(f"[sync] Hata: {e}", flush=True)
        if IS_MAC:
            try:
                from tools.memory_backup import backup_memory
                result = await asyncio.to_thread(backup_memory)
                print(f"[backup] {result.get('result') or result.get('error')}", flush=True)
            except Exception as e:
                print(f"[backup] Hata: {e}", flush=True)

    # Açılışta: bugün sync yapılmadıysa hemen çalıştır
    await asyncio.sleep(10)  # backend tam ayağa kalksın
    if _last_sync_date() != date.today():
        print("[sync] Bugün henüz sync yapılmamış, başlatılıyor...", flush=True)
        await _run_sync()

    while True:
        await asyncio.sleep(60)
        now = datetime.now()
        if now.hour == 23 and _last_sync_date() != date.today():
            await _run_sync()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from tools.device_transfer import start_watcher, stop_watcher
    task = asyncio.create_task(event_pump())
    backup_task = asyncio.create_task(_nightly_scheduler())
    loop = asyncio.get_event_loop()
    start_watcher(loop)
    yield
    task.cancel()
    backup_task.cancel()
    stop_watcher()
    pipeline.stop()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"ok": True, "running": pipeline.running}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    try:
        await manager.connect(ws)
        await ws.send_json({
            "type": "status",
            "running": pipeline.running,
            "live": pipeline.live_enabled,
            "proactive": pipeline.proactive_enabled,
        })
        mode_name, _ = get_active_mode()
        await ws.send_json({"type": "mode", "name": mode_name})

        while True:
            msg = await ws.receive_json()
            t = msg.get("type")
            if t == "start":
                pipeline.start()
            elif t == "stop":
                pipeline.stop()
            elif t == "toggle_proactive":
                pipeline.set_proactive(bool(msg.get("enabled")))
            elif t == "toggle_live":
                pipeline.set_live(bool(msg.get("enabled")))
            else:
                await ws.send_json({"type": "log", "level": "error", "text": f"Bilinmeyen komut: {t}"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
