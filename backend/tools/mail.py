"""Gmail — API tabanlı gönderim (OAuth), fallback olarak compose URL."""
import base64
import json
import os
import sys
import subprocess
import urllib.parse
import webbrowser
from email.utils import parsedate_to_datetime
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from tools.contacts import resolve_email

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH") or os.path.join(_BASE, "credentials.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH") or os.path.join(_BASE, "token.json")
MAIL_STATE_PATH = os.path.join(_BASE, "data", "gmail_state.json")

MAIL_ACCOUNTS = {
    "burcu": "burcuemre0@gmail.com",
    "burcuemre": "burcuemre0@gmail.com",
    "burcuemre0": "burcuemre0@gmail.com",
    "burcuemre0@gmail.com": "burcuemre0@gmail.com",
    "erdem": "erdemciburakemre@gmail.com",
    "burak": "erdemciburakemre@gmail.com",
    "erdemci": "erdemciburakemre@gmail.com",
    "erdemciburakemre": "erdemciburakemre@gmail.com",
    "erdemciburakemre@gmail.com": "erdemciburakemre@gmail.com",
}
DEFAULT_ACCOUNT = os.getenv("GMAIL_DEFAULT_ACCOUNT", "erdemciburakemre@gmail.com")

MAC_PREFERRED_BROWSER = "Google Chrome"


def _normalize_account(account: str | None = None) -> str:
    raw = (account or "").strip().lower()
    if not raw:
        raw = _load_active_account()
    return MAIL_ACCOUNTS.get(raw, raw if "@" in raw else DEFAULT_ACCOUNT)


def _token_path_for_account(account: str | None = None) -> str:
    if os.getenv("GMAIL_TOKEN_PATH"):
        return TOKEN_PATH
    email = _normalize_account(account)
    if email == DEFAULT_ACCOUNT and os.path.exists(TOKEN_PATH):
        return TOKEN_PATH
    safe = email.replace("@", "_").replace(".", "_")
    return os.path.join(_BASE, f"token_{safe}.json")


def _load_active_account() -> str:
    try:
        with open(MAIL_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_account(data.get("active_account") or DEFAULT_ACCOUNT)
    except Exception:
        return DEFAULT_ACCOUNT


def switch_mail_account(account: str) -> dict:
    email = _normalize_account(account)
    os.makedirs(os.path.dirname(MAIL_STATE_PATH), exist_ok=True)
    with open(MAIL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"active_account": email}, f, ensure_ascii=False, indent=2)
    token_path = _token_path_for_account(email)
    return {
        "ok": True,
        "active_account": email,
        "token_ready": os.path.exists(token_path),
        "token_path": token_path,
    }


def get_active_mail_account() -> dict:
    email = _load_active_account()
    token_path = _token_path_for_account(email)
    return {
        "ok": True,
        "active_account": email,
        "token_ready": os.path.exists(token_path),
        "available_accounts": sorted(set(MAIL_ACCOUNTS.values())),
    }


def _get_service(account: str | None = None):
    token_path = _token_path_for_account(account)
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and not creds.has_scopes(SCOPES):
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # invalid_grant: refresh token ölmüş (expire/revoke) → token'ı sil,
                # sıfırdan yetkilendir (tarayıcıda tek seferlik Gmail onayı).
                try:
                    os.remove(token_path)
                except OSError:
                    pass
                creds = None
        if not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    "Gmail OAuth client dosyası bulunamadı. "
                    f"`credentials.json` dosyasını `{CREDENTIALS_PATH}` konumuna koy "
                    "veya `.env` içinde GMAIL_CREDENTIALS_PATH ile yolunu belirt."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _headers_to_dict(headers: list[dict]) -> dict[str, str]:
    return {
        (item.get("name") or "").lower(): item.get("value") or ""
        for item in headers
    }


def _clean_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


