import re
from PIL import Image

from ai import assistant
from modes.detector import get_active_mode

SCREEN_HINTS = [
    r"\bşu\b", r"\bbu\b", r"\bşura", r"\bbura", r"\borada\b", r"\bburada\b",
    r"\bekran", r"\bgörüyor", r"\bgörebiliyor",
    r"\bnerede\b", r"\bhangi\b",
]

TECHNICAL_HINTS = [
    r"\bhata\b", r"\berror\b", r"\bexception\b", r"\bcrash\b",
    r"\bkod\b", r"\bfonksiyon\b", r"\bclass\b", r"\bblueprint\b",
    r"\bunreal\b", r"\bunity\b", r"\bshader\b", r"\bdebug\b",
    r"\bnasıl yap", r"\bneden çalış", r"\bçalışmıyor\b",
    r"\bkontrol et\b", r"\baç\b", r"\bgönder\b", r"\byaz\b",
]


def _match(patterns, text):
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def route(transcript: str, screenshot: Image.Image) -> tuple[str, str]:
    """
    Teknik/vision → Gemini Flash (güçlü, 20 RPD)
    Sohbet/basit  → Gemini Flash Lite (500 RPD), Flash'a fallback
    """
    mode, system_prompt = get_active_mode()
    text = transcript.lower()
    screen_hit = _match(SCREEN_HINTS, text)
    tech_hit = _match(TECHNICAL_HINTS, text)

    is_technical_mode = mode in ("unreal", "unity", "code")
    needs_flash = screen_hit is not None or tech_hit is not None or is_technical_mode

    if needs_flash:
        use_vision = screen_hit is not None
        try:
            return f"flash [{mode}]", assistant.ask(transcript, screenshot if use_vision else None, system_prompt, use_lite=False)
        except Exception as e:
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                try:
                    return f"flash-lite-fallback [{mode}]", assistant.ask(transcript, None, system_prompt, use_lite=True)
                except Exception as e2:
                    return "hata", f"Yanıt alınamadı: {e2}"
            return "hata", f"Yanıt alınamadı: {e}"
    else:
        try:
            return f"flash-lite [{mode}]", assistant.ask(transcript, None, system_prompt, use_lite=True)
        except Exception as e:
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                try:
                    return f"flash-fallback [{mode}]", assistant.ask(transcript, None, system_prompt, use_lite=False)
                except Exception as e2:
                    return "hata", f"Yanıt alınamadı: {e2}"
            return "hata", f"Yanıt alınamadı: {e}"


if __name__ == "__main__":
    from screen.capture import capture_screenshot_pil

    q = input("Test sorusu: ")
    shot = capture_screenshot_pil()
    label, response = route(q, shot)
    print(f"\n[{label}] Jarvan: {response}")
