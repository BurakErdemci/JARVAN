"""Gmail — API tabanlı gönderim (OAuth), fallback olarak compose URL."""
import base64
import os
import sys
import subprocess
import urllib.parse
import webbrowser
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from tools.contacts import resolve_email

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(_BASE, "credentials.json")
TOKEN_PATH = os.path.join(_BASE, "token.json")

MAC_PREFERRED_BROWSER = "Google Chrome"


def _get_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"credentials.json bulunamadı: {CREDENTIALS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _send_via_api(to: str, subject: str, body: str) -> dict:
    service = _get_service()
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject or ""
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"ok": True, "to": to, "subject": subject, "auto_send": True, "messageId": sent.get("id")}


def _open_compose_url(to: str, subject: str, body: str) -> dict:
    params = {"view": "cm", "fs": "1", "to": to, "su": subject or "", "body": body}
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
    return {"ok": True, "to": to, "subject": subject, "auto_send": False, "note": "Manuel gönderim — kullanıcı 'Gönder'e basacak."}


def send_mail(to: str, subject: str, body: str, auto_send: bool = False) -> dict:
    raw = (to or "").strip()
    target = resolve_email(raw) or ""
    if not target or "@" not in target:
        return {"ok": False, "error": f"'{raw}' için mail adresi bulunamadı. Rehberde yoksa tam adres gerek."}

    if not (body or "").strip():
        return {"ok": False, "error": "Mesaj gövdesi boş"}

    if not auto_send:
        return _open_compose_url(target, subject, body)

    try:
        return _send_via_api(target, subject, body)
    except HttpError as e:
        return {"ok": False, "error": f"Gmail API hatası: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Gönderim başarısız: {e}"}
