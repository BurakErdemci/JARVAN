import os
import platform
from dotenv import load_dotenv

load_dotenv()

# ─── Platform tespiti (Mac/Windows donanım varsayımlarını ayırmak için) ──
_IS_MAC = platform.system() == "Darwin"
_IS_WINDOWS = platform.system() == "Windows"


def _default_vram_gb() -> str:
    """Telemetri VRAM bar'ı için makul toplam (GB). Mac'te discrete GPU yok —
    Apple Silicon unified memory'den Metal'in ayırdığı bütçe ~%70. Windows'ta
    RX 6750 XT = 12GB. .env'de GPU_VRAM_GB verilirse bu yok sayılır."""
    if _IS_MAC:
        try:
            import psutil
            return str(round(psutil.virtual_memory().total / 1e9 * 0.7))
        except Exception:
            return "11"  # 16GB Mac default Metal bütçesi
    return "12"  # RX 6750 XT

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Feature flags
# Experimental worker/MCP paths stay out of the live voice runtime until the
# core Live + memory loop is stable.
ENABLE_EXPERIMENTAL_WORKERS = os.getenv("ENABLE_EXPERIMENTAL_WORKERS", "0") == "1"
ENABLE_MCP_HUB = os.getenv("ENABLE_MCP_HUB", "0") == "1"

# Tavily (LLM-odaklı web arama, 1000 istek/ay free)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Kişisel
MY_WHATSAPP = os.getenv("MY_WHATSAPP", "")  # Ülke koduyla, + ya da boşluk olmadan

# VAD - Omi'den alınan production parametreleri
VAD_GATE_PRE_ROLL_MS         = 300
VAD_GATE_HANGOVER_MS         = 4000
VAD_GATE_SPEECH_THRESHOLD    = 0.65
VAD_GATE_FINALIZE_SILENCE_MS = 300
VAD_MODEL_POOL_SIZE          = 4

# Audio
AUDIO_SAMPLE_RATE    = 16000   # Whisper ve Silero 16kHz bekliyor
AUDIO_CHUNK_MS       = 32      # Silero 16kHz için tam 512 sample ister (32ms)
AUDIO_CHANNELS       = 1       # Mono

# Screen — hangi monitör: 1 = ilk, 2 = ikinci (0 = tüm ekranlar). Env'den ayarlanır.
# Default 2: Burak'ın Windows çift-monitör kurulumu. capture.py guard'lı — tek ekranlı
# Mac'te 2 mevcut değilse otomatik 1'e (primary) düşer, patlamaz. Harici ekranlı Mac'te
# 2 = harici ekran. MacBook tek ekran kullanıyorsan .env'de SCREEN_MONITOR_INDEX=1 yap.
SCREEN_MONITOR_INDEX = int(os.getenv("SCREEN_MONITOR_INDEX", "2"))

# GPU VRAM toplamı (GB) — telemetri panelinde VRAM bar'ı için.
# Otomatik: Windows → 12 (RX 6750 XT), Mac → unified memory'nin ~%70'i.
GPU_VRAM_GB = float(os.getenv("GPU_VRAM_GB", _default_vram_gb()))

# Whisper (STT — faster-whisper, gömülü).
# 'small': CPU'da hızlı (~2-3s) + ~0.5GB RAM — 16GB makine + "hız önemli" için ideal.
# large-v3-turbo CPU'da 8-12s + ~2GB (çok ağır). Türkçe doğruluk az gelirse → 'medium'.
WHISPER_MODEL_SIZE   = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE       = os.getenv("WHISPER_DEVICE", "cpu")   # AMD GPU → CUDA yok, CPU
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
# CTranslate2 CPU thread sayısı. 0 = otomatik (fiziksel çekirdek sayısını seçer).
# Default 0 → her makinede uyumlu (Ryzen 5 7500F'te 6, M4'te 8-10 çekirdek otomatik).
WHISPER_CPU_THREADS  = int(os.getenv("WHISPER_CPU_THREADS", "0"))

