# Jarvan — AI Kişisel Asistan

**Ekranını gören, sesini duyan, konuşan ve bilgisayarını kontrol eden kişisel AI asistan.**

Sahibi ve geliştirici: Burak Emre Erdemci · Windows (32GB RAM, RX 6750 XT 12GB, Ryzen 5 7500F)  
Mac'te de çalışıyor (geliştirme ortamı), asıl hedef platform Windows.

---

## Güncel Durum (2026-04-19)

### Tamamlanan (Production)

- ✅ **Gemini Live native audio** — `gemini-3.1-flash-live-preview` ile gerçek zamanlı ses dialog
- ✅ **Tool sistemi** (12 araç): app aç/kapat, hava durumu, web arama, URL aç, Gmail, WhatsApp, ekran görme, browser ajan
- ✅ **Proaktif mod** — `send_video=True` ile 1 FPS ekran stream, Gemini Live ekranı sürekli izliyor
- ✅ **Conversation memory** — Session resetlendiğinde son 20 mesaj system prompt'a inject ediliyor
- ✅ **Mod sistemi** — Aktif pencereye göre system prompt değişiyor (Unreal / Unity / Code / Default)
- ✅ **Search pipeline** — Tavily → DDGS fallback → Flash Lite özetleme → Live'a temiz metin
- ✅ **Browser agent** — browser-use 0.5.x, Opera GX, CDP takeover, process-level task lock
- ✅ **Mail** — Gmail OAuth API (auto_send=true: direkt gönderir, false: compose URL açar)
- ✅ **WhatsApp** — URL scheme + pyautogui Enter (platform fark etmeksizin)
- ✅ **Electron UI** — Ses aç/kapat, live mod, proaktif mod toggle, mod göstergesi, log ekranı
- ✅ **VAD pipeline** — Silero VAD (legacy mod, Live mod kullanılmıyor)
- ✅ **Windows UTF-8 fix** — stdout/stderr reconfigure, PYTHONIOENCODING=utf-8

### Açık Sorunlar

- ⚠️ **VAD modu (legacy)**: Live kapalıyken aktif olan Whisper+VAD pipeline'ı maintenance modunda; ağırlıklı kullanım Live üzerinden.

### Planlanan

- ⏳ Ayarlar ekranı (VAD threshold, ses, dil)
- ⏳ Production build (PyInstaller + electron-builder)
- ⏳ pyautogui görev executor (mouse/keyboard kontrolü)
- ⏳ Computer use (v0.4) — browser-use + pyautogui + onay mekanizması
- ⏳ Gemini function calling ajanı (v0.5) — araç çağrısını JSON olarak döndür, metin üretme

---

## Mimari

```
Kullanıcı (ses)
      ↓
PyAudio mikrofon akışı (16kHz mono PCM)
      ↓
LiveSession._mic_loop() — ekoya karşı cooldown (0.8s)
      ↓
Gemini Live WebSocket (gemini-3.1-flash-live-preview)
      ↓                          ↑
  ses yanıtı (PCM 24kHz)    tool_call gelirse → _handle_tool_calls()
      ↓
PyAudio output stream
```

**Proaktif mod aktifse:**
```
LiveSession._video_loop() — 1 FPS, 720x720 JPEG → Gemini Live WebSocket
```

**Live modu kapalıysa (legacy):**
```
Mikrofon → VADGate (Silero) → faster-whisper → router.py → Gemini Flash/Lite → Edge TTS
```

---

## Dosya Yapısı

