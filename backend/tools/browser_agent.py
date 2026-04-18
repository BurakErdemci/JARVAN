"""Browser-use agent — çoklu Gemini modeli arasında RPM-aware rotasyon."""
import os
import sys
import time
import socket
import asyncio
import platform
import subprocess
from collections import deque
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

# Opera GX — kullanıcı burada site loginlerini bir kez yapar, Jarvan oturumu
# miras alır (user_data_dir persist). Chrome yerine Opera → ana tarayıcını bozmaz.
def _resolve_browser_binary() -> str | None:
    system = platform.system()
    if system == "Darwin":
        candidates = ["/Applications/Opera GX.app/Contents/MacOS/Opera"]
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        candidates = [
            os.path.join(local, r"Programs\Opera GX\opera.exe"),
            os.path.join(program_files, r"Opera GX\opera.exe"),
            os.path.join(program_files, r"Opera GX\launcher.exe"),
        ]
    else:
        candidates = ["/usr/bin/opera", "/snap/bin/opera"]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _resolve_profile_dir() -> str:
    system = platform.system()
    if system == "Darwin":
        return str(Path.home() / "Library" / "Application Support" / "jarvan-opera-profile")
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return os.path.join(local, "jarvan-opera-profile")
    return str(Path.home() / ".config" / "jarvan-opera-profile")


BROWSER_BINARY = _resolve_browser_binary()
BROWSER_PROFILE_DIR = _resolve_profile_dir()


def _cleanup_singleton_locks():
    """Önceki crash'lerden kalan SingletonLock/Cookie/Socket dosyalarını sil.
    Windows'ta NTFS kilidi process ölse bile dosyayı bırakabiliyor → bir sonraki
    launch 'profile locked' diyor ve temp profile'a düşüyor."""
    if not os.path.isdir(BROWSER_PROFILE_DIR):
        return
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        p = os.path.join(BROWSER_PROFILE_DIR, name)
        try:
            if os.path.exists(p) or os.path.islink(p):
                os.remove(p)
        except OSError:
            pass

# (model_id, rpm_limit) — free tier limitleri
# Sıralama = RPD bütçesine göre (çok olanı önce tüket)
# NOT: 2.5 flash / flash-lite bugünkü RPD'yi tükettiği için pool'dan çıkarıldı
MODEL_POOL = [
    ("gemma-4-26b-a4b-it", 15),             # 1500 RPD — primary (MoE, 4B aktif)
    ("gemini-3.1-flash-lite-preview", 15),  # 500 RPD — secondary
]
SAFETY_MARGIN = 1  # limit - 1'de anahtarla, patlamayı önle

TASK_TIMEOUT_S = 480
MAX_STEPS = 15

_READ_ONLY_PREFIX = (
    "SADECE BİLGİ TOPLAMA modu. Form gönderme, satın alma, hesap açma, mesaj atma YOK. "
    "Sadece ara, oku, bul, özetle. "

    # UÇUŞ — site seçimi
    "UÇUŞ (İÇ HAT - Türkiye içi): https://www.google.com/travel/flights — form ile ara. "
    "UÇUŞ (YURT DIŞI): https://www.enuygun.com adresine git, ana sayfadaki form üzerinden doldur. "
    "Adımlar: (1) 'Tek yön' veya 'Gidiş-dönüş' seç, (2) 'Nereden' alanına kalkış şehrini yaz, "
    "autocomplete açılınca en üstteki (veya doğru olan) öneriye TIKLA, (3) 'Nereye' alanına varış "
    "şehrini yaz ve yine autocomplete'ten TIKLA — mutlaka dropdown seçeneğine bas, sadece yazma yetmez. "
    "(4) 'Gidiş Tarihi'ni seç, (5) 'Ucuz bilet bul' butonuna tıkla. "
    "Enuygun URL pattern'i tahmin etme — 404 verir. Enuygun captcha gösterirse 60sn bekle, olmazsa "
    "Google Flights'a düş. "
    "Skyscanner'a ASLA girme (captcha duvarı). "

    # UÇUŞ — kurallar
    "Google Flights'ta kullanıcı tek tarih verdiyse ÖNCE 'Gidiş dönüş' dropdown'unu 'Tek yön'e çevir, "
    "sonra diğer alanları doldur. Gidiş-dönüş ise iki tarihi de gir. "

    # CAPTCHA — human-in-the-loop
    "CAPTCHA / 'robot mu?' / 'BASILI TUT' / PerimeterX ekranı görürsen: "
    "hiçbir şey tıklama, 60 saniye kadar bekle (scroll veya wait action), "
    "kullanıcı elle çözecek. Sonra sayfa yüklendiyse normal devam et. "
    "60sn sonra hâlâ captcha varsa done action ile 'captcha çözülmedi, vazgeçildi' de. "

    # Sonuç — extract_structured_data YASAK
    "ÖNEMLİ: `extract_structured_data` KULLANMA — HTML parsing yavaş, timeout yiyor. "
    "Uçuş/otel sonuçları sayfada görünür olduğunda DOĞRUDAN ekrandan oku, "
    "gördüğün fiyatları `done` action'la KISA özetle (belirtmediyse en ucuz 3). "
    "UZUN TABLO üretme, Attachments/JSON üretme — sesli asistan dinliyor. "

    # Diğer
    "Otel/konaklama: google.com/travel/hotels. Genel arama: google.com. "
    "Görev: "
)