# ─── Sesli endpointing (cümle bitti mi?) ────────────────────────────
# Konuştuktan sonra bu kadar sessizlik → cümle bitti say. ÇOK düşükse cümle ortası
# duraksamada keser ("gördüğün bütün ... toolları" → "...tuğ"). 1000ms doğal duraksamaya
# tolerans verir; çok yüksekse tur sonu gecikir. Mic'ine göre .env'den ayarla.
VOICE_SILENCE_MS = int(os.getenv("VOICE_SILENCE_MS", "1000"))
# int16 RMS eşiği — üstü "konuşma". Düşürürsen yumuşak heceleri de yakalar ama
# gürültüyü konuşma sanabilir. Sessiz mic'te düşür, gürültülü ortamda yükselt.
VOICE_RMS_GATE   = int(os.getenv("VOICE_RMS_GATE", "300"))
# "tr" sabit — kısa kliplerde otomatik dil algılama yanlış dile düşüp saçmalıyor.
# Sen Türkçe konuşuyorsun, çıkış zaten Gemma'dan İngilizce. EN'e geçmek istersen "en".
WHISPER_LANGUAGE     = os.getenv("WHISPER_LANGUAGE", "tr")

# ─── Local Voice Brain (Gemma via Ollama) ───────────────────────────────
# NOT: 'localhost' DEĞİL '127.0.0.1' — Windows'ta localhost önce IPv6 (::1) deneyip
# ~2s timeout sonra IPv4'e düşüyor (her çağrıya +~2.2s). Ölçüldü: 2.74s → 0.47s.
# ─── Wake word (Vosk) ───────────────────────────────────────────────────
# "wake up" İngilizce → İngilizce Vosk modeli şart (vosk-tr İngilizceyi tanımaz).
# models/vosk-en-small'a vosk-model-small-en-us-0.15 çıkarılmalı. TR'ye dönmek için
# WAKE_WORD=uyan + VOSK_MODEL_PATH=models/vosk-tr.
WAKE_WORD       = os.getenv("WAKE_WORD", "wake up").lower()
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "models/vosk-en-small")

OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:12b")
# gemma4 reasoning modeli — santral/hafif-cevap rolünde düşünme gereksiz (~4-5s ekler).
GEMMA_THINK = os.getenv("GEMMA_THINK", "0") == "1"
# Context penceresi. Ollama default 4096; 27 tool şeması bunu doldurup üretime yer
# bırakmıyor (done_reason=length, eval=1). 8192 → tool'lar + cevap rahat sığar.
# (Ölçüldü: ctx=4096 ile 27 tool kırık; ctx=8192 ile tool_call + cevap düzgün.)
GEMMA_NUM_CTX = int(os.getenv("GEMMA_NUM_CTX", "8192"))
# GPU'ya verilecek katman sayısı (-1 = hepsi). 12GB kartta 12B@8k SINIRDA:
# ilk sorguda compute tamponları açılırken VRAM taşar → sürücü takas yapar →
# hem chat timeout hem sistem geneli kasma. 48 katmanın ~42'si GPU'da kalsın,
# 6'sı RAM'e → ~1.5GB nefes alanı (32GB RAM'de hissedilmez).
GEMMA_NUM_GPU = int(os.getenv("GEMMA_NUM_GPU", "-1"))
# Ollama chat zaman aşımı (sn). Soğuk yükleme + 8k prompt eval 60sn'yi aşabiliyor.
GEMMA_TIMEOUT = float(os.getenv("GEMMA_TIMEOUT", "120"))
# Uyku modunda Gemma'yı Ollama'dan boşalt (RAM/VRAM serbest). Uyanınca yeniden yüklenir
# (greeting Kokoro'dan anında çalarak yükleme gecikmesini gizler). 7/24 idle RAM için.
UNLOAD_ON_SLEEP = os.getenv("UNLOAD_ON_SLEEP", "1") == "1"

# ─── Local Voice Output (TTS — Kokoro ONNX, gömülü) ──────────────────────
# Jarvan TR+EN anlar ama HER ZAMAN İngilizce konuşur (İngilizce TTS sesleri çok daha iyi).
_KOKORO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "kokoro")
KOKORO_MODEL_PATH  = os.getenv("KOKORO_MODEL_PATH",  os.path.join(_KOKORO_DIR, "kokoro-v1.0.onnx"))
KOKORO_VOICES_PATH = os.getenv("KOKORO_VOICES_PATH", os.path.join(_KOKORO_DIR, "voices-v1.0.bin"))
KOKORO_VOICE       = os.getenv("KOKORO_VOICE", "bm_george")   # British male (Burak onayladı)
KOKORO_LANG        = os.getenv("KOKORO_LANG", "en-us")
KOKORO_SPEED       = float(os.getenv("KOKORO_SPEED", "1.0"))
