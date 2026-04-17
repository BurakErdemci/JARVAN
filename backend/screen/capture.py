import mss
import base64
import sys
import os
from PIL import Image
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def capture_screenshot() -> str:
    """Ekran görüntüsü alır, base64 encoded JPEG string döner."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 0 = tüm ekranlar, 1 = birinci ekran
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def capture_screenshot_pil() -> Image.Image:
    """Ekran görüntüsünü PIL Image olarak döner (Gemini için)."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


if __name__ == "__main__":
    import time
    print("Ekran görüntüsü alınıyor...")
    start = time.time()
    b64 = capture_screenshot()
    elapsed = (time.time() - start) * 1000
    print(f"Başarılı — {len(b64)} byte base64, {elapsed:.1f}ms sürdü")
    print("screenshot.jpg olarak kaydediliyor...")
    img = capture_screenshot_pil()
    img.save("screenshot.jpg")
    print("Kaydedildi. screenshot.jpg dosyasını aç ve kontrol et.")