```
jarvan/
├── CLAUDE.md                          # Bu dosya
├── backend/
│   ├── main.py                        # FastAPI + WebSocket server, Pipeline yönetimi
│   ├── config.py                      # Tüm sabitler, .env yükleme
│   ├── contacts.json                  # İsim → email rehberi
│   ├── contacts_phones.json           # İsim → telefon rehberi
│   ├── credentials.json               # Gmail OAuth client secret (gitignore'da)
│   ├── token.json                     # Gmail OAuth token (gitignore'da)
│   ├── requirements.txt
│   ├── ai/
│   │   ├── assistant.py               # Legacy: Gemini Flash/Lite tek çağrı (VAD modu için)
│   │   ├── live_session.py            # Gemini Live — asıl AI motoru, tüm tool'lar burada
│   │   └── router.py                  # Legacy: Teknik/sohbet intent router (VAD modu için)
│   ├── audio/
│   │   ├── vad_gate.py                # Silero VAD — SILENCE/SPEECH/HANGOVER/FINALIZE state machine
│   │   └── transcriber.py             # faster-whisper (small, int8, Türkçe)
│   ├── screen/
│   │   └── capture.py                 # mss ekran yakala → PIL Image veya base64 JPEG
│   ├── tts/
│   │   └── speaker.py                 # Edge TTS (tr-TR-EmelNeural) — legacy VAD modu için
│   ├── modes/
│   │   ├── detector.py                # pygetwindow → aktif pencere → mod adı
│   │   └── prompts.py                 # UNREAL/UNITY/CODE/DEFAULT system prompt metinleri
│   └── tools/
│       ├── app_control.py             # open_app, close_app — cross-platform alias tablosu
│       ├── browser.py                 # open_url, search_web (Google), hidden_search (Tavily→DDGS)
│       ├── browser_agent.py           # browser-use ajan — otonom tarayıcı görevi
│       ├── contacts.py                # contacts.json / contacts_phones.json lookup
│       ├── mail.py                    # Gmail OAuth gönderim + compose URL fallback
│       ├── weather.py                 # Hava durumu (requests tabanlı)
│       └── whatsapp.py                # whatsapp:// URL scheme + pyautogui Enter
├── frontend/
│   ├── electron/
│   │   ├── main.ts                    # Electron ana process — backend spawn, IPC
│   │   └── preload.ts                 # IPC köprüsü (contextBridge)
│   └── src/
│       ├── App.tsx                    # Ana UI bileşeni
│       ├── types.ts                   # WebSocket mesaj tipleri
│       ├── hooks/                     # useWebSocket vb.
│       └── components/                # UI parçaları
```

---

## Modüller — Detaylı

### `backend/main.py`

FastAPI + WebSocket server. `Pipeline` sınıfı ses pipeline'ını ayrı thread'de yönetir.

**WebSocket mesajları (frontend → backend):**
- `{"type": "start"}` → pipeline.start()
- `{"type": "stop"}` → pipeline.stop()
- `{"type": "toggle_live", "enabled": bool}` → Live ↔ VAD geçişi
- `{"type": "toggle_proactive", "enabled": bool}` → 1 FPS video stream aç/kapat

**WebSocket mesajları (backend → frontend):**
- `{"type": "status", "running": bool, "live": bool, "proactive": bool}`
- `{"type": "mode", "name": "unreal"|"unity"|"code"|"default"}`
- `{"type": "log", "level": "user"|"jarvan"|"system"|"error", "text": str, "provider"?: str}`

**Conversation memory:** `Pipeline._emit_log()` her `user` ve `jarvan` logunu `conversation_memory` listesine ekler (max 20 mesaj). `LiveSession` yeniden bağlandığında bu liste system prompt'a inject edilir.

**Retry mekanizması:** Live oturum çöktüğünde 5 kez yeniden bağlanmaya çalışır. 30s'den kısa çalıştıysa retry sayacı sıfırlanmaz, exponential backoff (max 8s).

---

### `backend/ai/live_session.py`

Tüm projenin kalbi. Gemini Live WebSocket bağlantısı ve araç sistemi.

**Model:** `gemini-3.1-flash-live-preview`

**Config:**
```python
INPUT_SAMPLE_RATE = 16000   # Mikrofon
OUTPUT_SAMPLE_RATE = 24000  # Hoparlör
OUTPUT_COOLDOWN_S = 0.8     # Jarvan konuşunca eko engeli
VOICE_NAME = "Kore"         # Türkçe ses
```

