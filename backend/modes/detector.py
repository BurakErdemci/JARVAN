import pygetwindow as gw
from modes.prompts import UNREAL_PROMPT, UNITY_PROMPT, CODE_PROMPT, DEFAULT_PROMPT

WINDOW_MODE_MAP = [
    (["Unreal", "UE5", "UE4"], "unreal", UNREAL_PROMPT),
    (["Unity"], "unity", UNITY_PROMPT),
    (["Visual Studio Code", "Code", "Cursor", "PyCharm", "Rider", "CLion"], "code", CODE_PROMPT),
]


def get_active_mode() -> tuple[str, str]:
    """Aktif pencereye göre mod ve system prompt döner.

    Returns: (mode_name, system_prompt)
    """
    try:
        window = gw.getActiveWindow()
        title = window.title if window else ""
    except Exception:
        title = ""

    for keywords, mode_name, prompt in WINDOW_MODE_MAP:
        for kw in keywords:
            if kw.lower() in title.lower():
                return mode_name, prompt

    return "default", DEFAULT_PROMPT


if __name__ == "__main__":
    mode, _ = get_active_mode()
    try:
        import pygetwindow as gw
        title = gw.getActiveWindow().title
    except Exception:
        title = "?"
    print(f"Aktif pencere: {title}")
    print(f"Mod: {mode}")
