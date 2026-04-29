"""Deterministic Spotify actions for common playback tasks on Windows."""

import asyncio
import time
import urllib.parse
import subprocess
import pyautogui
import pygetwindow as gw
from tools.app_control import open_app

def _close_spotify_file_dialogs():
    """Spotify kapak düzenleme gibi dosya seçicileri açıksa kapat."""
    try:
        dialog_titles = ("aç", "open", "dosya", "file")
        wins = [w for w in gw.getAllWindows() if w.title and any(t in w.title.lower() for t in dialog_titles)]
        for win in wins:
            if win.width > 400 and win.height > 250:
                win.activate()
                time.sleep(0.1)
                pyautogui.press("esc")
                time.sleep(0.2)
    except Exception:
        pass

def _dismiss_spotify_overlays():
    """Açık Spotify menüsü/modali varsa kapat."""
    try:
        pyautogui.press("esc")
        time.sleep(0.15)
    except Exception:
        pass

def _focus_spotify() -> bool:
    """Spotify penceresini öne getirir, büyütür ve odaklar."""
    try:
        # Görünmez/arka plan Spotify pencerelerini elemek için genişlik filtresi (width > 500)
        wins = [w for w in gw.getAllWindows() if "spotify" in w.title.lower() and w.title != "" and w.width > 500]
        if wins:
            win = wins[0]
            if win.isMinimized:
                win.restore()
            if not win.isMaximized:
                win.maximize()
                
            import ctypes
            # Windows Focus Hırsızlığı Korumasını aşmak için Alt tuşunu simüle ediyoruz
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0) # Alt down
            win.activate()
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0) # Alt up
            
            # Ekstra garanti: Pencerenin güvenli başlık çubuğuna bir kez fiziksel tıkla
            safe_x = win.left + 300
            safe_y = win.top + 15
            pyautogui.click(safe_x, safe_y)
            return True
        return False
    except Exception:
        return False

def _click_coords(x_ratio: float, y_ratio: float):
    """Belirtilen oranlara göre Spotify ekranında fareyi hareket ettirip çift tıklar."""
    wins = [w for w in gw.getAllWindows() if "spotify" in w.title.lower() and w.title != "" and w.width > 500]
    if not wins:
        return
    win = wins[0]
    click_x = win.left + int(win.width * x_ratio)
    click_y = win.top + int(win.height * y_ratio)
    
    # Fareyi yumuşakça götür ki Spotify hover (üzerine gelme) efektini algılasın
    pyautogui.moveTo(click_x, click_y, duration=0.2)
    time.sleep(0.1)
    pyautogui.click()
    time.sleep(0.05)
    pyautogui.click()

def _click_top_result_card() -> bool:
    """Arama sonuçlarındaki Top Result kartına girer."""
    wins = [w for w in gw.getAllWindows() if "spotify" in w.title.lower() and w.title != "" and w.width > 500]
    if not wins:
        return False
    win = wins[0]
    x = win.left + int(win.width * 0.16)
    y = win.top + int(win.height * 0.33)
    pyautogui.moveTo(x, y, duration=0.2)
    time.sleep(0.05)
    pyautogui.click()
    time.sleep(0.05)
    pyautogui.click()
    return True