def _build_rotating_class():
    """browser_use.llm.ChatGoogle'dan türeyen RotatingChatGoogle sınıfını çalışma zamanında oluşturur.
    Agent, isinstance(llm, browser_use.llm sınıfları) kontrolü yaptığı için kalıtım şart."""
    from browser_use.llm import ChatGoogle

    class RotatingChatGoogle(ChatGoogle):
        """Birden çok ChatGoogle instance'ı arasında rolling 60s RPM penceresine göre rotasyon yapar."""

        def __init__(self, pool, api_key: str):
            first_model, _ = pool[0]
            init_kwargs = {"model": first_model, "api_key": api_key}
            if first_model.startswith("gemini-"):
                init_kwargs["thinking_budget"] = 0
            super().__init__(**init_kwargs)

            self._pool_entries = []
            for model_id, rpm in pool:
                kwargs = {"model": model_id, "api_key": api_key}
                if model_id.startswith("gemini-"):
                    kwargs["thinking_budget"] = 0
                llm = ChatGoogle(**kwargs)
                self._pool_entries.append({
                    "llm": llm,
                    "model": model_id,
                    "rpm": rpm,
                    "calls": deque(),
                })

        def _pick(self):
            now = time.monotonic()
            for entry in self._pool_entries:
                while entry["calls"] and now - entry["calls"][0] > 60.0:
                    entry["calls"].popleft()
            for entry in self._pool_entries:
                if len(entry["calls"]) < entry["rpm"] - SAFETY_MARGIN:
                    return entry
            return min(self._pool_entries, key=lambda e: len(e["calls"]))

        async def ainvoke(self, messages, output_format=None, **kwargs):
            last_err = None
            tried = set()
            for _ in range(len(self._pool_entries)):
                entry = self._pick()
                if entry["model"] in tried:
                    await asyncio.sleep(2)
                    continue
                tried.add(entry["model"])
                entry["calls"].append(time.monotonic())
                try:
                    print(f"[rotating-llm] -> {entry['model']} ({len(entry['calls'])}/{entry['rpm']} son 60s)", flush=True)
                    return await entry["llm"].ainvoke(messages, output_format=output_format, **kwargs)
                except Exception as e:
                    msg = str(e).lower()
                    if "429" in msg or "resource_exhausted" in msg or "503" in msg or "unavailable" in msg:
                        print(f"[rotating-llm] {entry['model']} düştü, diğerine geçiliyor", flush=True)
                        now = time.monotonic()
                        entry["calls"].clear()
                        for _ in range(entry["rpm"]):
                            entry["calls"].append(now)
                        last_err = e
                        continue
                    raise
            if last_err:
                raise last_err
            raise RuntimeError("RotatingChatGoogle: havuzda kullanılabilir model yok")

    return RotatingChatGoogle


async def run_browser_task(task: str) -> dict:
    if not task or not task.strip():
        return {"ok": False, "error": "görev boş"}
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY yok"}

    try:
        from browser_use import Agent, BrowserProfile
    except Exception as e:
        return {"ok": False, "error": f"browser-use import hatası: {e}"}

    full_task = _READ_ONLY_PREFIX + task.strip()

    try:
        _cleanup_singleton_locks()
        RotatingChatGoogle = _build_rotating_class()
        llm = RotatingChatGoogle(MODEL_POOL, GEMINI_API_KEY)
        # Opera GX bulunamazsa browser-use default Chromium'a düşer
        profile_kwargs = {
            "user_data_dir": BROWSER_PROFILE_DIR,
            "headless": False,
            "keep_alive": False,  # her görev sonunda kapat — SingletonLock'u önler (Windows)
        }
        if BROWSER_BINARY:
            profile_kwargs["executable_path"] = BROWSER_BINARY
        profile = BrowserProfile(**profile_kwargs)
        agent = Agent(task=full_task, llm=llm, browser_profile=profile)

        history = await asyncio.wait_for(agent.run(max_steps=MAX_STEPS), timeout=TASK_TIMEOUT_S)

        final_text = ""
        try:
            final_text = history.final_result() or ""
        except Exception:
            pass
        if not final_text:
            try:
                extracted = history.extracted_content()
                if extracted:
                    final_text = str(extracted[-1])
            except Exception:
                pass

        # Attachments / JSON bloklarını kes — model sesli asistan, kısa özet yeterli
        if final_text:
            cut = final_text.find("\nAttachments:")
            if cut != -1:
                final_text = final_text[:cut].strip()
            final_text = final_text[:600]

        return {
            "ok": True,
            "result": final_text or "Görev tamamlandı ama metin sonuç yok.",
        }
    except asyncio.TimeoutError:
        return {"ok": False, "error": f"görev {TASK_TIMEOUT_S}sn içinde bitmedi"}
    except Exception as e:
        import traceback
        print(f"[browser_agent] HATA:\n{traceback.format_exc()}", flush=True)
        return {"ok": False, "error": f"browser agent hatası: {type(e).__name__}: {e}"}


