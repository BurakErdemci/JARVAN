"""Cihazlar arası dosya transferi — Syncthing ortak klasörü üzerinden."""
import asyncio
import json
import logging
import os
import platform
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("jarvan.transfer")

IS_MAC = platform.system() == "Darwin"
THIS_DEVICE = "mac" if IS_MAC else "windows"
OTHER_DEVICE = "windows" if IS_MAC else "mac"

# ─── Syncthing Ortak Klasör ────────────────────────────────────────
# Her iki PC'de de Syncthing bu klasörü senkronize eder.
# Mac:     ~/JarvanShare      (veya JARVAN_SHARE_PATH env var)
# Windows: C:\JarvanShare     (veya JARVAN_SHARE_PATH env var)

def _default_share() -> str:
    if IS_MAC:
        return os.path.expanduser("~/JarvanShare")
    return r"C:\JarvanShare"

SHARE_ROOT = Path(os.getenv("JARVAN_SHARE_PATH", _default_share()))

# Alt klasörler
TRANSFER_DIR  = SHARE_ROOT / "transfer"
INBOX_DIR     = TRANSFER_DIR / f"to_{THIS_DEVICE}"    # benim gelen kutum
OUTBOX_DIR    = TRANSFER_DIR / f"to_{OTHER_DEVICE}"   # karşı tarafa giden
MANIFEST_DIR  = TRANSFER_DIR / "manifests"

for _d in [INBOX_DIR, OUTBOX_DIR, MANIFEST_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ─── Dosya Gönder ──────────────────────────────────────────────────

def send_to_device(file_path: str, message: str = "", device: str = OTHER_DEVICE) -> dict:
    """
    Dosyayı Syncthing ortak klasörüne kopyalar.
    Syncthing karşı cihaza otomatik iletir.
    """
    src = Path(file_path).expanduser()
    if not src.exists():
        return {"ok": False, "error": f"Dosya bulunamadı: {file_path}"}

    target_dir = TRANSFER_DIR / f"to_{device}"
    target_dir.mkdir(parents=True, exist_ok=True)

    dst = target_dir / src.name
    # Aynı isimde dosya varsa timestamp ekle
    if dst.exists():
        stem = src.stem
        suffix = src.suffix
        ts = datetime.now().strftime("%H%M%S")
        dst = target_dir / f"{stem}_{ts}{suffix}"

    shutil.copy2(src, dst)

    # Manifest yaz — karşı taraf bu dosyayı okuyup bildirim yapar
    manifest = {
        "from": THIS_DEVICE,
        "to": device,
        "file": dst.name,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "size_kb": dst.stat().st_size // 1024,
    }
    manifest_path = MANIFEST_DIR / f"{dst.stem}_{THIS_DEVICE}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"[transfer] Gönderildi → {device}: {dst.name}")
    return {
        "ok": True,
        "result": f"'{src.name}' dosyası {device}'a gönderildi. Syncthing iletecek.",
        "destination": str(dst),
    }


# ─── Gelen Dosya İzleyici ──────────────────────────────────────────

class FileWatcher:
    """INBOX_DIR'ı izler, yeni dosya gelince callback çağırır."""

    def __init__(self, on_file: Callable):
        self._on_file = on_file
        self._seen: set = set()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._seen = {p.name for p in INBOX_DIR.iterdir() if p.is_file()}
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._watch, daemon=True, name="file-watcher")
        self._thread.start()
        logger.info(f"[transfer] FileWatcher başlatıldı → {INBOX_DIR}")

    def stop(self) -> None:
        self._stop_event.set()

    def _watch(self) -> None:
        while not self._stop_event.is_set():
            try:
                for f in INBOX_DIR.iterdir():
                    if f.is_file() and f.name not in self._seen:
                        self._seen.add(f.name)
                        manifest = self._find_manifest(f.name)
                        asyncio.run_coroutine_threadsafe(
                            self._on_file(f, manifest), self._loop
                        )
            except Exception as e:
                logger.error(f"[transfer] Watcher hata: {e}")
            time.sleep(3)

    def _find_manifest(self, filename: str) -> dict:
        stem = Path(filename).stem
        # stem içinde timestamp soneki olabilir, tam eşleşme dene
        for mf in MANIFEST_DIR.glob(f"{stem}_*.json"):
            try:
                return json.loads(mf.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"file": filename, "from": OTHER_DEVICE, "message": ""}


# ─── Singleton Watcher ─────────────────────────────────────────────

_watcher: Optional[FileWatcher] = None
_notification_callback: Optional[Callable] = None


def set_incoming_callback(cb: callable) -> None:
    """LiveSession bu callback'i register eder — yeni dosya gelince çağrılır."""
    global _notification_callback
    _notification_callback = cb


async def _on_file_received(path: Path, manifest: dict) -> None:
    logger.info(f"[transfer] Gelen dosya: {path.name} from={manifest.get('from')}")
    if _notification_callback:
        try:
            await _notification_callback(path, manifest)
        except Exception as e:
            logger.error(f"[transfer] Callback hata: {e}")


def start_watcher(loop: asyncio.AbstractEventLoop) -> None:
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher(on_file=_on_file_received)
    _watcher.start(loop)


def stop_watcher() -> None:
    if _watcher:
        _watcher.stop()


# ─── Durum Sorgu ───────────────────────────────────────────────────

def get_transfer_status() -> dict:
    """Gelen kutusundaki dosyaları listeler."""
    files = [
        {"name": f.name, "size_kb": f.stat().st_size // 1024}
        for f in INBOX_DIR.iterdir() if f.is_file()
    ]
    return {
        "ok": True,
        "this_device": THIS_DEVICE,
        "share_root": str(SHARE_ROOT),
        "inbox": files,
        "inbox_count": len(files),
    }