**Session içindeki task'lar:**
1. `_mic_loop()` — PyAudio'dan 32ms chunk okur, Gemini'ye gönderir. Jarvan konuşurken + 0.8s sonrasına kadar suspend (eko engeli).
2. `_receive_loop()` — Ses, transkripsiyon ve tool_call alır. Tool gelince `_handle_tool_calls()` create_task ile spawn eder.
3. `_stop_watcher()` — Pipeline stop flag izler.
4. `_video_loop()` — (proaktif=True ise) 1 FPS, 720×720 JPEG, Gemini Live'a send_realtime_input(video=...).

**Duplicate tool call koruması:**
- `_inflight_tools: set[str]` — aynı anda iki kez çağrılamaz
- `_tool_cooldown: dict[str, float]` — browser_task tamamlanınca 90s cooldown

**System prompt yapısı (birleşik):**
```
modes/prompts.py → mod system prompt
+ VISION_BEHAVIOR_HINT_PROACTIVE veya VISION_BEHAVIOR_HINT_FALLBACK
+ TOOL_CONFIRMATION_HINT
+ RESEARCH_HINT
+ (varsa) conversation_memory inject
```

**Araçlar ve handler'ları:**

| Araç | Handler | Notlar |
|------|---------|--------|
| `open_app` | `asyncio.to_thread(open_app)` | app_control.py |
| `close_app` | `asyncio.to_thread(close_app)` | taskkill / osascript |
| `get_weather` | `asyncio.to_thread(get_weather)` | weather.py |
| `open_url` | `asyncio.to_thread(open_url)` | webbrowser.open |
| `search_web` | `asyncio.to_thread(hidden_search)` → `_summarize_search()` | Tavily→DDGS, Flash Lite özetleme |
| `open_result` | `last_search_results[idx]` → `open_url` | En son search sonuçlarını açar |
| `see_screen` | `_describe_screen()` | mss → JPEG → Gemini vision |
| `browser_task` | `run_browser_task()` | browser_agent.py, in-flight lock |
| `browser_start` | `asyncio.to_thread(launch_debug_browser)` | Opera GX CDP port açar |
| `browser_takeover` | `run_takeover_task()` | CDP'den mevcut browser'a bağlan |
| `send_mail` | `asyncio.to_thread(send_mail)` | OAuth veya compose URL |
| `send_whatsapp` | `asyncio.to_thread(send_whatsapp)` | URL scheme + pyautogui Enter |

**`_summarize_search()`:** Ham Tavily/DDGS sonucunu Flash Lite ile Türkçe 2-4 cümleye indirir. Live'a JSON/URL gitmez → 1011 WebSocket kapanma riski azalır.

**`_describe_screen()`:** mss ile ekran yakalar, 720×720 thumbnail, JPEG Q75, Gemini vision ile Türkçe 2-3 cümle analiz. Model sırası: `gemini-2.5-flash` → `gemini-2.5-flash-lite` → `gemini-3.1-flash-lite-preview`.

---

### `backend/tools/browser_agent.py`

browser-use 0.5.x tabanlı otonom tarayıcı ajanı.

**Sabitler:**
```python
CDP_PORT = 9223           # Jarvan'ın kendi debug browser portu
TASK_TIMEOUT_S = 480      # 8 dakika max
MAX_STEPS = 15
```

**Process-level task lock:**
```python
_TASK_LOCK = threading.Lock()
_TASK_RUNNING = bool
```
LiveSession yeniden bağlandığında `_inflight_tools` set'i sıfırlanır ama eski browser görevi hâlâ çalışıyor olabilir. Module scope lock bunu engeller — hangi LiveSession instance'ı olursa olsun aynı flag görülür.

**LLM rotasyonu (`RotatingChatGoogle`):**
`browser_use.llm.ChatGoogle`'dan kalıtım alır (isinstance kontrolü zorunlu). Rolling 60s RPM penceresi — `deque` tabanlı call tracking. Pool:
```python
MODEL_POOL = [
    ("gemma-4-26b-a4b-it", 15),           # 1500 RPD
    ("gemini-3.1-flash-lite-preview", 15), # 500 RPD
]
SAFETY_MARGIN = 1  # limitin 1 altında anahtarla
```

