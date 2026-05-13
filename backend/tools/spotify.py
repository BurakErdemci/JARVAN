"""Spotify tool — spotipy tabanlı, pyautogui yok."""
import asyncio
import os
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing "
    "playlist-read-private "
    "playlist-read-collaborative"
)

TOKEN_CACHE = str(Path(__file__).parent.parent / "data" / "spotify_token.json")


def _sp() -> spotipy.Spotify:
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope=SCOPES,
        cache_path=TOKEN_CACHE,
        open_browser=True,
    ))


def _get_device(sp: spotipy.Spotify) -> str | None:
    """Mevcut aktif/available cihazı döner."""
    devices = sp.devices().get("devices", [])
    for d in devices:
        if d["is_active"]:
            return d["id"]
    if devices:
        sp.transfer_playback(devices[0]["id"], force_play=False)
        return devices[0]["id"]
    return None


async def _active_device(sp: spotipy.Spotify) -> str | None:
    """Aktif cihaz yoksa Spotify'ı açıp bekler, sonra tekrar dener."""
    device_id = await asyncio.to_thread(_get_device, sp)
    if device_id:
        return device_id

    # Cihaz yok — Spotify'ı aç
    import subprocess, platform
    if platform.system() == "Darwin":
        subprocess.Popen(["open", "-a", "Spotify"])
    else:
        subprocess.Popen(["start", "spotify"], shell=True)

    # Spotify'ın API'ye register olması için bekle
    for _ in range(4):
        await asyncio.sleep(2)
        device_id = await asyncio.to_thread(_get_device, sp)
        if device_id:
            return device_id

    return None


def _find_user_playlist(sp: spotipy.Spotify, query: str) -> dict | None:
    """Kullanıcının kendi playlist'lerinde isim eşleşmesi arar."""
    q = query.lower().strip()
    offset = 0
    while True:
        result = sp.current_user_playlists(limit=50, offset=offset)
        items = result.get("items") or []
        for pl in items:
            if pl and pl.get("name") and q in pl["name"].lower():
                return pl
        if result.get("next"):
            offset += 50
        else:
            break
    return None


async def play_spotify_track(
    track: str | None = None,
    artist: str | None = None,
    is_playlist: bool = False,
    shuffle: bool = False,
) -> dict:
    """Spotify'da şarkı veya playlist arar ve çalar."""
    try:
        sp = _sp()
        device_id = await _active_device(sp)

        if not track:
            sp.start_playback(device_id=device_id)
            return {"ok": True, "result": "Spotify devam ettiriliyor."}

        query = f"{track} {artist}".strip() if artist else track.strip()

        if is_playlist:
            # Önce kullanıcının kendi playlist'lerine bak
            playlist = await asyncio.to_thread(_find_user_playlist, sp, query)
            if not playlist:
                # Bulunamazsa genel aramaya düş
                results = sp.search(q=query, type="playlist", limit=1)
                items = (results.get("playlists") or {}).get("items") or []
                if not items:
                    return {"ok": False, "error": f"'{query}' playlist bulunamadı."}
                playlist = items[0]
            if shuffle:
                sp.shuffle(True, device_id=device_id)
            sp.start_playback(context_uri=playlist["uri"], device_id=device_id)
            return {"ok": True, "result": f"'{playlist['name']}' playlist çalınıyor."}

        results = sp.search(q=query, type="track", limit=1)
        items = (results.get("tracks") or {}).get("items") or []
        if not items:
            return {"ok": False, "error": f"'{query}' şarkısı bulunamadı."}
        t = items[0]
        sp.start_playback(uris=[t["uri"]], device_id=device_id)
        name = f"{t['name']} — {t['artists'][0]['name']}"
        return {"ok": True, "result": f"'{name}' çalınıyor."}

    except Exception as e:
        return {"ok": False, "error": str(e)}


async def control_spotify(action: str) -> dict:
    """pause / play / next / previous / toggle"""
    try:
        sp = _sp()
        device_id = await _active_device(sp)
        match action.lower():
            case "pause":
                sp.pause_playback(device_id=device_id)
            case "play":
                sp.start_playback(device_id=device_id)
            case "next":
                sp.next_track(device_id=device_id)
            case "previous":
                sp.previous_track(device_id=device_id)
            case "toggle":
                current = sp.current_playback()
                if current and current.get("is_playing"):
                    sp.pause_playback(device_id=device_id)
                else:
                    sp.start_playback(device_id=device_id)
            case _:
                return {"ok": False, "error": f"Bilinmeyen aksiyon: {action}"}
        return {"ok": True, "result": f"Spotify: {action}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
