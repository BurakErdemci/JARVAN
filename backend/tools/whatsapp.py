"""WhatsApp mesaj gönderme — URL scheme + pyautogui Enter (Windows Optimize)."""
import time
import urllib.parse
import subprocess
import webbrowser

import pygetwindow as gw
import pyautogui

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MY_WHATSAPP
from tools.contacts import resolve_phone

def _whatsapp_running() -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WhatsApp.exe"],
            capture_output=True, timeout=2, text=True,
        )
        return "WhatsApp.exe" in r.stdout
    except Exception:
        pass
    return False

def send_whatsapp(message: str, phone: str | None = None) -> dict:
    if not message or not message.strip():
        return {"ok": False, "error": "Mesaj boş"}

    raw = (phone or "").strip()
    if not raw:
        target = (MY_WHATSAPP or "").replace("+", "").replace(" ", "")
    else:
        resolved = resolve_phone(raw)
        if not resolved:
            return {
                "ok": False,
                "error": f"'{raw}' rehberde yok. contacts_phones.json'a ülke koduyla ekle (örn. \"cengiz\": \"905321234567\") veya kullanıcıya numarayı sor.",
            }
        target = resolved

    if not target:
        return {"ok": False, "error": "Telefon numarası yok (MY_WHATSAPP .env'de tanımlı değil)"}

    url = f"whatsapp://send?phone={target}&text={urllib.parse.quote(message)}"

    was_running = _whatsapp_running()

    try:
        webbrowser.open(url)
    except Exception as e:
        return {"ok": False, "error": f"URL açılamadı: {e}"}

    time.sleep(5.0 if not was_running else 3.0)

    try:
        wins = [w for w in gw.getAllWindows() if "whatsapp" in w.title.lower()]
        if wins:
            wins[0].activate()
            time.sleep(0.5)
        pyautogui.press("enter")
    except Exception as e:
        return {"ok": False, "error": f"Enter basılamadı: {e}", "opened": True}

    return {"ok": True, "sent_to": target, "message": message}
