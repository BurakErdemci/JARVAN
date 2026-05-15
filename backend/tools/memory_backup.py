"""Jarvan hafıza yedeği — ChromaDB + Obsidian + memory.json → Google Drive."""
import io
import json
import logging
import os
import platform
import zipfile
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger("jarvan.backup")

IS_MAC = platform.system() == "Darwin"

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Yollar ────────────────────────────────────────────────────────

CHROMA_DIR      = Path(os.getenv("CHROMA_DB_PATH",  os.path.join(_BASE, "data", "chroma")))
MEMORY_JSON     = Path(os.getenv("MEMORY_JSON_PATH", os.path.join(_BASE, "data", "memory.json")))
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH") or os.path.join(_BASE, "credentials.json")
DRIVE_TOKEN_PATH = os.path.join(_BASE, "token_drive.json")

if IS_MAC:
    OBSIDIAN_VAULT = Path(os.getenv("OBSIDIAN_VAULT_PATH",
        "/Users/burakemreerdemci/Documents/JarvanVault/JARVAN"))
else:
    OBSIDIAN_VAULT = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\JarvanVault\JARVAN"))

DRIVE_FOLDER_NAME = "jarvan_backups"
KEEP_LAST_N = 7

# Drive dosya yükleme için minimum scope
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


# ─── Google Drive Auth ──────────────────────────────────────────────

def _get_drive_service():
    creds = None
    if os.path.exists(DRIVE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(DRIVE_TOKEN_PATH, DRIVE_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"credentials.json bulunamadı: {CREDENTIALS_PATH}. "
                    "Google Cloud Console'dan Drive API'yi etkinleştir ve indir."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(DRIVE_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ─── Drive Klasör / Dosya Yardımcıları ─────────────────────────────

def _get_or_create_folder(service, name: str) -> str:
    """jarvan_backups klasörünü bulur veya oluşturur, ID döner."""
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=q, fields="files(id,name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def _list_backups(service, folder_id: str) -> list[dict]:
    q = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=q, fields="files(id,name,createdTime)",
        orderBy="createdTime desc"
    ).execute()
    return results.get("files", [])


def _delete_old_backups(service, folder_id: str, keep: int = KEEP_LAST_N) -> None:
    backups = _list_backups(service, folder_id)
    for old in backups[keep:]:
        service.files().delete(fileId=old["id"]).execute()
        logger.info(f"[backup] Eski yedek silindi: {old['name']}")


def _upload_zip(service, folder_id: str, zip_bytes: bytes, filename: str) -> str:
    media = MediaIoBaseUpload(io.BytesIO(zip_bytes), mimetype="application/zip", resumable=False)
    meta = {"name": filename, "parents": [folder_id]}
    f = service.files().create(body=meta, media_body=media, fields="id,name").execute()
    logger.info(f"[backup] Yüklendi: {f['name']} ({len(zip_bytes)//1024} KB)")
    return f["id"]


# ─── Zip Oluşturucular ──────────────────────────────────────────────

def _zip_directory(path: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if path.exists():
            for item in path.rglob("*"):
                if item.is_file():
                    zf.write(item, item.relative_to(path.parent))
    return buf.getvalue()


def _zip_files(files: list[Path]) -> bytes:
    """Belirtilen dosyaları tek zip'e toplar."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f.exists():
                zf.write(f, f.name)
    return buf.getvalue()


# ─── Ana Yedek Fonksiyonu ───────────────────────────────────────────

def backup_memory() -> dict:
    """
    Tüm hafızayı Google Drive'a yedekler.
    Mac'te çalıştırılmak üzere tasarlanmıştır (hafıza master'ı Mac).
    """
    if not IS_MAC:
        return {"ok": False, "error": "Hafıza yedeği sadece Mac'te çalışır (master cihaz)."}

    try:
        service = _get_drive_service()
        folder_id = _get_or_create_folder(service, DRIVE_FOLDER_NAME)
        tag = datetime.now().strftime("%Y-%m-%d_%H-%M")

        # 1. ChromaDB + memory.json yedeği
        chroma_zip = _zip_directory(CHROMA_DIR)
        memory_zip = _zip_files([MEMORY_JSON])
        # İkisini birleştir
        combined_buf = io.BytesIO()
        with zipfile.ZipFile(combined_buf, "w") as zf:
            zf.writestr("chroma.zip", chroma_zip)
            zf.writestr("memory.zip", memory_zip)
        memory_backup_bytes = combined_buf.getvalue()

        # 2. Obsidian vault yedeği
        obsidian_zip = _zip_directory(OBSIDIAN_VAULT)

        # 3. Drive'a yükle
        _upload_zip(service, folder_id, memory_backup_bytes, f"memory_{tag}.zip")
        _upload_zip(service, folder_id, obsidian_zip,        f"obsidian_{tag}.zip")

        # 4. Eski yedekleri temizle (her tür için ayrı)
        _delete_old_backups(service, folder_id, keep=KEEP_LAST_N * 2)

        return {
            "ok": True,
            "result": f"Hafıza yedeği Google Drive'a yüklendi ({tag}).",
            "memory_kb": len(memory_backup_bytes) // 1024,
            "obsidian_kb": len(obsidian_zip) // 1024,
        }

    except Exception as e:
        logger.error(f"[backup] Hata: {e}")
        return {"ok": False, "error": str(e)}


def get_backup_status() -> dict:
    """Drive'daki son yedekleri listeler."""
    try:
        service = _get_drive_service()
        folder_id = _get_or_create_folder(service, DRIVE_FOLDER_NAME)
        backups = _list_backups(service, folder_id)
        return {
            "ok": True,
            "count": len(backups),
            "backups": [{"name": b["name"], "date": b["createdTime"]} for b in backups[:5]],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