**`run_browser_task(task)` akışı:**
1. Task slot kontrolü (`_try_acquire_task_slot`)
2. `_cdp_up(9223)` → True ise CDP'ye bağlan
3. False ise `launch_debug_browser(9223)` → Opera GX başlat
4. Hâlâ False ise → fresh Chromium (BROWSER_PROFILE_DIR)
5. `controller = Controller(exclude_actions=["extract_structured_data"])` — prompt yasağı yetmediği için action seviyesinde hard disable
6. `agent.run(max_steps=15, timeout=480s)`
7. `history.final_result()` → 600 char limit, Attachments/ kesimi

**`launch_debug_browser(port)`:**
```
BROWSER_BINARY (Opera GX) + --remote-debugging-port={port} + --user-data-dir=BROWSER_PROFILE_DIR
```
- Windows: `%LOCALAPPDATA%\Programs\Opera GX\opera.exe`
- Mac: `/Applications/Opera GX.app/Contents/MacOS/Opera`
- Jarvan'a ait ayrı profil kullanır (BROWSER_PROFILE_DIR) — kullanıcının asıl Opera'sı açıkken SingletonLock çakışmasını önler
- İlk açılışta kullanıcı bir kez login yapar, sonra kalıcı

**`run_takeover_task(task)`:**
Kullanıcı "devral", "kaldığım yerden devam et" dediğinde. CDP :9223'e bağlanır, kullanıcının açık tab'larından devam eder. CDP kapalıysa hata döner (auto-launch yok — takeover için kullanıcının debug modda açtığı browser şart).

**`_READ_ONLY_PREFIX`** — tüm browser görevlerine eklenen güvenlik + taktik prompt:
- `extract_structured_data` yasağı (HTML parsing timeout)
- Uçuş: Google Flights (iç hat) / Enuygun (dış hat)
- CAPTCHA görürse 60s bekle, human-in-the-loop
- Sonucu ekrandan oku, done ile KISA özetle

**Platform profil yolları:**
```python
# Jarvan'ın kendi profili (BROWSER_PROFILE_DIR):
# Windows: %LOCALAPPDATA%\jarvan-opera-profile
# Mac: ~/Library/Application Support/jarvan-opera-profile

# Kullanıcının gerçek Opera profili (_resolve_real_opera_profile):
# Windows: %APPDATA%\Opera Software\Opera GX Stable
# Mac: ~/Library/Application Support/com.operasoftware.OperaGX
```

---

### `backend/tools/browser.py`

**`open_url(url)`** — `webbrowser.open()` ile varsayılan tarayıcıda aç.

**`hidden_search(query)`** — Arka planda Tavily API çağırır, fail olursa DuckDuckGo (ddgs). Tarayıcı açmaz. `live_session._summarize_search()` bunu çağırır.

---

### `backend/tools/mail.py`

**`send_mail(to, subject, body, auto_send)`**

`to` → `contacts.resolve_email()` → email adresi (rehberde isim varsa çevirir)

- `auto_send=True`: Gmail API (OAuth) → direkt gönderir. `credentials.json` ve `token.json` gerekli.
- `auto_send=False`: `https://mail.google.com/mail/?view=cm&...` compose URL aç.

OAuth flow: `token.json` yoksa veya süresi dolmuşsa `InstalledAppFlow` → localhost'ta browser açar.

---

### `backend/tools/whatsapp.py`

**`send_whatsapp(message, phone=None)`**

`phone` → `contacts.resolve_phone()` → numara (rehberde isim varsa çevirir)

Akış:
1. `whatsapp://send?phone={num}&text={msg}` URL'sini `webbrowser.open()` ile aç
2. WhatsApp başlamasını bekle (5s eğer çalışmıyorsa, 3s çalışıyorsa)
3. Enter bas: Mac=osascript keystroke, Windows=pygetwindow+pyautogui

---

### `backend/tools/app_control.py`

`APP_ALIASES` dict'i: uygulama adı → `{win: exe, mac: app_name}`.

