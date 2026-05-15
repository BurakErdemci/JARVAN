import asyncio
import os
import platform
import shutil
import uuid
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvan.gemini_cli")

IS_WIN = platform.system() == "Windows"

# Gemini CLI binary — env var > PATH lookup > platform default
_cli_env = os.getenv("GEMINI_CLI_PATH", "").strip()
if _cli_env:
    GEMINI_BIN = _cli_env
elif IS_WIN:
    # npm kurulumu: gemini.cmd PATH'de — tam yol bulunmazsa cmd /c ile çağırılır
    GEMINI_BIN = shutil.which("gemini.cmd") or shutil.which("gemini") or "gemini"
else:
    GEMINI_BIN = shutil.which("gemini") or "/opt/homebrew/bin/gemini"

# Proje kök dizini — env var yoksa bu dosyadan iki seviye yukarı
JARVAN_DIR = os.getenv(
    "JARVAN_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

MODEL_FLASH = "gemini-3-flash-preview"      # genel kullanım
MODEL_PRO   = "gemini-3.1-pro-preview"      # ağır/karmaşık işler

# In-memory job store: job_id -> {status, result, error, model}
_jobs: Dict[str, Dict[str, Any]] = {}

# Live session buraya queue koyar, worker bitince notification atar
_notification_queue: Optional[asyncio.Queue] = None


def set_notification_queue(q: asyncio.Queue) -> None:
    """LiveSession başlarken çağırır — tamamlanan işler buraya bildirilir."""
    global _notification_queue
    _notification_queue = q


def clear_notification_queue() -> None:
    """LiveSession kapanırken çağırır."""
    global _notification_queue
    _notification_queue = None


async def start_gemini_task(prompt: str, heavy: bool = False) -> str:
    """
    Gemini CLI'yi arka planda başlatır, anında job_id döner.
    heavy=True → gemini-3.1-pro-preview (derin analiz, büyük refactor)
    heavy=False → gemini-3-flash-preview (genel kod, hızlı görevler)
    Bitince notification_queue'ya otomatik bildirim gönderir.
    """
    model = MODEL_PRO if heavy else MODEL_FLASH
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {"status": "running", "result": None, "error": None, "model": model}
    asyncio.create_task(_run(job_id, prompt, model))
    logger.info(f"[gemini_cli] Görev başlatıldı: {job_id} ({model})")
    return job_id


def get_job_result(job_id: str) -> Dict[str, Any]:
    """
    job_id ile görev durumunu sorgular.
    status: running | done | error | not_found
    """
    return _jobs.get(job_id, {"status": "not_found", "result": None, "error": None})


async def _run(job_id: str, prompt: str, model: str) -> None:
    try:
        # Windows'ta .cmd dosyaları cmd /c üzerinden çalışır
        if IS_WIN:
            cmd = ["cmd", "/c", GEMINI_BIN, "--model", model, "--yolo"]
        else:
            cmd = [GEMINI_BIN, "--model", model, "--yolo"]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=JARVAN_DIR,
        )
        stdout, stderr = await proc.communicate(prompt.encode("utf-8"))

        output = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0 or output:
            _jobs[job_id] = {"status": "done", "result": output, "error": err or None}
            logger.info(f"[gemini_cli] Tamamlandı: {job_id} ({len(output)} karakter)")
            await _notify(job_id, "done", output)
        else:
            _jobs[job_id] = {"status": "error", "result": None, "error": err or "Bilinmeyen hata"}
            logger.error(f"[gemini_cli] Hata: {job_id} — {err[:200]}")
            await _notify(job_id, "error", err or "Bilinmeyen hata")

    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}
        logger.error(f"[gemini_cli] Exception: {job_id} — {e}")
        await _notify(job_id, "error", str(e))


async def _notify(job_id: str, status: str, content: str) -> None:
    """Tamamlanan işi notification_queue'ya koyar."""
    if _notification_queue is not None:
        await _notification_queue.put({
            "job_id": job_id,
            "status": status,
            "content": content,
        })
