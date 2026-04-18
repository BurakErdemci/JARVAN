from modes.prompts import UNREAL_PROMPT, UNITY_PROMPT, CODE_PROMPT, DEFAULT_PROMPT

try:
    import pygetwindow as gw
except Exception:
    gw = None

WINDOW_MODE_MAP = [
    (["Unreal", "UE5", "UE4"], "unreal", UNREAL_PROMPT),
    (["Unity"], "unity", UNITY_PROMPT),
    (["Visual Studio Code", "Code", "Cursor", "PyCharm", "Rider", "CLion"], "code", CODE_PROMPT),
]


def get_active_window_title() -> str:
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
