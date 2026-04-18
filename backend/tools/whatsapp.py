"""WhatsApp mesaj gönderme — URL scheme + pyautogui Enter."""
import os
import sys
import time
import urllib.parse
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MY_WHATSAPP


def send_whatsapp(message: str, phone: str | None = None) -> dict:
    target = (phone or MY_WHATSAPP or "").strip().replace("+", "").replace(" ", "")
    if not target:
        return {"ok": False, "error": "Telefon numarası yok (MY_WHATSAPP .env'de tanımlı değil)"}

    if not message or not message.strip():
        return {"ok": False, "error": "Mesaj boş"}

    url = f"whatsapp://send?phone={target}&text={urllib.parse.quote(message)}"

    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", url])
        elif sys.platform.startswith("win"):
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception as e:
        return {"ok": False, "error": f"URL açılamadı: {e}"}

    time.sleep(2.5)

    try:
        if sys.platform == "darwin":
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
