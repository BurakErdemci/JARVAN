import os
from dotenv import load_dotenv

load_dotenv()

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Tavily (LLM-odaklı web arama, 1000 istek/ay free)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

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

# Screen — hangi monitör: 1 = ilk, 2 = ikinci (0 = tüm ekranlar)
SCREEN_MONITOR_INDEX = 2

# Whisper
WHISPER_MODEL_SIZE   = "small"
WHISPER_DEVICE       = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_LANGUAGE     = "tr"
