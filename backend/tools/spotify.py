"""Deterministic Spotify actions for common playback tasks.

Arama sonrası Top Result kartındaki yeşil play butonuna tıklayarak çalar.
AppleScript ile pencere sınırlarını alır, koordinatları ona göre hesaplar.
"""

import asyncio
import platform
import subprocess
import time

import pyautogui

from tools.app_control import open_app

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"


# ─── Yardımcı fonksiyonlar ───────────────────────────────────────────

def _run_osascript(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=5,
    )


def _get_spotify_window_bounds() -> tuple[int, int, int, int]:
    """Spotify penceresinin (x, y, genişlik, yükseklik) değerlerini döner."""
    script = '''
tell application "Spotify" to activate
tell application "System Events"
    tell process "Spotify"
        set p to position of window 1
        set s to size of window 1
        return (item 1 of p as string) & "," & (item 2 of p as string) & "," & (item 1 of s as string) & "," & (item 2 of s as string)
    end tell
end tell
'''
    result = _run_osascript(script)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Spotify window bounds alınamadı")
    parts = [int(part.strip()) for part in result.stdout.strip().split(",")]
    if len(parts) != 4:
        raise RuntimeError(f"Beklenmeyen bounds çıktısı: {result.stdout!r}")
    return tuple(parts)  # type: ignore[return-value]


def _get_reliable_spotify_area() -> tuple[int, int, int, int]:
    """Spotify içerik alanını döner. AppleScript yanlış dönerse ekran boyutuna düşer."""
    try:
        x, y, w, h = _get_spotify_window_bounds()
        print(f"      [spotify] AppleScript bounds: x={x}, y={y}, w={w}, h={h}", flush=True)
        if w > 400 and h > 300:
            return x, y, w, h
        print(f"      [spotify] Bounds geçersiz (h={h}), ekran boyutuna düşülüyor", flush=True)
    except Exception as e:
        print(f"      [spotify] AppleScript hata: {e}", flush=True)

    # Fallback: Spotify fullscreen varsayımı
    sw, sh = pyautogui.size()
    print(f"      [spotify] Fallback ekran: {sw}x{sh}", flush=True)
    return 0, 25, sw, sh - 25  # 25px macOS menü çubuğu


def _click_top_result_play_button(is_playlist: bool = False):
    """Arama sonuçlarındaki Top Result kartına veya Play butonuna tıklar.
    
    is_playlist=True ise kartın kendisine tıklar (içine girmek için).
    is_playlist=False ise sağdaki yeşil play butonuna tıklar.
    """
    x, y, w, h = _get_reliable_spotify_area()

    if is_playlist:
        # Çalma listesi kartının ortasına tıkla (içine girsin)
        click_x = int(round(x + w * 0.50))
        click_y = int(round(y + h * 0.20))
        print(f"      [spotify] Entering playlist card: ({click_x}, {click_y})", flush=True)
        pyautogui.moveTo(click_x, click_y, duration=0.2)
        time.sleep(0.1)
        pyautogui.click()
    else:
        # YENİ SPOTIFY UI: 'Şarkılar' (Songs) listesinin ilk sırasındaki küçük resme odaklan
        # Bu nokta genellikle pencerenin X:%54, Y:%28 civarındadır.
        play_x = int(round(x + w * 0.54))
        play_y = int(round(y + h * 0.28))
        print(f"      [spotify] New UI: Clicking first song thumbnail play button at ({play_x}, {play_y})", flush=True)
        pyautogui.moveTo(play_x, play_y, duration=0.2)
        time.sleep(0.2)
        pyautogui.click()


def _click_playlist_playback_controls(shuffle: bool = True):
    """Playlist sayfası içindeki Shuffle ve Play butonlarına tıklar."""
    x, y, w, h = _get_reliable_spotify_area()

    if shuffle:
        # Karıştır (Shuffle) butonu: Büyük yeşil butonun biraz sağında
        shuffle_x = int(round(x + w * 0.38))
        shuffle_y = int(round(y + h * 0.40))
        print(f"      [spotify] Clicking Shuffle: ({shuffle_x}, {shuffle_y})", flush=True)
        pyautogui.click(shuffle_x, shuffle_y)
        time.sleep(0.3)

    # Büyük Yeşil Play butonu
    main_play_x = int(round(x + w * 0.27))
    main_play_y = int(round(y + h * 0.40))
    print(f"      [spotify] Clicking Main Play: ({main_play_x}, {main_play_y})", flush=True)
    pyautogui.click(main_play_x, main_play_y)