def check_mail(
    query: str = "",
    max_results: int = 5,
    unread_only: bool = False,
    account: str | None = None,
) -> dict:
    """Gmail API ile son mailleri okur. Browser/debug profile kullanmaz."""
    active_account = _normalize_account(account)
    try:
        limit = max(1, min(int(max_results or 5), 10))
    except Exception:
        limit = 5

    q = (query or "").strip()
    if unread_only:
        q = f"is:unread {q}".strip()

    try:
        service = _get_service(active_account)
        listed = service.users().messages().list(
            userId="me",
            q=q,
            maxResults=limit,
        ).execute()
        messages = listed.get("messages", []) or []
        if not messages:
            return {
                "ok": True,
                "account": active_account,
                "messages": [],
                "summary": "Eşleşen mail bulunamadı.",
            }

        items = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = _headers_to_dict(detail.get("payload", {}).get("headers", []))
            items.append({
                "id": detail.get("id", ""),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", "(konu yok)"),
                "date": _clean_date(headers.get("date", "")),
                "snippet": detail.get("snippet", ""),
                "labels": detail.get("labelIds", []),
            })

        lines = []
        for idx, item in enumerate(items, start=1):
            unread = "okunmamış" if "UNREAD" in item.get("labels", []) else "okunmuş"
            lines.append(
                f"{idx}. {item['from']} - {item['subject']} ({item['date']}, {unread}): {item['snippet']}"
            )

        return {
            "ok": True,
            "account": active_account,
            "count": len(items),
            "messages": items,
            "summary": "\n".join(lines),
        }
    except HttpError as e:
        return {"ok": False, "error": f"Gmail API hatası: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Mail kontrolü başarısız: {e}"}


def _extract_body(payload: dict) -> str:
    """Mail payload'ından düz metin gövdesini çıkarır (recursive parts dahil)."""
    if not payload:
        return ""

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        try:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        except Exception:
            return ""

    # Multipart — text/plain bul
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text

    # text/plain yoksa text/html'i al (fallback)
    if mime_type == "text/html" and body_data:
        try:
            html = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
            # Basit HTML temizliği
            import re
            text = re.sub(r"<[^>]+>", "", html)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        except Exception:
            return ""

    return ""


def read_mail_body(message_id: str, account: str | None = None) -> dict:
    """Belirli bir mailin tam gövdesini okur. check_mail'den dönen id ile kullanılır."""
    if not message_id:
        return {"ok": False, "error": "message_id boş"}

    active_account = _normalize_account(account)
    try:
        service = _get_service(active_account)
        detail = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        headers = _headers_to_dict(detail.get("payload", {}).get("headers", []))
        body = _extract_body(detail.get("payload", {}))

        # Çok uzun gövdeleri 4000 karakterle sınırla
        if len(body) > 4000:
            body = body[:4000] + "\n\n[...mail çok uzun, ilk 4000 karakter gösterildi]"

        return {
            "ok": True,
            "account": active_account,
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", "(konu yok)"),
            "date": _clean_date(headers.get("date", "")),
            "body": body or "(boş gövde)",
        }
    except HttpError as e:
        return {"ok": False, "error": f"Gmail API hatası: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Mail okunamadı: {e}"}


def _send_via_api(to: str, subject: str, body: str, account: str | None = None) -> dict:
    active_account = _normalize_account(account)
    service = _get_service(active_account)
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject or ""
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {
        "ok": True,
        "from_account": active_account,
        "to": to,
        "subject": subject,
        "auto_send": True,
        "messageId": sent.get("id"),
    }


def _open_compose_url(to: str, subject: str, body: str, account: str | None = None) -> dict:
    active_account = _normalize_account(account)
    params = {
        "view": "cm",
        "fs": "1",
        "authuser": active_account,
        "to": to,
        "su": subject or "",
        "body": body,
    }
    url = "https://mail.google.com/mail/?" + urllib.parse.urlencode(params)
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["open", "-a", MAC_PREFERRED_BROWSER, url], capture_output=True, timeout=5)
            if r.returncode != 0:
                webbrowser.open(url, new=2)
        else:
            webbrowser.open(url, new=2)
    except Exception as e:
        return {"ok": False, "error": f"URL açılamadı: {e}"}
    return {
        "ok": True,
        "from_account": active_account,
        "to": to,
        "subject": subject,
        "auto_send": False,
        "note": "Manuel gönderim - kullanıcı 'Gönder'e basacak.",
    }


def send_mail(
    to: str,
    subject: str,
    body: str,
    auto_send: bool = False,
    account: str | None = None,
) -> dict:
    raw = (to or "").strip()
    target = resolve_email(raw) or ""
    if not target or "@" not in target:
        return {"ok": False, "error": f"'{raw}' için mail adresi bulunamadı. Rehberde yoksa tam adres gerek."}

    if not (body or "").strip():
        return {"ok": False, "error": "Mesaj gövdesi boş"}

    if not auto_send:
        return _open_compose_url(target, subject, body, account)

    try:
        return _send_via_api(target, subject, body, account)
    except HttpError as e:
        return {"ok": False, "error": f"Gmail API hatası: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Gönderim başarısız: {e}"}