# --- Takeover modu: kullanıcının zaten açık tarayıcısına CDP ile bağlan ---

CDP_PORT = 9222


def _cdp_up(port: int) -> bool:
    """Port dinleniyor mu (chromium --remote-debugging-port bu port'ta)."""
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _resolve_real_opera_profile() -> str | None:
    """Kullanıcının asıl Opera GX profil klasörü (tablari, loginleri, bookmarks burada).
    Bu klasörü --user-data-dir olarak geçersek Opera normal gibi açılır, ama debug port dinler."""
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            p = os.path.join(appdata, "Opera Software", "Opera GX Stable")
            if os.path.isdir(p):
                return p
    elif system == "Darwin":
        p = str(Path.home() / "Library" / "Application Support" / "com.operasoftware.OperaGX")
        if os.path.isdir(p):
            return p
    return None


def launch_debug_browser(port: int = CDP_PORT) -> dict:
    """Opera GX'i kullanıcının GERÇEK profili + --remote-debugging-port flag'iyle başlat.
    Bu çağrıldıktan sonra kullanıcı normal gibi tarayıcıyı kullanır, ama Jarvan
    istediği zaman CDP ile bağlanıp sekmeleri devralabilir."""
    if _cdp_up(port):
        return {"ok": True, "result": "Tarayıcı zaten debug modda açık."}
    exe = BROWSER_BINARY
    if not exe:
        return {"ok": False, "error": "Opera GX bulunamadı (cross-platform path resolver boş döndü)"}

    real_profile = _resolve_real_opera_profile()
    cmd = [exe, f"--remote-debugging-port={port}"]
    if real_profile:
        cmd.append(f"--user-data-dir={real_profile}")
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return {"ok": False, "error": f"tarayıcı başlatılamadı: {type(e).__name__}: {e}"}

    # Port 8sn içinde hazır olsun
    for _ in range(16):
        time.sleep(0.5)
        if _cdp_up(port):
            return {"ok": True, "result": "Opera GX debug modunda açıldı, artık devralabilirim."}
    return {"ok": False, "error": (
        "Tarayıcı başlatıldı ama debug port dinlemiyor. "
        "Opera GX muhtemelen zaten başka bir pencerede açık — önce tamamen kapat, tekrar dene."
    )}


async def run_takeover_task(task: str) -> dict:
    """Zaten açık (debug modda) tarayıcıya bağlan, aktif tab'da görevi yürüt.
    Kullanıcı tarayıcıda bir şeye başlamış, Jarvan kaldığı yerden devam etsin diye."""
    if not task or not task.strip():
        return {"ok": False, "error": "görev boş"}
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY yok"}

    if not _cdp_up(CDP_PORT):
        return {"ok": False, "error": (
            "Tarayıcı debug modunda açık değil. Önce bana 'tarayıcıyı debug modda aç' "
            "(veya 'tarayıcı başlat') de, tab'ların gelsin, sonra devralabilirim."
        )}

    try:
        from browser_use import Agent, BrowserProfile
    except Exception as e:
        return {"ok": False, "error": f"browser-use import hatası: {e}"}

    full_task = _READ_ONLY_PREFIX + task.strip()

    try:
        RotatingChatGoogle = _build_rotating_class()
        llm = RotatingChatGoogle(MODEL_POOL, GEMINI_API_KEY)
        # cdp_url: mevcut browser'a bağlan, yeni spawn etme
        profile = BrowserProfile(
            cdp_url=f"http://127.0.0.1:{CDP_PORT}",
            keep_alive=True,  # takeover'da kullanıcının tarayıcısını kapatmayız
        )
        agent = Agent(task=full_task, llm=llm, browser_profile=profile)

        history = await asyncio.wait_for(agent.run(max_steps=MAX_STEPS), timeout=TASK_TIMEOUT_S)

        final_text = ""
        try:
            final_text = history.final_result() or ""
        except Exception:
            pass
        if not final_text:
            try:
                extracted = history.extracted_content()
                if extracted:
                    final_text = str(extracted[-1])
            except Exception:
                pass

        if final_text:
            cut = final_text.find("\nAttachments:")
            if cut != -1:
                final_text = final_text[:cut].strip()
            final_text = final_text[:600]

        return {
            "ok": True,
            "result": final_text or "Görev tamamlandı ama metin sonuç yok.",
        }
    except asyncio.TimeoutError:
        return {"ok": False, "error": f"görev {TASK_TIMEOUT_S}sn içinde bitmedi"}
    except Exception as e:
        import traceback
        print(f"[browser_agent] takeover HATA:\n{traceback.format_exc()}", flush=True)
        return {"ok": False, "error": f"takeover hatası: {type(e).__name__}: {e}"}