- `open_app`: Windows → `cmd /c start "exe"`, Mac → `open -a "App"`
- `close_app`: Windows → `taskkill /IM exe /F`, Mac → osascript quit → pkill fallback

---

### `backend/tools/weather.py`

`requests` ile `wttr.in/?format=j1` JSON API çağırır. Şehir adını alır, anlık + yarınki hava döner.

---

### `backend/modes/`

**`detector.py`:** `pygetwindow.getActiveWindow()` → pencere başlığı → `WINDOW_MODE_MAP` eşleşmesi.

```python
WINDOW_MODE_MAP = [
    (["Unreal", "UE5", "UE4"], "unreal", UNREAL_PROMPT),
    (["Unity"], "unity", UNITY_PROMPT),
    (["Visual Studio Code", "Code", "Cursor", "PyCharm", "Rider", "CLion"], "code", CODE_PROMPT),
]
# Eşleşme yoksa → "default", DEFAULT_PROMPT
```

**`prompts.py`:** Her mod için ayrı system prompt. Tümü Türkçe, samimi ton. Sesli asistan kuralları (max 2-3 cümle, markdown yok, liste yok) sadece DEFAULT_PROMPT'ta; diğer modlarda daha teknik.

---

### `backend/audio/vad_gate.py` (legacy)

Silero VAD tabanlı state machine. Live mod kullanılmıyorsa devreye girer.

```
State: SILENCE → SPEECH → HANGOVER → (4s sonra) SILENCE + FINALIZE
```

