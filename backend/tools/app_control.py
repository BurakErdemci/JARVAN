"""Uygulama aç/kapat — cross-platform (Windows öncelikli, macOS fallback)."""
import platform
import shutil
import subprocess

APP_ALIASES = {
    "not defteri": {"win": "notepad.exe", "mac": "TextEdit"},
    "notepad": {"win": "notepad.exe", "mac": "TextEdit"},
    "hesap makinesi": {"win": "calc.exe", "mac": "Calculator"},
    "hesap": {"win": "calc.exe", "mac": "Calculator"},
    "calculator": {"win": "calc.exe", "mac": "Calculator"},
    "chrome": {"win": "chrome.exe", "mac": "Google Chrome"},
    "google chrome": {"win": "chrome.exe", "mac": "Google Chrome"},
    "firefox": {"win": "firefox.exe", "mac": "Firefox"},
    "edge": {"win": "msedge.exe", "mac": "Microsoft Edge"},
    "opera": {"win": "opera.exe", "mac": "Opera"},
    "opera gx": {"win": "opera.exe", "mac": "Opera GX"},
    "tarayıcı": {"win": "opera.exe", "mac": "Opera GX"},
    "tarayici": {"win": "opera.exe", "mac": "Opera GX"},
    "vscode": {"win": "Code.exe", "mac": "Visual Studio Code"},
    "visual studio code": {"win": "Code.exe", "mac": "Visual Studio Code"},
    "cursor": {"win": "Cursor.exe", "mac": "Cursor"},
    "unreal": {"win": "UnrealEditor.exe", "mac": "UnrealEditor"},
    "unity": {"win": "Unity.exe", "mac": "Unity"},
    "spotify": {"win": "Spotify.exe", "mac": "Spotify"},
    "discord": {"win": "Discord.exe", "mac": "Discord"},
    "steam": {"win": "steam.exe", "mac": "Steam"},
    "obs": {"win": "obs64.exe", "mac": "OBS"},
    "cs2": {"win": "cs2.exe", "mac": None},
    "csgo": {"win": "cs2.exe", "mac": None},
    "terminal": {"win": "cmd.exe", "mac": "Terminal"},
    "whatsapp": {"win": "WhatsApp.exe", "mac": "WhatsApp"},
    "telegram": {"win": "Telegram.exe", "mac": "Telegram"},
    "slack": {"win": "slack.exe", "mac": "Slack"},
    "finder": {"win": None, "mac": "Finder"},
    "notion": {"win": "Notion.exe", "mac": "Notion"},
    "safari": {"win": None, "mac": "Safari"},
}

IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"


def _resolve(name: str) -> str | None:
    key = name.strip().lower()
    if key in APP_ALIASES:
        entry = APP_ALIASES[key]
        return entry["win"] if IS_WIN else entry["mac"]
    if IS_MAC:
        return name.strip().title()
    # Windows: taskkill /IM tam isim ister, .exe yoksa ekle
    raw = name.strip()
    if IS_WIN and raw and not raw.lower().endswith(".exe"):
        return raw + ".exe"
    return raw


def open_app(name: str) -> dict:
    target = _resolve(name)
    if not target:
        return {"ok": False, "error": f"'{name}' bu platformda tanımlı değil"}

    try:
        if IS_WIN:
            subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        elif IS_MAC:
            subprocess.Popen(["open", "-a", target])
        else:
            if not shutil.which(target):
                return {"ok": False, "error": f"'{target}' PATH'te bulunamadı"}
            subprocess.Popen([target])
        return {"ok": True, "opened": target}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def close_app(name: str) -> dict:
    target = _resolve(name)
    if not target:
        return {"ok": False, "error": f"'{name}' tanımlı değil"}

    try:
        if IS_WIN:
            result = subprocess.run(
                ["taskkill", "/IM", target, "/F"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return {"ok": False, "error": result.stderr.strip() or "kapatılamadı"}
        elif IS_MAC:
            try:
                result = subprocess.run(
                    ["osascript", "-e", f'tell application "{target}" to quit'],
                    capture_output=True, text=True, timeout=2,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or "osascript failed")
            except (subprocess.TimeoutExpired, RuntimeError):
                pk = subprocess.run(
                    ["pkill", "-i", "-f", target],
                    capture_output=True, timeout=3,
                )
                if pk.returncode not in (0, 1):
                    return {"ok": False, "error": f"pkill çalışmadı: {target}"}
        else:
            subprocess.run(["pkill", "-f", target], capture_output=True, timeout=5)
        return {"ok": True, "closed": target}
    except Exception as e:
        return {"ok": False, "error": str(e)}
