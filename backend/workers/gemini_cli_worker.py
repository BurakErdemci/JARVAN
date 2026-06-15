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

# ─── Çok-hedefli dispatch (Phase 2 — "beyinler": agy / codex / claude) ────────
# Gemma dispatcher hedef seçer; ağır iş abonelikli CLI'ya gider. Komutlar CONFIG'den
# gelir → bir CLI arayüzü değişir/patlarsa tek satır .env ile düzelir (memory uyarısı).
#
#   gemini → agy --print          (Gemini 3.x; araştırma/multimodal/uzun bağlam, ucuz)
#   gpt    → codex exec            (GPT-5.x-codex; ChatGPT aboneliğine DAHİL, hassas kod)
#   claude → claude "<prompt>"     (Opus; -p YOK. TTY yokken claude otomatik non-interactive
#            çıktıya düşüyor — PTY GEREKMEZ, düz subprocess yeter. Canlı doğrulandı.)
DISPATCH_DEFAULT_TARGET = os.getenv("DISPATCH_DEFAULT_TARGET", "gpt").lower()

# codex (OpenAI) — non-interactive exec. Doğru bayraklar (canlı doğrulandı):
#   --skip-git-repo-check : git repo dışında da çalışsın (yoksa cwd'yi repo'ya resetler)
#   --sandbox workspace-write : cwd içinde otonom dosya yazma (--full-auto DEPRECATED)
#   --color never : ANSI yok → temiz stdout. (--json JSONL event akışı verir, sonuç için kirli.)
CODEX_BIN  = os.getenv("CODEX_BIN", "codex")
CODEX_ARGS = os.getenv("CODEX_ARGS", "exec --skip-git-repo-check --sandbox workspace-write --color never")

# claude (Anthropic) — `claude "<prompt>"` (-p YOK). TTY yokken non-interactive çıktıya
# düşüp stdout'a yazıyor, dosya da yazıyor (canlı doğrulandı, PTY gerekmez).
# ⚠️ FATURALAMA BELİRSİZ: çıktı `-p` ile aynı; Anthropic'in ayrımı TTY-var(abonelik) vs
# otomatik(ücretli API havuzu). TTY olmadığı için MUHTEMELEN yine ücretli havuza düşer.
# Açmadan önce TEK çağrı yapıp Claude usage panelinden faturayı DOĞRULA. Default KAPALI.
CLAUDE_BIN      = os.getenv("CLAUDE_BIN", "claude")
CLAUDE_ENABLED  = os.getenv("CLAUDE_ENABLED", "0") == "1"
CLAUDE_ARGS     = os.getenv("CLAUDE_ARGS", "--dangerously-skip-permissions")
# Doluysa claude hedefi bu shell komutuyla çalışır ({prompt} değişir) — özel sarmalayıcı için.
CLAUDE_DISPATCH_CMD = os.getenv("CLAUDE_DISPATCH_CMD", "")


def _resolve_bin(name: str) -> str:
    """Windows'ta codex/claude npm `.cmd` shim'i — create_subprocess_exec bunları PATH'ten
    uzantısız bulamaz (FileNotFoundError). shutil.which .cmd/.exe'yi çözer; bulamazsa adı bırak."""
    return shutil.which(name) or name


# agy --print BİLİNEN BUG'I (Issue #76/#115): non-TTY subprocess'te cevabı stdout'a YAZMIYOR
# (rc=0, boş). PTY workaround yerine agy'nin kendi transcript dosyasından okuyoruz (daha
# sağlam, Windows+Mac aynı, bağımlılık yok). agy her cwd için bir conversation tutar:
#   cache/last_conversations.json : {cwd: conversation_id}
#   brain/<id>/.system_generated/logs/transcript.jsonl : satırlarda type==PLANNER_RESPONSE → content
AGY_HOME = os.getenv("AGY_HOME", os.path.join(os.path.expanduser("~"), ".gemini", "antigravity-cli"))