def _normalize_query(track: str, artist: str | None = None) -> str:
    q = (track or "").strip()
    if artist and artist.strip():
        q = f"{q} {artist.strip()}"
    return q.strip()


def _paste_text(text: str):
    """Metni clipboard üzerinden yapıştırır (Türkçe karakter desteği)."""
    if IS_MAC:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode("utf-8"))
        time.sleep(0.1)
        pyautogui.hotkey("command", "v")
    elif IS_WIN:
        escaped = text.replace("'", "''")
        subprocess.run(
            ["powershell", "-command", f"Set-Clipboard -Value '{escaped}'"],
            capture_output=True,
            timeout=5,
        )
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.05)


def _focus_spotify():
    """Spotify penceresini öne getirir ve odaklar."""
    if IS_MAC:
        _run_osascript('tell application "Spotify" to activate')
    elif IS_WIN:
        open_app("spotify")


# ─── Ana fonksiyon ───────────────────────────────────────────────────

async def control_spotify(action: str) -> dict:
    """Spotify'ı durdurur, devam ettirir veya bir sonraki/önceki şarkıya geçer."""
    scripts = {
        "pause": 'tell application "Spotify" to pause',
        "play": 'tell application "Spotify" to play',
        "next": 'tell application "Spotify" to next track',
        "previous": 'tell application "Spotify" to previous track',
        "toggle": 'tell application "Spotify" to playpause'
    }
    
    script = scripts.get(action.lower())
    if not script:
        return {"ok": False, "error": f"Geçersiz aksiyon: {action}"}
        
    await asyncio.to_thread(_run_osascript, script)
    return {"ok": True, "result": f"Spotify: {action} komutu gönderildi."}


async def play_spotify_track(
    track: str | None = None, 
    artist: str | None = None,
    is_playlist: bool = False,
    shuffle: bool = False
) -> dict:
    """Spotify'da şarkı veya çalma listesi arar ve çalar.
    is_playlist=True ise listenin içine girip shuffle açabilir.
    """
    if not track:
        return await control_spotify("play")
        
    query = _normalize_query(track, artist)
    if not query:
        return {"ok": False, "error": "şarkı adı boş"}

    # 1. Spotify'ı aç
    opened = await asyncio.to_thread(open_app, "spotify")
    if not opened.get("ok"):
        return {"ok": False, "error": opened.get("error", "Spotify açılamadı")}
    await asyncio.sleep(1.2)

    # 2. Spotify'ı odakla
    await asyncio.to_thread(_focus_spotify)
    await asyncio.sleep(0.4)

    try:
        # 3. Search bar'a odaklan
        search_key = "command" if IS_MAC else "ctrl"
        pyautogui.hotkey(search_key, "l")
        await asyncio.sleep(0.2)
        
        # 4. Mevcut aramayı temizle + yeni sorguyu yapıştır
        pyautogui.hotkey(search_key, "a")
        await asyncio.sleep(0.1)
        pyautogui.press("backspace") # AppleScript bazen Cmd+A'yı kaçırabiliyor
        await asyncio.to_thread(_paste_text, query)
        await asyncio.sleep(0.3)

        # 5. Enter ile arama sonuçları sayfasına git
        pyautogui.press("enter")
        await asyncio.sleep(1.2) 

        # 6. Sonuçlara göre çalmayı başlat
        if IS_MAC:
            if is_playlist:
                # Önce çalma listesine gir
                await asyncio.to_thread(_click_top_result_play_button, is_playlist=True)
                await asyncio.sleep(1.5) # Sayfanın yüklenmesini bekle
                # Shuffle ve Play butonlarına bas
                await asyncio.to_thread(_click_playlist_playback_controls, shuffle=shuffle)
            else:
                await asyncio.to_thread(_click_top_result_play_button, is_playlist=False)
        else:
            # Windows fallback: Tab ile navigasyon
            for _ in range(3):
                pyautogui.press("tab")
                await asyncio.sleep(0.1)
            pyautogui.press("enter")

        await asyncio.sleep(0.4)

    except Exception as exc:
        return {"ok": False, "error": f"Spotify playback başarısız: {exc}"}

    return {"ok": True, "result": f'Spotify\'da "{query}" çalınıyor.'}

