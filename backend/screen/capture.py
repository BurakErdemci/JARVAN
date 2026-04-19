import mss
import base64
import sys
import os
import platform
import ctypes
from ctypes import byref, Structure, c_double, c_uint32
from PIL import Image
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SCREEN_MONITOR_INDEX


def _pick_monitor(sct):
    idx = SCREEN_MONITOR_INDEX if SCREEN_MONITOR_INDEX < len(sct.monitors) else 1
    return sct.monitors[idx]


def _get_monitor_bounds_generic(mon: dict) -> dict:
    """Generic fallback: tüm desktop için tek bir scale varsayar."""
    import pyautogui

    logical_w, logical_h = pyautogui.size()

    with mss.mss() as sct:
        virtual = sct.monitors[0]

    physical_w = max(int(virtual["width"]), 1)
    physical_h = max(int(virtual["height"]), 1)
    scale_x = physical_w / max(int(logical_w), 1)
    scale_y = physical_h / max(int(logical_h), 1)

    def _to_logical(value: int, scale: float) -> int:
        if scale <= 0:
            return int(value)
        return int(round(value / scale))

    return {
        "left": _to_logical(int(mon["left"]), scale_x),
        "top": _to_logical(int(mon["top"]), scale_y),
        "width": max(_to_logical(int(mon["width"]), scale_x), 1),
        "height": max(_to_logical(int(mon["height"]), scale_y), 1),
        "physical_left": int(mon["left"]),
        "physical_top": int(mon["top"]),
        "physical_width": int(mon["width"]),
        "physical_height": int(mon["height"]),
        "scale_x": scale_x,
        "scale_y": scale_y,
        "source": "generic",
    }


def _get_monitor_bounds_macos(mon: dict) -> dict | None:
    """macOS'ta her ekran için ayrı logical/pixel scale çöz.

    CoreGraphics `bounds` değerleri point/logical uzayda, `pixels` ise fiziksel
    piksel uzayında gelir. `mss` ile seçilen monitörü fiziksel çözünürlüğüne göre
    eşleyip pyautogui için doğru logical sınırları çıkarırız.
    """
    class CGPoint(Structure):
        _fields_ = [("x", c_double), ("y", c_double)]

    class CGSize(Structure):
        _fields_ = [("width", c_double), ("height", c_double)]

    class CGRect(Structure):
        _fields_ = [("origin", CGPoint), ("size", CGSize)]

    try:
        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    except OSError:
        return None

    max_displays = 16
    active = (c_uint32 * max_displays)()
    count = c_uint32(0)

    cg.CGGetActiveDisplayList.argtypes = [c_uint32, ctypes.POINTER(c_uint32), ctypes.POINTER(c_uint32)]
    cg.CGGetActiveDisplayList.restype = ctypes.c_int32
    cg.CGDisplayBounds.argtypes = [c_uint32]
    cg.CGDisplayBounds.restype = CGRect
    cg.CGDisplayPixelsWide.argtypes = [c_uint32]
    cg.CGDisplayPixelsWide.restype = c_uint32
    cg.CGDisplayPixelsHigh.argtypes = [c_uint32]
    cg.CGDisplayPixelsHigh.restype = c_uint32

    err = cg.CGGetActiveDisplayList(max_displays, active, byref(count))
    if err != 0:
        return None

    target_w = int(mon["width"])
    target_h = int(mon["height"])
    candidates = []

    for i in range(count.value):
        display_id = active[i]
        bounds = cg.CGDisplayBounds(display_id)
        pixels_w = int(cg.CGDisplayPixelsWide(display_id))
        pixels_h = int(cg.CGDisplayPixelsHigh(display_id))
        logical_w = max(int(round(bounds.size.width)), 1)
        logical_h = max(int(round(bounds.size.height)), 1)
        score = abs(pixels_w - target_w) + abs(pixels_h - target_h)
        candidates.append({
            "display_id": int(display_id),
            "left": int(round(bounds.origin.x)),
            "top": int(round(bounds.origin.y)),
            "width": logical_w,
            "height": logical_h,
            "physical_left": int(mon["left"]),
            "physical_top": int(mon["top"]),
            "physical_width": pixels_w,
            "physical_height": pixels_h,
            "scale_x": pixels_w / logical_w,
            "scale_y": pixels_h / logical_h,
            "score": score,
        })

    if not candidates:
        return None

    best = min(candidates, key=lambda item: item["score"])
    best["source"] = "macos-coregraphics"
    return best


def capture_screenshot() -> str:
    """Ekran görüntüsü alır, base64 encoded JPEG string döner."""
    with mss.mss() as sct:
        monitor = _pick_monitor(sct)
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def capture_screenshot_pil() -> Image.Image:
    """Ekran görüntüsünü PIL Image olarak döner."""
    with mss.mss() as sct:
        monitor = _pick_monitor(sct)
        screenshot = sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def get_monitor_bounds() -> dict:
    """Aktif monitörün mantıksal koordinatlarını döner.

    `mss` fiziksel piksel, `pyautogui` ise mantıksal koordinat kullanır.
    Computer use ekran görüntüsünü `mss` ile aldığı için seçili monitörün fiziksel
    sınırlarını, pyautogui için kullanılabilir mantıksal sınırlara dönüştürürüz.
    """
    with mss.mss() as sct:
        mon = _pick_monitor(sct)

    if platform.system() == "Darwin":
        native = _get_monitor_bounds_macos(mon)
        if native:
            return native

    return _get_monitor_bounds_generic(mon)


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