Parametreler (Omi'den alındı):
```python
VAD_GATE_SPEECH_THRESHOLD    = 0.65
VAD_GATE_HANGOVER_MS         = 4000  # 4s bekle, cümle ortasında kesme
VAD_GATE_FINALIZE_SILENCE_MS = 300
```

---

### `backend/audio/transcriber.py` (legacy)

```python
WhisperModel("small", device="cpu", compute_type="int8")
# language="tr", beam_size=5, vad_filter=False (VAD bizde)
```

---

### `backend/screen/capture.py`

`mss` ile ekran yakalar. `SCREEN_MONITOR_INDEX=2` (config.py) → ikinci monitör. PIL Image veya base64 JPEG döner.

---

### `backend/tts/speaker.py` (legacy)

`edge-tts tr-TR-EmelNeural` + `pygame` ile ses çalar. Sadece VAD modu için; Live modda Gemini'nin kendi native audio'su kullanılıyor.

---

### `backend/config.py`

```python
GEMINI_API_KEY     # .env'den
TAVILY_API_KEY     # .env'den, search_web için
MY_WHATSAPP        # .env'den, kullanıcının kendi numarası
SCREEN_MONITOR_INDEX = 2   # İkinci monitör
```

---

### Frontend (Electron + React + Vite)

**Stack:** Electron 33, React 18, TypeScript, Tailwind CSS, Framer Motion, Lucide

**Başlatma:**
```
npm run dev → Vite build → Electron main → backend spawn (python main.py) → WebSocket /ws bağlantısı
```

**UI:**
- Ses aç/kapat (start/stop pipeline)
- Live mod toggle (Gemini Live ↔ VAD)
- Proaktif mod toggle (1 FPS video stream)
- Aktif mod göstergesi (Unreal / Unity / Code / Default)
- Log ekranı (user / jarvan / system / error)

---

## Kurulum

### .env (backend/.env)
```
GEMINI_API_KEY=...
TAVILY_API_KEY=...       # opsiyonel, DDGS fallback var
MY_WHATSAPP=905XXXXXXXXX # ülke koduyla, + olmadan
```

### Gmail OAuth
```
backend/credentials.json → Google Cloud Console'dan indir
İlk çalıştırmada browser açılır → giriş yap → token.json oluşur
```

### Python
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python main.py           # Direkt test
```

### Frontend
```bash
cd frontend
npm install
npm run dev              # Electron + Vite dev mode
```

---

## Browser Agent Debug

Windows'ta browser agent sorun çıkardığında:

```powershell
cd C:\...\JARVAN\backend
.venv\Scripts\python.exe -c "
from tools.browser_agent import _cdp_up, launch_debug_browser, BROWSER_BINARY, BROWSER_PROFILE_DIR, CDP_PORT
print('binary:', BROWSER_BINARY)
print('profile_dir:', BROWSER_PROFILE_DIR)
print('cdp_up_before:', _cdp_up(CDP_PORT))
print('launch_result:', launch_debug_browser())
print('cdp_up_after:', _cdp_up(CDP_PORT))
"
```

**Beklenen:** `binary` Opera GX path döner, `launch_result` ok=True, `cdp_up_after` True.

**Sıkça çıkan sorunlar:**
- `binary: None` → Opera GX kurulu değil ya da PATH farklı
- `cdp_up_after: False` → Opera GX başka bir pencerede açık ve BROWSER_PROFILE_DIR'ı kilitlemiş; Opera'yı kapat, tekrar dene
- `SingletonLock` → `_cleanup_singleton_locks()` BROWSER_PROFILE_DIR'daki lock dosyalarını siler

---

## Bilinen Kararlar / Trade-off'lar

| Karar | Sebep |
|-------|-------|
| Live native audio (Gemini) → VAD/Whisper/TTS yok | Gecikme ~200ms, VRAM harcamıyor, Türkçe kalitesi iyi |
| browser-use 0.5.x + RotatingChatGoogle kalıtımı | isinstance kontrolü nedeniyle ChatGoogle'dan kalıtım şart |
| `extract_structured_data` action seviyesinde disable | Prompt yasağı yetersiz, 80-130s timeout Live session'ı donduruyor |
| `keep_alive=False` (BrowserProfile) | True ise `session.stop()` hang ediyor, tool response gitmiyor |
| Jarvan'a ayrı Opera profili (BROWSER_PROFILE_DIR) | Kullanıcının asıl Opera'sı açıkken SingletonLock çakışmasını önler |
| CDP port 9223 (9222 değil) | 9222 kullanıcının kendi debug browser'ında olabilir |
| Tavily → DDGS fallback | Tavily 1000 istek/ay, DDGS sınırsız ama daha yavaş |
| Conversation memory = 20 mesaj system prompt inject | Live WebSocket kopunca bağlam kaybolur; inject ile süreklilik |
| search_web sonucu Flash Lite ile özetlenir | Ham JSON/URL Live'a giderse 1011 kapanma riski artar |
| Tool response'ta `_instruction` yok | Meta-field modeli konfüze edip halüsinasyona sebep oluyordu |
| Keepalive (boş text frame) kaldırıldı | turn_complete=False frame'leri tool sonrası halüsinasyona yol açıyordu |

---

## Yol Haritası

### v0.1 ✅ — VAD MVP
Silero VAD + Whisper + Gemini Flash + Edge TTS + mss ekran

### v0.2 ✅ — Gemini Live
Native audio dialog, 1 FPS video stream, proaktif mod, Live session

### v0.3 ✅ — Context & Araçlar
Conversation memory, browser agent, Gmail, WhatsApp, web arama, hava durumu, mod sistemi

### v0.4 — Computer Use
- `pyautogui` görev executor (mouse/keyboard)
- Tüm aksiyonlarda sesli onay mekanizması ("X'i yapacağım, onaylıyor musun?")
- Sandbox modu (tehlikeli görevleri simüle et)

### v0.5 — Ultra-Low Latency Agentic
- Gemini function calling ile metin yerine JSON tool response
- Gemini Live native audio'yu fully exploit et (300ms R-T-T hedefi)
- User context state JSON olarak system prompt'a

### v0.6 — Tam Otonomi
- Proaktif inisiyatif (UE5 açıldığını detect edince kendisi konuşsun)
- Shadow Coder (ekran geçmişi, rewind asistanı)
- RAG + ChromaDB (kullanıcı davranış vektörleri)
- Telegram remote execute tüneli

---

## Geliştirici

**Burak Emre Erdemci**  
[burakerdemci.com](https://burakerdemci.com) · [github.com/BurakErdemci](https://github.com/BurakErdemci)