def _read_agy_response(cwd: str) -> Optional[str]:
    """agy'nin son cevabını transcript'ten oku (stdout boş gelince fallback)."""
    try:
        lc = os.path.join(AGY_HOME, "cache", "last_conversations.json")
        conv_map = json.loads(Path(lc).read_text(encoding="utf-8"))
        target = os.path.normcase(os.path.normpath(cwd))
        conv = next((v for k, v in conv_map.items()
                     if os.path.normcase(os.path.normpath(k)) == target), None)
        if not conv:
            return None
        tp = os.path.join(AGY_HOME, "brain", conv, ".system_generated", "logs", "transcript.jsonl")
        if not os.path.exists(tp):
            return None
        parts = []
        for line in Path(tp).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") == "PLANNER_RESPONSE" and o.get("content"):
                parts.append(o["content"])
        return "\n".join(parts).strip() or None
    except Exception as e:
        logger.warning(f"[agy] transcript okunamadı: {e}")
        return None


def _timeout_seconds(spec: str, default: int = 1800) -> int:
    """'30m' / '90s' / '2h' → saniye. Codex/claude'a wait_for timeout'u için."""
    try:
        spec = (spec or "").strip().lower()
        if spec.endswith("h"):
            return int(float(spec[:-1]) * 3600)
        if spec.endswith("m"):
            return int(float(spec[:-1]) * 60)
        if spec.endswith("s"):
            return int(float(spec[:-1]))
        return int(float(spec))
    except (ValueError, TypeError):
        return default


def _target_label(target: str, heavy: bool) -> str:
    """Task panelinde/log'da gösterilecek motor adı."""
    if target == "gemini":
        return MODEL_HEAVY if heavy else MODEL_FAST
    if target == "gpt":
        return "Codex (GPT-5.x)"
    if target == "claude":
        return "Claude Code (Opus)"
    return target


def _build_command(target: str, prompt: str, heavy: bool) -> list[str]:
    """Hedefe göre subprocess komutu kurar. codex/claude bin'leri Windows .cmd için resolve."""
    if target == "gemini":
        model = MODEL_HEAVY if heavy else MODEL_FAST
        return [AGY_BIN, "--model", model, "--dangerously-skip-permissions",
                "--print-timeout", PRINT_TIMEOUT, "--print", prompt]
    if target == "gpt":
        return [_resolve_bin(CODEX_BIN), *CODEX_ARGS.split(), prompt]
    if target == "claude":
        return [_resolve_bin(CLAUDE_BIN), *CLAUDE_ARGS.split(), prompt]
    raise ValueError(f"Bilinmeyen dispatch hedefi: {target}")

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


async def dispatch_task(prompt: str, target: str = "", heavy: bool = False) -> str:
    """Ağır işi seçilen CLI beynine paslar. Anında job_id döner.

    target: 'gemini' (agy) | 'gpt' (codex) | 'claude'. Boş → DISPATCH_DEFAULT_TARGET.
    heavy:  gemini'de Pro/Flash seçer; gpt/claude'da yok sayılır (tek model).
    Bitince notification_queue'ya otomatik bildirim gönderir.
    """
    target = (target or DISPATCH_DEFAULT_TARGET).lower()
    if target not in ("gemini", "gpt", "claude"):
        target = DISPATCH_DEFAULT_TARGET
    label = _target_label(target, heavy)
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {"status": "running", "result": None, "error": None,
                     "model": label, "target": target}
    _save_jobs(_jobs)
    asyncio.create_task(_run(job_id, prompt, target, heavy))
    logger.info(f"[dispatch] Görev başlatıldı: {job_id} → {target} ({label})")
    return job_id


async def start_gemini_task(prompt: str, heavy: bool = False) -> str:
    """Geriye-uyum alias'ı — eski çağrılar Gemini (agy) hedefine gider."""
    return await dispatch_task(prompt, target="gemini", heavy=heavy)


def get_job_result(job_id: str) -> Dict[str, Any]:
    """
    job_id ile görev durumunu sorgular.
    status: running | done | error | not_found
    """
    return _jobs.get(job_id, {"status": "not_found", "result": None, "error": None})


