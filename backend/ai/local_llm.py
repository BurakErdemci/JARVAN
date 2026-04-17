from io import BytesIO
from typing import Optional

import ollama
from PIL import Image

MODEL = "qwen3-vl:8b"

SYSTEM_PROMPT = """Sen Jarvan'sın — bir developer'ın kişisel AI asistanı.

Kurallar:
- Kısa ve doğal konuş, sohbet eder gibi. Madde madde listeleme.
- Türkçe konuş.
- "Merhaba, nasıl yardımcı olabilirim?" gibi gereksiz girişler yapma.
- Ekran görüntüsü verildiyse ona göre cevap ver. Verilmediyse sadece metne odaklan."""


def _image_to_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def ask(transcript: str, screenshot: Optional[Image.Image] = None) -> str:
    """Qwen3-VL — opsiyonel ekran görüntüsüyle yanıt üretir."""
    user_msg = {"role": "user", "content": transcript}
    if screenshot is not None:
        user_msg["images"] = [_image_to_bytes(screenshot)]

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            user_msg,
        ],
        think=False,
        options={"temperature": 0.7},
    )
    return response["message"]["content"].strip()


if __name__ == "__main__":
    from screen.capture import capture_screenshot_pil

    q = input("Test sorusu: ")
    use_screen = input("Ekran ver? (e/h): ").strip().lower() == "e"
    shot = capture_screenshot_pil() if use_screen else None
    print(f"\nJarvan (local): {ask(q, shot)}")
