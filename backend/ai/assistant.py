import google.generativeai as genai
import sys
import os
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Sen Jarvan'sın — bir developer'ın kişisel AI asistanı.

Kurallar:
- Kısa ve net konuş. Uzun açıklamalar yapma.
- Ekranda ne görüyorsan ona göre yanıt ver.
- Türkçe konuş.
- Eğer soru teknikse (kod, hata, araç) doğrudan cevaba gir.
- "Merhaba, nasıl yardımcı olabilirim?" gibi gereksiz girişler yapma."""


def ask(transcript: str, screenshot: Image.Image) -> str:
    """Ses transkripsiyonu + ekran görüntüsü → Gemini yanıtı."""
    model = genai.GenerativeModel("gemini-3-flash-preview")

    response = model.generate_content([
        SYSTEM_PROMPT,
        f"Kullanıcı şunu dedi: {transcript}",
        screenshot,
    ])

    return response.text.strip()


if __name__ == "__main__":
    from screen.capture import capture_screenshot_pil

    transcript = input("Test sorusu: ")
    print("Ekran görüntüsü alınıyor...")
    screenshot = capture_screenshot_pil()
    print("Gemini'ye gönderiliyor...")
    response = ask(transcript, screenshot)
    print(f"\nJarvan: {response}")