async def _finish(job_id: str, target: str, output: str, err: str, returncode: int) -> None:
    """Subprocess sonucunu job'a yaz + notification at (agy/codex ortak)."""
    if returncode == 0 or output:
        _jobs[job_id] = {**_jobs.get(job_id, {}), "status": "done",
                         "result": output, "error": err or None}
        _save_jobs(_jobs)
        logger.info(f"[dispatch:{target}] Tamamlandı: {job_id} ({len(output)} karakter)")
        await _notify(job_id, "done", output)
    else:
        _jobs[job_id] = {**_jobs.get(job_id, {}), "status": "error",
                         "result": None, "error": err or "Bilinmeyen hata"}
        _save_jobs(_jobs)
        logger.error(f"[dispatch:{target}] Hata: {job_id} — {err[:200]}")
        await _notify(job_id, "error", err or "Bilinmeyen hata")


async def _fail(job_id: str, target: str, msg: str) -> None:
    _jobs[job_id] = {**_jobs.get(job_id, {}), "status": "error", "result": None, "error": msg}
    _save_jobs(_jobs)
    logger.error(f"[dispatch:{target}] {msg}")
    await _notify(job_id, "error", msg)


async def _run(job_id: str, prompt: str, target: str, heavy: bool) -> None:
    if target == "claude":
        if not CLAUDE_ENABLED:
            await _fail(job_id, "claude",
                        "Claude hedefi kapalı (CLAUDE_ENABLED=0). `-p` olmadan da çalışıyor "
                        "ama FATURALAMA belirsiz (muhtemelen ücretli API havuzu). Açmadan önce "
                        "tek çağrıyla Claude usage panelinden faturayı doğrula, sonra .env'de "
                        "CLAUDE_ENABLED=1 yap.")
            return
        if CLAUDE_DISPATCH_CMD:  # özel sarmalayıcı verilmişse onu kullan
            await _run_claude_shell(job_id, prompt)
            return
        # aksi halde normal subprocess yoluna düş: claude "<prompt>" (_build_command)
    try:
        cmd = _build_command(target, prompt, heavy)
        bin_name = cmd[0]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=JARVAN_DIR,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=_timeout_seconds(PRINT_TIMEOUT))
        except asyncio.TimeoutError:
            proc.kill()
            await _fail(job_id, target, f"{target} zaman aşımına uğradı ({PRINT_TIMEOUT}).")
            return

        output = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        # agy --print non-TTY'de stdout'u düşürür (bilinen bug) → transcript'ten oku.
        if target == "gemini" and not output:
            transcript = _read_agy_response(JARVAN_DIR)
            if transcript:
                output = transcript
        await _finish(job_id, target, output, err, proc.returncode)

    except FileNotFoundError:
        await _fail(job_id, target,
                    f"{bin_name if 'bin_name' in dir() else target} binary bulunamadı. "
                    f"PATH'i ya da ilgili *_BIN env'ini kontrol et.")
    except ValueError as e:
        await _fail(job_id, target, str(e))
    except Exception as e:
        await _fail(job_id, target, str(e))


async def _run_claude_shell(job_id: str, prompt: str) -> None:
    """CLAUDE_DISPATCH_CMD verildiyse claude'u özel shell komutuyla çalıştır ({prompt} değişir).
    Özel sarmalayıcı (gerçek TTY için script/tmux vb.) isteyenler için kaçış kapısı."""
    try:
        cmd_str = CLAUDE_DISPATCH_CMD.replace("{prompt}", prompt)
        proc = await asyncio.create_subprocess_shell(
            cmd_str,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=JARVAN_DIR,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_timeout_seconds(PRINT_TIMEOUT))
        await _finish(job_id, "claude",
                      stdout.decode("utf-8", errors="replace").strip(),
                      stderr.decode("utf-8", errors="replace").strip(),
                      proc.returncode)
    except asyncio.TimeoutError:
        await _fail(job_id, "claude", f"claude zaman aşımına uğradı ({PRINT_TIMEOUT}).")
    except Exception as e:
        await _fail(job_id, "claude", str(e))


async def _notify(job_id: str, status: str, content: str) -> None:
    """Tamamlanan işi notification_queue'ya koyar."""
    if _notification_queue is not None:
        await _notification_queue.put({
            "job_id": job_id,
            "status": status,
            "content": content,
        })
