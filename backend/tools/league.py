"""League of Legends / Riot Client launcher for Windows."""

import os
import subprocess
import time
from pathlib import Path

import pyautogui
import pygetwindow as gw


RIOT_PRODUCT_ARGS = [
    "--launch-product=league_of_legends",
    "--launch-patchline=live",
]
DEFAULT_START_SEARCH_QUERY = os.getenv("LOL_START_SEARCH_QUERY", "League of Legends")

ACCOUNT_ALIASES = {
    "1": "FJKIS",
    "ana": "FJKIS",
    "ana hesap": "FJKIS",
    "fjkis": "FJKIS",
    "fjkis123": "FJKIS",
    "2": "KATILBRONZ",
    "ikinci": "KATILBRONZ",
    "katilbronz": "KATILBRONZ",
    "3": "ABUBAKAR",
    "üçüncü": "ABUBAKAR",
    "ucuncu": "ABUBAKAR",
    "abubakar": "ABUBAKAR",
}


def _candidate_paths() -> list[str]:
    program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    local = os.environ.get("LOCALAPPDATA", "")
    system_drive = os.environ.get("SystemDrive", "C:")
    return [
        os.getenv("LOL_CLIENT_PATH", ""),
        os.getenv("RIOT_CLIENT_PATH", ""),
        rf"{system_drive}\Riot Games\League of Legends\LeagueClient.exe",
        rf"{system_drive}\Riot Games\Riot Client\RiotClientServices.exe",
        rf"{program_data}\Riot Games\RiotClientInstalls.json",
        rf"{local}\Riot Games\Riot Client\RiotClientServices.exe",
    ]


def _read_riot_installs_json(path: str) -> list[str]:
    try:
        import json

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        paths = []
        for value in data.values():
            if isinstance(value, str) and value.lower().endswith(".exe"):
                paths.append(value.replace("/", "\\"))
        return paths
    except Exception:
        return []


def _resolve_launcher() -> str | None:
    extra = []
    for path in _candidate_paths():
        if path and path.lower().endswith(".json") and os.path.exists(path):
            extra.extend(_read_riot_installs_json(path))

    for path in [*_candidate_paths(), *extra]:
        if path and path.lower().endswith(".exe") and os.path.exists(path):
            return path
    return None


def _launch_from_windows_search(query: str | None = None) -> dict:
    """Windows Start aramasından kullanıcı gibi LoL aç."""
    search_text = (query or DEFAULT_START_SEARCH_QUERY).strip() or "League of Legends"
    try:
        pyautogui.press("win")
        time.sleep(0.7)
        pyautogui.write(search_text, interval=0.02)
        time.sleep(1.0)
        pyautogui.press("enter")
        return {"ok": True, "method": "windows_search", "query": search_text}
    except Exception as exc:
        return {"ok": False, "error": f"Windows aramasından başlatılamadı: {exc}"}


def _launch_from_path(launcher: str) -> dict:
    """Son çare: resmi Riot/LoL launcher path'i üzerinden aç."""
    args = [launcher]
    if os.path.basename(launcher).lower() == "riotclientservices.exe":
        args.extend(RIOT_PRODUCT_ARGS)
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", *args],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        return {"ok": True, "method": "path", "launcher": launcher}
    except Exception as exc:
        return {"ok": False, "error": f"League başlatılamadı: {exc}", "launcher": launcher}