def _find_and_click_green_play_button() -> bool:
    """Ekranda Spotify'ın büyük yeşil çalma butonunu renk blob'u olarak bulup tıklar."""
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

    wins = [w for w in gw.getAllWindows() if "spotify" in w.title.lower() and w.title != ""]
    if not wins:
        return False
    win = wins[0]
    
    # Ana play butonu büyük, dolu, yuvarlak bir yeşil blob'dur.
    # Yeşil playlist yazıları ve shuffle ikonu küçük kaldığı için component filtresinden elenir.
    start_y = win.top + int(win.height * 0.25)
    end_y = win.top + int(win.height * 0.55)
    start_x = win.left + int(win.width * 0.02)
    end_x = win.left + int(win.width * 0.45)
    
    try:
        region = (start_x, start_y, end_x - start_x, end_y - start_y)
        import mss
        from PIL import Image

        with mss.mss() as sct:
            shot = sct.grab({
                "left": int(region[0]),
                "top": int(region[1]),
                "width": int(region[2]),
                "height": int(region[3]),
            })
            screenshot = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        width, height = screenshot.size
        
        green = set()
        for y in range(0, height, 2):
            for x in range(0, width, 2):
                r, g, b = screenshot.getpixel((x, y))
                if g > 140 and g > r + 30 and g > b + 20 and r < 130 and b < 140:
                    green.add((x, y))

        components = []
        while green:
            stack = [green.pop()]
            xs = []
            ys = []
            area = 0
            while stack:
                x, y = stack.pop()
                xs.append(x)
                ys.append(y)
                area += 1
                for nx, ny in ((x + 2, y), (x - 2, y), (x, y + 2), (x, y - 2)):
                    if (nx, ny) in green:
                        green.remove((nx, ny))
                        stack.append((nx, ny))

            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            blob_w = max_x - min_x + 2
            blob_h = max_y - min_y + 2
            if area >= 250 and blob_w >= 34 and blob_h >= 34:
                components.append((area, min_x, min_y, max_x, max_y))

        if not components:
            return False

        area, min_x, min_y, max_x, max_y = max(components, key=lambda item: item[0])
        target_x = start_x + ((min_x + max_x) // 2)
        target_y = start_y + ((min_y + max_y) // 2)

        pyautogui.moveTo(target_x, target_y, duration=0.2)
        time.sleep(0.1)
        pyautogui.click()
        return True
    except Exception as e:
        print(f"Green button tarama hatası: {e}")
        return False
        
    return False

def _normalize_query(track: str, artist: str | None = None) -> str:
    q = (track or "").strip()
    if artist and artist.strip():
        q = f"{q} {artist.strip()}"
    return q.strip()

async def control_spotify(action: str) -> dict:
    """Spotify'ı durdurur, devam ettirir veya bir sonraki/önceki şarkıya geçer."""
    action = action.lower()
    if action in ["pause", "play", "toggle"]:
        pyautogui.press("playpause")
    elif action == "next":
        pyautogui.press("nexttrack")
    elif action == "previous":
        pyautogui.press("prevtrack")
    else:
        return {"ok": False, "error": f"Geçersiz aksiyon: {action}"}
        
    return {"ok": True, "result": f"Spotify: {action} komutu gönderildi."}

async def play_spotify_track(
    track: str | None = None, 
    artist: str | None = None,
    is_playlist: bool = False,
    shuffle: bool = False
) -> dict:
    if not track:
        return await control_spotify("play")
        
    query = _normalize_query(track, artist)
    if not query:
        return {"ok": False, "error": "şarkı adı boş"}

    await asyncio.to_thread(_close_spotify_file_dialogs)
    await asyncio.to_thread(_dismiss_spotify_overlays)

    # 1. Spotify'ı aç
    opened = await asyncio.to_thread(open_app, "spotify")
    if not opened.get("ok"):
        return {"ok": False, "error": opened.get("error", "Spotify açılamadı")}
    await asyncio.sleep(1.2)

    try:
        # 2. URI ile DOĞRUDAN arama sayfasına git. 
        url = f"spotify:search:{urllib.parse.quote(query)}"
        subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        await asyncio.sleep(2.5) # Sonuçların yüklenmesini bekle
        
        # 3. Spotify'ı öne getir
        await asyncio.to_thread(_close_spotify_file_dialogs)
        await asyncio.to_thread(_dismiss_spotify_overlays)
        await asyncio.to_thread(_focus_spotify)
        await asyncio.sleep(0.5)

        played = await asyncio.to_thread(_find_and_click_green_play_button)
        if played:
            return {"ok": True, "result": f'Spotify\'da "{query}" çalınıyor.'}
        if is_playlist:
            entered = await asyncio.to_thread(_click_top_result_card)
            if not entered:
                return {"ok": False, "error": "Spotify arama sonucundaki playlist kartı bulunamadı."}
            await asyncio.sleep(1.5)
            played = await asyncio.to_thread(_find_and_click_green_play_button)
            if not played:
                return {"ok": False, "error": "Playlist sayfası açıldı ama yeşil çalma butonu bulunamadı."}
            return {"ok": True, "result": f'Spotify\'da "{query}" çalınıyor.'}

        # 4. Top Result kartına çift tıkla ve detay sayfasını aç (Şarkı/Liste fark etmez)
        wins = [w for w in gw.getAllWindows() if "spotify" in w.title.lower() and w.title != "" and w.width > 500]
        if wins:
            win = wins[0]
            # Sol menünün açık/kapalı durumundan etkilenmemek için X ekseninde sabit ~320px kullanıyoruz.
            card_x = win.left + 320
            card_y = win.top + int(win.height * 0.32)
            
            pyautogui.moveTo(card_x, card_y, duration=0.2)
            time.sleep(0.05)
            pyautogui.click()
            time.sleep(0.05)
            pyautogui.click() # Çift tıkla ki albüm/liste sayfası açılsın
            
        await asyncio.sleep(1.5) # Sayfanın tam yüklenmesi için bekle
        
        # 5. Sayfa açıldıktan sonra (Albüm veya Playlist sayfası), doğrudan YEŞİL BUTONUN sabit koordinatına tıkla
        # Tam merkeze isabet etmesi için X: %4.5, Y: %40.5 olarak milimetrik ayarlandı.
        played = await asyncio.to_thread(_find_and_click_green_play_button)
        if not played:
            return {"ok": False, "error": "Spotify yeşil çalma butonu bulunamadı."}

    except Exception as exc:
        return {"ok": False, "error": f"Spotify playback başarısız: {exc}"}

    return {"ok": True, "result": f'Spotify\'da "{query}" çalınıyor.'}
