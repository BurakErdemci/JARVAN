"""Spotify tool — spotipy tabanlı, pyautogui yok."""
import asyncio
import os
import re
import unicodedata
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth


def _norm_tokens(s: str) -> set[str]:
    """Türkçe aksanları kaldırıp kelime token seti döner (eşleşme skoru için)."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return set(re.findall(r"[a-z0-9]+", s))


def _match_score(req_tokens: set[str], candidate_text: str) -> float:
    """İstenen kelimelerin ne kadarının adayda geçtiği (0..1)."""
    cand = _norm_tokens(candidate_text)
    if not req_tokens or not cand:
        return 0.0
    return len(req_tokens & cand) / len(req_tokens)

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

        # Çoklu sonuç çek, istenen ada en çok benzeyeni seç (limit=1 yanlış şarkı çalıyordu).
        results = sp.search(q=query, type="track", limit=10)
        items = (results.get("tracks") or {}).get("items") or []
        if not items:
            return {"ok": False, "error": f"'{query}' şarkısı bulunamadı."}

        req = _norm_tokens(f"{track} {artist or ''}")

        def _cand_text(t: dict) -> str:
            return t["name"] + " " + " ".join(a["name"] for a in t.get("artists", []))

        best = max(items, key=lambda t: _match_score(req, _cand_text(t)))
        score = _match_score(req, _cand_text(best))
        name = f"{best['name']} — {best['artists'][0]['name']}"

        # Hiçbiri istenen ada benzemiyorsa rastgele çalma — netleştir.
        if score < 0.34:
            return {
                "ok": False,
                "error": (f"'{track}' tam eşleşmedi, yanlış şarkı çalmamak için durdum. "
                          f"En yakın bulduğum: '{name}'. Bunu mu çalayım, yoksa şarkı/sanatçı adını netleştirir misin?"),
            }

        sp.start_playback(uris=[best["uri"]], device_id=device_id)
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
