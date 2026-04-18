"""WhatsApp mesaj gönderme — URL scheme + pyautogui Enter."""
import os
import sys
import time
import urllib.parse
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MY_WHATSAPP
from tools.contacts import resolve_phone


def _whatsapp_running() -> bool:
    try:
        if sys.platform == "darwin":
            r = subprocess.run(
                ["osascript", "-e", 'application "WhatsApp" is running'],
                capture_output=True, timeout=2, text=True,
            )
            return r.stdout.strip().lower() == "true"
        elif sys.platform.startswith("win"):
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
        if sys.platform == "darwin":
            subprocess.Popen(["open", url])
        elif sys.platform.startswith("win"):
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception as e:
        return {"ok": False, "error": f"URL açılamadı: {e}"}

    time.sleep(5.0 if not was_running else 2.5)

    try:
        if sys.platform == "darwin":
            subprocess.run(
                ["osascript", "-e", 'tell application "WhatsApp" to activate'],
                capture_output=True, timeout=3,
            )
            time.sleep(0.4)
            subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to keystroke return'],
                capture_output=True, timeout=3,
            )
        else:
            import pyautogui
            pyautogui.press("enter")
    except Exception as e:
        return {"ok": False, "error": f"Enter basılamadı: {e}", "opened": True}

    return {"ok": True, "sent_to": target, "message": message}
