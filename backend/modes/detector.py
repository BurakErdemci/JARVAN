from modes.prompts import UNREAL_PROMPT, UNITY_PROMPT, CODE_PROMPT, DEFAULT_PROMPT

import platform
import subprocess

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

try:
    if IS_WIN:
        import pygetwindow as gw
    else:
        gw = None
except Exception:
    gw = None

WINDOW_MODE_MAP = [
    (["Unreal", "UE5", "UE4"], "unreal", UNREAL_PROMPT),
    (["Unity"], "unity", UNITY_PROMPT),
    (["Visual Studio Code", "Code", "Cursor", "PyCharm", "Rider", "CLion"], "code", CODE_PROMPT),
]


def get_active_window_title() -> str:
    if IS_WIN:
        if gw is None:
            return ""
        try:
            window = gw.getActiveWindow()
            if not window:
                return ""
            title = window.title
            if callable(title):
                title = title()
            return title or ""
        except Exception:
            return ""
    elif IS_MAC:
        try:
            # 1. Öncelikli olarak aktif pencerenin başlığını (window title) almaya çalış
            script_title = 'tell application "System Events" to tell (first process whose frontmost is true) to get value of attribute "AXTitle" of window 1'
            title = subprocess.check_output(['osascript', '-e', script_title], stderr=subprocess.DEVNULL).decode().strip()
            if title:
                return title
        except Exception:
            pass
        try:
            # 2. Hata verirse (Erişilebilirlik izni yoksa vb.) aktif süreç (proses) adını dön
            script_proc = 'tell application "System Events" to get name of first process whose frontmost is true'
            return subprocess.check_output(['osascript', '-e', script_proc], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return ""
    return ""


def get_active_mode() -> tuple[str, str]:
    """Aktif pencereye göre mod ve system prompt döner.

    Returns: (mode_name, system_prompt)
    """
    title = get_active_window_title()

    for keywords, mode_name, prompt in WINDOW_MODE_MAP:
        for kw in keywords:
            if kw.lower() in title.lower():
                return mode_name, prompt

    return "default", DEFAULT_PROMPT


if __name__ == "__main__":
    mode, _ = get_active_mode()
    title = get_active_window_title() or "?"
    print(f"Aktif pencere: {title}")
    print(f"Mod: {mode}")