def _process_running(names: tuple[str, ...]) -> bool:
    try:
        result = subprocess.run(
            ["tasklist"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.lower()
        return any(name.lower() in output for name in names)
    except Exception:
        return False


def _find_window(keywords: tuple[str, ...]):
    for win in gw.getAllWindows():
        title = (win.title or "").lower()
        if title and any(k.lower() in title for k in keywords) and win.width > 500:
            return win
    return None


def _focus_window(win) -> bool:
    try:
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.4)
        return True
    except Exception:
        return False


def _capture_window(win):
    try:
        import mss
        from PIL import Image

        region = {
            "left": int(win.left),
            "top": int(win.top),
            "width": max(int(win.width), 1),
            "height": max(int(win.height), 1),
        }
        with mss.mss() as sct:
            shot = sct.grab(region)
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    except Exception:
        return None


def _login_form_ready(win) -> bool:
    """Riot login formu gerçekten render edildi mi?"""
    img = _capture_window(win)
    if img is None:
        return False

    width, height = img.size
    if width < 700 or height < 450:
        return False

    left_panel_w = max(int(width * 0.26), 1)
    bright = 0
    total = 0
    for y in range(int(height * 0.12), int(height * 0.85), 8):
        for x in range(0, left_panel_w, 8):
            r, g, b = img.getpixel((x, y))
            if r > 185 and g > 185 and b > 185:
                bright += 1
            total += 1

    if total == 0 or bright / total < 0.45:
        return False

    field_points = [
        (int(width * 0.13), int(height * 0.31)),
        (int(width * 0.13), int(height * 0.39)),
    ]
    for x, y in field_points:
        r, g, b = img.getpixel((x, y))
        if not (r > 200 and g > 200 and b > 200):
            return False
    return True


def _wait_for_login_form(win, timeout_s: int = 45) -> bool:
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        if _login_form_ready(win):
            return True
        time.sleep(2.0)
    return False


def _resolve_account_key(account: str | None = None) -> str | None:
    raw = (account or "").strip().lower()
    if not raw:
        raw = os.getenv("RIOT_DEFAULT_ACCOUNT", "").strip().lower()
    if not raw:
        return None
    if raw in ACCOUNT_ALIASES:
        return ACCOUNT_ALIASES[raw]
    normalized = raw.upper().replace(" ", "_").replace("-", "_")
    return normalized


def _credentials_for_account(account: str | None = None) -> tuple[str, str, str | None]:
    key = _resolve_account_key(account)
    if key:
        username = os.getenv(f"RIOT_{key}_USERNAME", "").strip()
        password = os.getenv(f"RIOT_{key}_PASSWORD", "").strip()
        if username and password:
            return username, password, key

    # Backward-compatible single account fallback.
    username = os.getenv("RIOT_USERNAME", "").strip()
    password = os.getenv("RIOT_PASSWORD", "").strip()
    return username, password, key


def _league_ready() -> bool:
    if _process_running(("LeagueClientUx.exe", "LeagueClient.exe")):
        win = _find_window(("league of legends",))
        if win:
            if _login_form_ready(win):
                return False
            # Login formu kaybolduktan sonra LeagueClientUx penceresi varlığı
            # pratikte ana client/transition aşamasına geçtiğimizi gösterir.
            _focus_window(win)
            return True
    return False


def _launch_league_with_fallback(launcher: str | None) -> dict:
    launch_result = _launch_from_windows_search()
    if not launch_result.get("ok") and launcher:
        launch_result = _launch_from_path(launcher)
    return launch_result


def _try_login_from_env(account: str | None = None) -> dict:
    username, password, key = _credentials_for_account(account)
    if not username or not password:
        if key:
            return {"ok": False, "error": f"RIOT_{key}_USERNAME / RIOT_{key}_PASSWORD .env içinde yok."}
        return {"ok": False, "error": "RIOT_USERNAME / RIOT_PASSWORD veya hesap bazlı Riot bilgileri .env içinde yok."}

    win = _find_window(("riot client", "sign in", "oturum", "giriş"))
    if not win:
        return {"ok": False, "error": "Riot login penceresi bulunamadı."}
    if not _focus_window(win):
        return {"ok": False, "error": "Riot login penceresi odaklanamadı."}
    if not _wait_for_login_form(win):
        return {"ok": False, "error": "Riot login formu hazır hale gelmedi."}

    # Riot Client login ekranı sık değişiyor. Bu yüzden alanlara oranla tıklayıp
    # Tab sırasıyla ilerleyen temkinli bir giriş denemesi yapıyoruz.
    x = win.left + int(win.width * 0.13)
    username_y = win.top + int(win.height * 0.31)
    password_y = win.top + int(win.height * 0.39)
    submit_y = win.top + int(win.height * 0.77)

    pyautogui.click(x, username_y)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(username, interval=0.02)
    pyautogui.click(x, password_y)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(password, interval=0.02)
    pyautogui.click(x, submit_y)
    return {"ok": True, "account_key": key, "username": username, "result": "Riot login bilgileri gönderildi."}


def launch_league_client(auto_login: bool = True, timeout_s: int = 120, account: str | None = None) -> dict:
    """LoL client'ı ana ekrana kadar açmaya çalışır."""
    launcher = _resolve_launcher()
    existing_win = _find_window(("riot client", "league of legends", "sign in", "oturum", "giriş"))
    if existing_win and _login_form_ready(existing_win):
        _focus_window(existing_win)
        launch_result = {"ok": True, "method": "existing_login_window"}
    else:
        launch_result = _launch_league_with_fallback(launcher)
        if not launch_result.get("ok"):
            return launch_result

    start = time.monotonic()
    login_attempted = False
    last_login_result = None
    login_submitted_at = 0.0

    while time.monotonic() - start < max(20, int(timeout_s)):
        riot_win = _find_window(("riot client", "league of legends", "sign in", "oturum", "giriş"))
        if riot_win and auto_login and not login_attempted and _login_form_ready(riot_win):
            last_login_result = _try_login_from_env(account)
            login_attempted = True
            login_submitted_at = time.monotonic()
            time.sleep(3)
            continue

        if _league_ready():
            return {
                "ok": True,
                "result": "League of Legends client hazır.",
                "launch": launch_result,
                "launcher": launcher,
            }

        if login_attempted and login_submitted_at and time.monotonic() - login_submitted_at > 12:
            current_win = _find_window(("riot client", "league of legends", "sign in", "oturum", "giriş"))
            if current_win and not _login_form_ready(current_win):
                return {
                    "ok": True,
                    "result": "Riot login gönderildi; client yükleniyor veya ana ekrana geçiyor.",
                    "launch": launch_result,
                    "launcher": launcher,
                    "account": account,
                }

        time.sleep(2)

    if last_login_result and not last_login_result.get("ok"):
        return {
            "ok": False,
            "error": f"League açıldı ama login tamamlanamadı: {last_login_result.get('error')}",
            "launch": launch_result,
            "launcher": launcher,
            "account": account,
        }
    return {
        "ok": False,
        "error": "League client beklenen sürede hazır olmadı. Riot güncelleme/login ekranında kalmış olabilir.",
        "launch": launch_result,
        "launcher": launcher,
        "account": account,
    }
