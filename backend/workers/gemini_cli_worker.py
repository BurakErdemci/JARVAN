"""Arka plan dev/araştırma worker'ı.

Motor: Antigravity CLI (`agy`) — Gemini CLI'nin halefi. Public API
(`start_gemini_task`, `get_job_result`, notification queue) aynı kaldı; sadece
alttaki subprocess çağrısı `gemini`'den `agy --print`'e geçti.

agy arayüzü:
  agy --model "<display ad>" --dangerously-skip-permissions \
      --print-timeout <süre> --print "<prompt>"
  → prompt'u argüman olarak alır, cevabı stdout'a yazıp çıkar (TTY gerekmez).
"""

import asyncio
import json
import os
import uuid
import logging
import shutil
import platform
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("jarvan.agy_cli")


def _find_agy_bin() -> str:
    """agy binary'sini bul. PATH güncellenmemiş shell'lerde de çalışsın diye
    kurulum yollarına da bakar (Windows: %LOCALAPPDATA%\\agy\\bin)."""
    if env := os.getenv("AGY_BIN"):
        return env
    if env := os.getenv("GEMINI_BIN"):  # eski config'lerle geriye uyum
        return env
    if found := shutil.which("agy"):
        return found

    candidates = []
    if platform.system() == "Windows":
        local = os.getenv("LOCALAPPDATA", "")
        if local:
            candidates.append(os.path.join(local, "agy", "bin", "agy.exe"))
    else:
        home = os.path.expanduser("~")
        candidates.append(os.path.join(home, ".local", "bin", "agy"))
        candidates.append(os.path.join(home, ".agy", "bin", "agy"))

    for c in candidates:
        if os.path.exists(c):
            return c
    return "agy"  # son çare — PATH'te olduğunu umar


AGY_BIN = _find_agy_bin()
JARVAN_DIR = os.getenv("JARVAN_DIR", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Model display isimleri (agy models çıktısından). .env ile override edilebilir.
MODEL_FAST  = os.getenv("AGY_MODEL_FAST",  "Gemini 3.5 Flash (Medium)")
MODEL_HEAVY = os.getenv("AGY_MODEL_HEAVY", "Gemini 3.1 Pro (High)")

# Ağır görevler default 5dk'yı aşabilir (büyük refactor, derin araştırma).
PRINT_TIMEOUT = os.getenv("AGY_PRINT_TIMEOUT", "30m")

# Job sonuçlarını diske yaz — session yeniden bağlanınca kaybolmaz
_BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_JOBS_FILE = _BASE / "data" / "jobs.json"

def _load_jobs() -> Dict[str, Dict[str, Any]]:
    try:
        return json.loads(_JOBS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_jobs(jobs: Dict) -> None:
    try:
        _JOBS_FILE.parent.mkdir(exist_ok=True)
        _JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[agy] jobs.json yazılamadı: {e}")

# Başlangıçta diskten yükle
_jobs: Dict[str, Dict[str, Any]] = _load_jobs()

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
    agy CLI'yi arka planda başlatır, anında job_id döner.
    heavy=True → Gemini 3.1 Pro (High) — derin analiz, büyük refactor
    heavy=False → Gemini 3.5 Flash (Medium) — genel kod, hızlı görevler
    Bitince notification_queue'ya otomatik bildirim gönderir.
    """
    model = MODEL_HEAVY if heavy else MODEL_FAST
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {"status": "running", "result": None, "error": None, "model": model}
    asyncio.create_task(_run(job_id, prompt, model))
    logger.info(f"[agy] Görev başlatıldı: {job_id} ({model})")
    return job_id


def get_job_result(job_id: str) -> Dict[str, Any]:
    """
    job_id ile görev durumunu sorgular.
    status: running | done | error | not_found
    """
    return _jobs.get(job_id, {"status": "not_found", "result": None, "error": None})


async def _run(job_id: str, prompt: str, model: str) -> None:
    try:
        # agy.exe native binary — cmd /c sarmalama gerekmez, prompt argüman olarak gider.
        cmd = [
            AGY_BIN,
            "--model", model,
            "--dangerously-skip-permissions",
            "--print-timeout", PRINT_TIMEOUT,
            "--print", prompt,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=JARVAN_DIR,
        )
        stdout, stderr = await proc.communicate()

        output = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0 or output:
            _jobs[job_id] = {"status": "done", "result": output, "error": err or None}
            _save_jobs(_jobs)
            logger.info(f"[agy] Tamamlandı: {job_id} ({len(output)} karakter)")
            await _notify(job_id, "done", output)
        else:
            _jobs[job_id] = {"status": "error", "result": None, "error": err or "Bilinmeyen hata"}
            _save_jobs(_jobs)
            logger.error(f"[agy] Hata: {job_id} — {err[:200]}")
            await _notify(job_id, "error", err or "Bilinmeyen hata")

    except FileNotFoundError:
        msg = f"agy binary bulunamadı ({AGY_BIN}). AGY_BIN env veya PATH'i kontrol et."
        _jobs[job_id] = {"status": "error", "result": None, "error": msg}
        _save_jobs(_jobs)
        logger.error(f"[agy] {msg}")
        await _notify(job_id, "error", msg)
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}
        _save_jobs(_jobs)
        logger.error(f"[agy] Exception: {job_id} — {e}")
        await _notify(job_id, "error", str(e))


async def _notify(job_id: str, status: str, content: str) -> None:
    """Tamamlanan işi notification_queue'ya koyar."""
    if _notification_queue is not None:
        await _notification_queue.put({
            "job_id": job_id,
            "status": status,
            "content": content,
        })
