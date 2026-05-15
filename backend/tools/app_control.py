"""Uygulama aç/kapat — cross-platform (Windows öncelikli, macOS fallback)."""
import platform
import shutil
import subprocess

APP_ALIASES = {
    "not defteri": "notepad.exe",
    "notepad": "notepad.exe",
    "hesap makinesi": "calc.exe",
    "hesap": "calc.exe",
    "calculator": "calc.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "opera": "opera.exe",
    "opera gx": "opera.exe",
    "tarayıcı": "opera.exe",
    "tarayici": "opera.exe",
    "vscode": "Code.exe",
    "visual studio code": "Code.exe",
    "cursor": "Cursor.exe",
    "unreal": "UnrealEditor.exe",
    "unity": "Unity.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "steam": "steam.exe",
    "obs": "obs64.exe",
    "cs2": "cs2.exe",
    "csgo": "cs2.exe",
    "terminal": "cmd.exe",
    "whatsapp": "WhatsApp.exe",
    "telegram": "Telegram.exe",
    "slack": "slack.exe",
    "notion": "Notion.exe",
}

def _resolve(name: str) -> str | None:
    key = name.strip().lower()
    if key in APP_ALIASES:
        return APP_ALIASES[key]
    raw = name.strip()
    if raw and not raw.lower().endswith(".exe"):
        return raw + ".exe"
    return raw

def open_app(name: str) -> dict:
    target = _resolve(name)
    if not target:
        return {"ok": False, "error": f"'{name}' tanımlı değil"}

    try:
        subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        return {"ok": True, "opened": target}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def close_app(name: str) -> dict:
    target = _resolve(name)
    if not target:
        return {"ok": False, "error": f"'{name}' tanımlı değil"}

    try:
        result = subprocess.run(
            ["taskkill", "/IM", target, "/F"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr.strip() or "kapatılamadı"}
        return {"ok": True, "closed": target}
    except Exception as e:
        return {"ok": False, "error": str(e)}
