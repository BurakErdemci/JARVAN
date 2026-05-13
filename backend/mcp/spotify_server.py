"""JARVAN Spotify MCP Server — spotipy tabanlı, koordinat yok."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from fastmcp import FastMCP

mcp = FastMCP("spotify-jarvan")

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


def _ensure_open():
    import subprocess, time
    subprocess.Popen(["open", "-a", "Spotify"])
    time.sleep(3)


def _active_device(sp: spotipy.Spotify, retry: bool = True) -> str | None:
    devices = sp.devices().get("devices", [])
    for d in devices:
        if d["is_active"]:
            return d["id"]
    if devices:
        sp.transfer_playback(devices[0]["id"], force_play=False)
        return devices[0]["id"]
    if retry:
        _ensure_open()
        import time; time.sleep(2)
        return _active_device(sp, retry=False)
    return None


@mcp.tool()
def play_track(query: str, is_playlist: bool = False, shuffle: bool = False) -> str:
    """Spotify'da şarkı veya playlist arar ve çalar."""
    sp = _sp()
    device_id = _active_device(sp)

    if is_playlist:
        results = sp.search(q=query, type="playlist", limit=1)
        items = (results.get("playlists") or {}).get("items") or []
        if not items:
            return f"'{query}' adında playlist bulunamadı."
        playlist = items[0]
        if shuffle:
            sp.shuffle(True, device_id=device_id)
        sp.start_playback(context_uri=playlist["uri"], device_id=device_id)
        return f"'{playlist['name']}' playlist çalınıyor."

    results = sp.search(q=query, type="track", limit=1)
    items = (results.get("tracks") or {}).get("items") or []
    if not items:
        return f"'{query}' şarkısı bulunamadı."
    track = items[0]
    sp.start_playback(uris=[track["uri"]], device_id=device_id)
    return f"'{track['name']} — {track['artists'][0]['name']}' çalınıyor."


@mcp.tool()
def control_playback(action: str) -> str:
    """Oynatma kontrolü: pause, play, next, previous, shuffle_on, shuffle_off."""
    sp = _sp()
    device_id = _active_device(sp)
    match action.lower():
        case "pause":
            sp.pause_playback(device_id=device_id)
        case "play":
            sp.start_playback(device_id=device_id)
        case "next":
            sp.next_track(device_id=device_id)
        case "previous":
            sp.previous_track(device_id=device_id)
        case "shuffle_on":
            sp.shuffle(True, device_id=device_id)
        case "shuffle_off":
            sp.shuffle(False, device_id=device_id)
        case _:
            return f"Bilinmeyen aksiyon: {action}"
    return f"Spotify: {action} tamamlandı."


@mcp.tool()
def get_current_track() -> dict:
    """Şu an çalan şarkıyı döner."""
    sp = _sp()
    current = sp.current_playback()
    if not current or not current.get("item"):
        return {"playing": False, "info": "Şu an bir şey çalmıyor."}
    item = current["item"]
    return {
        "playing": current["is_playing"],
        "track": item["name"],
        "artist": ", ".join(a["name"] for a in item["artists"]),
        "album": item["album"]["name"],
        "uri": item["uri"],
    }


if __name__ == "__main__":
    mcp.run()
