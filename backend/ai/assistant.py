import google.generativeai as genai
import sys
import os
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)


FLASH_MODEL = "gemini-3-flash-preview"
FLASH_LITE_MODEL = "gemini-3.1-flash-lite-preview"


def ask(transcript: str, screenshot: Image.Image = None, system_prompt: str = "", use_lite: bool = False) -> str:
    """Ses transkripsiyonu + opsiyonel ekran görüntüsü → Gemini yanıtı."""
    model_name = FLASH_LITE_MODEL if use_lite else FLASH_MODEL
    model = genai.GenerativeModel(model_name)

    content = [system_prompt, f"Kullanıcı şunu dedi: {transcript}"]
    if screenshot is not None:
        content.append(screenshot)

    response = model.generate_content(content)
    return response.text.strip()


if __name__ == "__main__":
    from screen.capture import capture_screenshot_pil

    transcript = input("Test sorusu: ")
    print("Ekran görüntüsü alınıyor...")
    screenshot = capture_screenshot_pil()
    print("Gemini'ye gönderiliyor...")
    response = ask(transcript, screenshot)
    print(f"\nJarvan: {response}")
