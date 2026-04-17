import re
from PIL import Image

from ai import local_llm, assistant


# Ekran bağlamı gerektiren ipuçları — bunlar geçerse vision aktif.
SCREEN_HINTS = [
    r"\bşu\b", r"\bbu\b", r"\bşura", r"\bbura", r"\borada\b", r"\bburada\b",
    r"\bekran", r"\bgörüyor", r"\bgörebiliyor",
    r"\bnerede\b", r"\bhangi\b",
]

# Teknik/derinlikli cevap gerektiren ipuçları — cloud'a git (daha güçlü model).
TECHNICAL_HINTS = [
    r"\bhata\b", r"\berror\b", r"\bexception\b", r"\bcrash\b",
    r"\bkod\b", r"\bfonksiyon\b", r"\bclass\b", r"\bblueprint\b",
    r"\bunreal\b", r"\bunity\b", r"\bshader\b", r"\bdebug\b",
    r"\bnasıl yap", r"\bneden çalış", r"\bçalışmıyor\b",
]


def _match(patterns, text):
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def route(transcript: str, screenshot: Image.Image) -> tuple[str, str]:
    """Üç katmanlı yönlendirme:
      1. Teknik soru → cloud (Gemini 3 Flash + vision)
      2. Ekran bahsi → local vision (Qwen3-VL + screenshot)
      3. Sade sohbet → local text (Qwen3-VL, ekran yok)

    Returns: (label, response)
    """
    text = transcript.lower()
    tech_hit = _match(TECHNICAL_HINTS, text)
    screen_hit = _match(SCREEN_HINTS, text)

    if tech_hit:
        try:
            return f"cloud:gemini-3-flash (teknik: '{tech_hit}')", assistant.ask(transcript, screenshot)
        except Exception as e:
            print(f"[router] cloud hata, local'e düşüyor: {e}")
            return "local:qwen3-vl (cloud hata)", local_llm.ask(transcript, screenshot)

    if screen_hit:
        return f"local:qwen3-vl + vision (ekran: '{screen_hit}')", local_llm.ask(transcript, screenshot)

    return "local:qwen3-vl (sohbet)", local_llm.ask(transcript)


if __name__ == "__main__":
    from screen.capture import capture_screenshot_pil

    q = input("Test sorusu: ")
    shot = capture_screenshot_pil()
    label, response = route(q, shot)
    print(f"\n[{label}] Jarvan: {response}")
