# 🤖 Jarvan

**Ekranını gören, sesini duyan, gerektiğinde konuşan kişisel AI asistan.**

> Bir developer'ın kendi ihtiyacı için yaptığı şey. Ürün değil, araç.

---

## 📍 Mevcut Durum (2026-04-17)

**Geliştirme ortamı değişti:** Mac (16GB) → Windows (32GB RAM + RX 6750 XT 12GB VRAM + Ryzen 5 7500F). Mac'te local LLM RAM yetmediği için swap'e düşüyor, Windows'a taşındı.

### Tamamlanan (v0.1 kısmı)

- ✅ **Silero VAD** — `backend/audio/vad_gate.py` (Omi parametreleriyle: 300ms pre-roll, 4sn hangover, 0.65 threshold)
- ✅ **faster-whisper** — `backend/audio/transcriber.py` (small model, int8, Türkçe)
- ✅ **mss screenshot** — `backend/screen/capture.py`
- ✅ **Gemini 3 Flash (cloud)** — `backend/ai/assistant.py` (`gemini-3-flash-preview`, vision destekli)
- ✅ **Local LLM (Ollama)** — `backend/ai/local_llm.py` (Qwen3-VL:8b, vision destekli, `think=False`)
- ✅ **3-Tier Router** — `backend/ai/router.py` (regex intent filter):
  - Teknik kelime → cloud Gemini + vision
  - Ekran bahsi → local Qwen3-VL + vision
  - Sade sohbet → local Qwen3-VL (ekran yok)
- ✅ **Edge TTS** — `backend/tts/speaker.py` (`tr-TR-EmelNeural`) — *Kokoro yerine Edge seçildi, daha doğal Türkçe*
- ✅ **Pipeline test** — `backend/test_pipeline.py` (mikrofon → VAD → Whisper → router → TTS, uçtan uca)

### Windows'a Geçiş İşleri

1. Repoyu GitHub'dan Windows'a klonla
2. Python 3.12 venv, `pip install -r backend/requirements.txt`
3. Ollama Windows kur → `ollama pull qwen3-vl:8b`
4. ROCm sürücüsü doğrula (AMD GPU ivmesi) — `ollama run qwen3-vl:8b` test
5. `.env` oluştur → `GEMINI_API_KEY` ekle
6. `python backend/test_pipeline.py`

### Sıradaki İş (Windows'ta)

- ⏳ **Mod sistemi** — aktif pencere tespiti (pygetwindow/pywin32) → dynamic system prompt (Unreal / Unity / Code / default)
- ⏳ **Gemini Flash Lite intent filter** — regex yerine LLM tabanlı filtre
- ⏳ **FastAPI backend** — `main.py` WebSocket handler (test_pipeline'ı server'a çevir)
- ⏳ **Electron UI** — minimal toggle + mod göstergesi + log
- ⏳ **Timestamp sync** — ses/ekran hizalaması (Omi'deki `DgWallMapper` pattern)

### Bilinen Kararlar / Trade-off'lar

- **Kokoro yerine Edge TTS** → Türkçe kalitesi daha iyi, local çalışıyor
- **Qwen3-VL:8b + `think=False`** → thinking açıkken "selam nasılsın"a bile 1dk düşünüyor, voice assistant için kapatıldı
- **Router regex tabanlı** → v0.1 için yeterli, v0.3'te Flash Lite'a geçiş planlı
- **3-tier local-first** → cloud sadece teknik sorular için, günlük kullanım rate limit'e takılmaz

---

## Neden Jarvan?

Unreal Engine'de Blueprint düğümlerinde takılıyorum. Kod yazarken bir şeyi anlayamıyorum. Google'da arıyorum, Stack Overflow'a bakıyorum, ChatGPT'ye soruyorum — her seferinde context kayboluyor, ekranımı göremiyorlar, ne yaptığımı bilmiyorlar.

İstediğim şey basit: ekranıma bakan, ne yaptığımı anlayan, sesimi duyan ve **gerektiğinde** konuşan bir sistem. Sürekli yorum yapmayan ama takıldığımda orada olan biri.

Omi gibi projeler var ama güvenmiyorum — ne gönderdiğini bilmiyorsun, verilen bilgisayarında ne kadar kalıyor belli değil.

Jarvan tamamen kendi bilgisayarımda çalışıyor. STT local, VAD local, TTS local. Sadece AI çağrısı buluta gidiyor, o da sadece gerçekten gerektiğinde.

---

## Mimari Özeti

```
Mikrofon
    ↓
Silero VAD (local — konuşma var mı?)
    ↓ konuşma tespit edildi
faster-whisper (local — metne çevir)
    ↓ cümle tamamlandı
Intent Filter (local — AI'a gönderilmeli mi?)
    ↓ evet
mss → ekran görüntüsü al
    ↓
Gemini 3 Flash API (ses transkripsiyonu + ekran = yanıt)
    ↓
Kokoro TTS (local — yanıtı seslendir)
```

**Katmanlı aktivasyon:** Gemini'ye sadece intent filter "bunu görmeli" dediğinde gidiliyor. Sessizlik, dolgu sesler, kısa onaylar hiçbir zaman API'a gitmiyor.

---

## Teknoloji Stack'i

### Ses Katmanı (Tamamen Local)
| Teknoloji | Görev | Neden |
|-----------|-------|-------|
| **Silero VAD** | Konuşma tespiti | Omi'nin production-tested mimarisi, 16 model instance pool, SPEECH→HANGOVER→SILENCE state machine |
| **faster-whisper** | Speech-to-text | Whisper'ın 4x hızlı versiyonu, Türkçe destekli, gerçek zamanlı streaming modu |

### Görsel Katman (Tamamen Local)
| Teknoloji | Görev | Neden |
|-----------|-------|-------|
| **mss** | Ekran görüntüsü | Cross-platform, 3ms/screenshot, bağımlılık yok |

### AI Katmanı (Bulut — Sadece Gerektiğinde)
| Teknoloji | Görev | Neden |
|-----------|-------|-------|
| **Gemini 3 Flash** | Ana AI beyni | Vision destekli, ücretsiz tier (5 RPM), Unity AI'da test edildi |
| **Gemini 3.1 Flash Lite** | Intent filter | 15 RPM, ucuz filtre katmanı — "bu API'a gitsin mi?" kararı |

### Ses Üretim Katmanı (Tamamen Local)
| Teknoloji | Görev | Neden |
|-----------|-------|-------|
| **Kokoro TTS** | Text-to-speech | 2025'te çıktı, local çalışıyor, insan sesi kalitesinde, ücretsiz |

### Uygulama Katmanı
| Teknoloji | Görev | Neden |
|-----------|-------|-------|
| **Python + FastAPI** | Backend | Zaten bilinen stack, async, Silero + Whisper entegrasyonu kolay |
| **Electron** | Desktop UI | Unity Architect AI'dan gelen deneyim, cross-platform build |

---

## VAD Mimarisi (Omi'den Öğrenilen)

Omi kaynak kodundan alınan production-tested parametreler:

```python
VAD_GATE_PRE_ROLL_MS        = 300    # Konuşmadan 300ms önceyi de yakala
VAD_GATE_HANGOVER_MS        = 4000   # Sessizlik sonrası 4sn daha "konuşuyor" say
VAD_GATE_SPEECH_THRESHOLD   = 0.65   # Silero speech probability eşiği
VAD_GATE_FINALIZE_SILENCE_MS = 300   # Bu kadar sessizlik → cümle bitti
```

State machine:
```
SILENCE → (ses algılandı) → SPEECH → (ses kesildi) → HANGOVER → SILENCE
                                                        ↑
                                           4sn bekle, cümle devam edebilir
```

Neden 4 saniye hangover? Çünkü "şey... bunu nasıl yapıyorum ki" gibi cümlelerde insan doğal olarak duraklıyor. 4 saniye beklemeden kesilirse cümle ortasında transkripsiyona giriyor.

---

## Token Optimizasyonu

### Katmanlı Savunma

**Katman 1 — Silero VAD (sıfır maliyet)**
Sessizlik, arka plan gürültüsü, "hmm", "aa" gibi dolgu sesler hiçbir zaman Whisper'a gitmiyor.

**Katman 2 — faster-whisper (sıfır maliyet)**
Sadece gerçek konuşma segmentleri transkribe ediliyor. Token yok, API yok.

**Katman 3 — Intent Filter (Gemini 3.1 Flash Lite)**
Transkripsiyon tamamlandıktan sonra ucuz bir filtre: "bu Gemini 3 Flash'a gönderilmeli mi?"

Geçmeyen örnekler:
- "tamam", "evet", "oldu" → ignore
- "aa", "hmm" → ignore
- kısa onaylar → ignore

Geçen örnekler:
- soru içeren cümleler
- "nasıl", "neden", "ne", "anlamadım" içeren ifadeler
- hata mesajı görüntüde + sesli tepki

**Katman 4 — Gemini 3 Flash (API)**
Sadece buraya kadar gelen içerik pahalı modele ulaşıyor. Ses transkripsiyonu + ekran görüntüsü birlikte gönderiliyor.

### Rate Limit Hesabı

Günde 2 saat aktif kullanım, katmanlı filtre sonrası ~50-100 Gemini 3 Flash çağrısı.
Ücretsiz tier: günde 500 istek. Fazlasıyla yeterli.

---

## Ekran + Ses Timestamp Hizalaması

Omi kaynak kodunda `DgWallMapper` sınıfı: VAD sessizliği atladığında STT'nin timestamp'leri gerçek zamandan kayıyor.

Jarvan'da da aynı sorun olacak: VAD "konuşma var" dediğinde ekran görüntüsü alınıyor, ama VAD'ın timestamp'i ile gerçek zaman arasında küçük bir kayma var. Bu bileşen baştan planlanmalı.

---

## Omi'den Öğrenilenler

BasedHardware/omi kaynak kodu analiz edildi. Kritik bulgular:

1. **VAD olmadan maliyet kontrolsüz büyür** — Silero VAD active modda tüm sessizliği kesiyor, Deepgram'a sadece gerçek konuşma gidiyor
2. **Hangover mekanizması kritik** — 4sn beklemeden cümle ortasında kesiyorsun
3. **should_discard() pattern'i çal** — ucuz modelle ön filtre, pahalı modeli koru
4. **Timestamp remapping kaçınılmaz** — VAD + STT + ekran üç farklı zaman ekseninde çalışıyor
5. **Model pool şart** — tek global Silero instance bottleneck yaratıyor, Omi 16 kopya kullanıyor

---

## Klasör Yapısı (Planlanan)

```
jarvan/
├── backend/
│   ├── main.py                    # FastAPI + WebSocket handler
│   ├── audio/
│   │   ├── vad_gate.py            # Silero VAD streaming gate (Omi pattern)
│   │   ├── transcriber.py         # faster-whisper entegrasyonu
│   │   └── recorder.py            # Mikrofon akışı yönetimi
│   ├── screen/
│   │   ├── capture.py             # mss screenshot
│   │   └── timestamp_sync.py      # Ses-ekran timestamp hizalaması
│   ├── ai/
│   │   ├── intent_filter.py       # Gemini Flash Lite — gönderilmeli mi?
│   │   ├── assistant.py           # Gemini 3 Flash — ses + ekran → yanıt
│   │   └── providers.py           # Multi-provider (Gemini, fallback Ollama)
│   ├── tts/
│   │   └── kokoro.py              # Kokoro TTS — yanıtı seslendir
│   └── config.py                  # VAD parametreleri, threshold'lar
├── frontend/
│   ├── main/
│   │   ├── background.ts          # Electron ana süreç
│   │   └── preload.ts             # IPC köprüsü
│   └── renderer/
│       └── pages/
│           └── home.tsx           # Ana UI (durum göstergesi, log, ayarlar)
├── docker-compose.yml
├── requirements.txt
└── JARVAN.md                      # Bu dosya
```

---

## Geliştirme Notları

### VAD Başlatma
```python
from silero_vad import load_silero_vad

# Model pool — single instance bottleneck'i önle
VAD_MODEL_POOL_SIZE = 4  # Başlangıç için 4, production'da 16
```

### faster-whisper Başlatma
```python
from faster_whisper import WhisperModel

model = WhisperModel(
    "small",          # Türkçe için small yeterli
    device="cpu",     # GPU yoksa cpu
    compute_type="int8"  # Hız için quantization
)
```

### mss Ekran Yakalama
```python
import mss
import mss.tools

with mss.mss() as sct:
    screenshot = sct.grab(sct.monitors[0])
    # Base64'e çevir → Gemini'ye gönder
```

### Gemini Vision Çağrısı
```python
import google.generativeai as genai

model = genai.GenerativeModel("gemini-3-flash-preview")
response = model.generate_content([
    transcript,      # Ses transkripsiyonu
    screenshot_img,  # mss ile alınan ekran görüntüsü
    system_prompt    # Jarvan'ın kişiliği ve kuralları
])
```

---

## Privacy Notları

- Ses transkripsiyonu: **tamamen local** (faster-whisper)
- VAD: **tamamen local** (Silero)
- TTS: **tamamen local** (Kokoro)
- Ekran görüntüsü: sadece Gemini çağrısı tetiklendiğinde, sadece o an alınıyor
- Gemini API: ses transkripsiyonu + ekran görüntüsü Google sunucularına gidiyor — bu bilinçli bir trade-off

Omi'den fark: Omi ne gönderdiğin belirsiz, sürekli buluta akıyor. Jarvan'da hangi verinin ne zaman nereye gittiği kod üzerinden takip edilebilir.

---

## Mod Sistemi

Jarvan "her şeyi yapan asistan" değil — hangi uygulama ön planda olduğuna göre moda giren bir sistem. Tek Gemini çağrısı gidiyor ama system prompt değişiyor.

```python
active_window = get_active_window()

if "Unreal" in active_window:
    mode = "developer_unreal"
    system_prompt = UNREAL_PROMPT      # Blueprint, C++, UE5 ağırlıklı
elif "Unity" in active_window:
    mode = "developer_unity"
    system_prompt = UNITY_PROMPT       # C#, Unity API, game feel
elif "Code" in active_window or "Cursor" in active_window:
    mode = "developer_code"
    system_prompt = CODE_PROMPT        # Genel yazılım, debug
elif is_short_question(transcript):
    mode = "assistant"
    system_prompt = ASSISTANT_PROMPT   # Kısa, hızlı yanıt
else:
    mode = "default"
    system_prompt = DEFAULT_PROMPT     # Dengeli genel asistan
```

Her mod ayrı bir system prompt dosyası. Dev modları teknik bilgi ağır, assistant modu hafif ve hızlı. Token israfı yok, odak kaybolmuyor.

---

## Gemini Live API — Video Akışı

Bazı sorunlar screenshot ile çözülemiyor. Karakterin koşma animasyonu bozuk — sadece koşarken oluyor, tek frame'de göremezsin. O anı göstermek için gerçek zamanlı video lazım.

**Gemini Live API** tam bu iş için:
- Ses + video akışını aynı anda gerçek zamanlı işliyor
- Düşük gecikmeyle yanıt veriyor
- `gemini-3.1-flash-live-preview` — Mart 2026 itibarıyla free tier'da ücretsiz
- WebSocket tabanlı, sürekli stream

Senaryo:
```
"Koşma animasyonu bozuk, şu an görüyor musun?"
    ↓
Gemini Live ekranı gerçek zamanlı izliyor
    ↓
Animasyon bozulduğu anda tam o frame'i görüyor
    ↓
"Root motion kapalı, şu kemik rotasyonu yanlış görünüyor..."
```

v0.1'deki screenshot sistemiyle başlanıyor, v0.2'de Gemini Live'a geçiliyor. Mimari değişiklik büyük — WebSocket stream, farklı VAD yaklaşımı, yeni ses pipeline — o yüzden ayrı bir sprint.

---

## Yol Haritası

### v0.1 — MVP (Screenshot tabanlı)
- [x] Silero VAD entegrasyonu (Omi parametreleriyle)
- [x] faster-whisper transkripsiyon
- [x] Basit intent filter (regex tabanlı, `backend/ai/router.py`)
- [x] mss ekran görüntüsü + Gemini 3 Flash
- [x] Local LLM (Qwen3-VL:8b, Ollama) + 3-tier router (cloud/local-vision/local-text)
- [ ] Mod sistemi (active window tespiti + dynamic system prompt)
- [x] ~~Kokoro TTS~~ → Edge TTS (`tr-TR-EmelNeural`)
- [ ] Minimal Electron UI (açık/kapalı toggle, aktif mod göstergesi, log)

### v0.2 — Gemini Live (Video & Hybrid Stream)
- [x] Gemini Live API entegrasyonu (`gemini-3.1-flash-live-preview`)
- [x] Ses + Ekran video stream — (1 FPS WebSocket Sürekli Yayın Mimarisi)
- [x] Proaktif mod kapalıyken 2.5 Flash Native (Audio) ile ucuz limitli kullanım sağlanması
- [x] VAD olmadan direkt Live Session mikrofon stream yapısı kurulması
- [x] Kullanıcı UI entegrasyonu (Mod göstergeleri, Proaktif Toggle, Log ekranı)
- [x] Proaktif mod (Video yayını) anında aç/kapa yapıldığında sistemin kendini adapte etmesi

### v0.3 — Context & Hafıza (Kişiselleştirme)
- [x] Kullanıcı bağlamı hafızası (Sürekli Hafıza - `main.py` içerisinden son 20 mesajın enjektesi)
- [x] Modlar arası (Live/Proaktif) geçişte kopan bağlantılarda anlık durum kurtarması
- [ ] Ayarlar ekranı (VAD threshold, dil, ses tipi değiştirme arayüzü)
- [ ] Production build (PyInstaller + electron-builder)

### v0.4 — Computer Use (PC Kontrolü)

Jarvan'ın "benim yerime iş yap" modu. "Git şu siteye gir", "mail at", "şu dosyayı taşı" gibi görevleri sesle veriyor, Jarvan execute ediyor.

**Araç stack'i:**

| Görev türü | Araç | Neden |
|-----------|------|-------|
| Tarayıcı görevleri (mail, form, web) | `browser-use` | 55k star, Playwright + LLM, Gemini destekli, aktif |
| Sistem görevleri (dosya, uygulama, mouse) | `pyautogui` | Pure Python, cross-platform, sıfır bağımlılık |

**Akış:**

```python
task = "Gmail'i aç ve şu kişiye mail at"

# Görev türünü belirle
if is_browser_task(task):
    browser_use_agent.run(task)   # Playwright ile tarayıcı kontrolü
elif is_system_task(task):
    pyautogui_agent.run(task)     # Mouse/keyboard kontrolü
```

**Onay mekanizması — zorunlu:**

Jarvan hiçbir zaman onaysız execute etmiyor. Her görev öncesi sesli özet:

```
"Gmail'i açacağım, burak@gmail.com adresine 
'Toplantı yarın saat 3' yazacağım ve göndereceğim.
Onaylıyor musun?"
    ↓
Sen "evet" diyorsun
    ↓
Execute
```

Bu hem güvenlik hem Jarvan'ın "kontrollü, güvenilir" felsefesiyle uyuşuyor. OpenClaw gibi arka planda özerk çalışan bir sistem değil — her kritik adımda sen onaylıyorsun.

**Neden OpenClaw değil:**
OpenClaw messaging platform üzerinden çalışıyor, ne gönderdiği belirsiz, özerk davranış riskleri var (kullanıcıların mail inboxlarını silmiş, izinsiz profil oluşturmuş vakaları belgelenmiş). Jarvan'da görev pipeline'ı şeffaf ve onay gerektiriyor.

- [ ] `browser-use` entegrasyonu (Gemini destekli Playwright agent)
- [ ] `pyautogui` görev executor
- [ ] Onay mekanizması (sesli özet → kullanıcı onayı → execute)
- [ ] Görev türü sınıflandırıcı (browser task mı, system task mı?)
- [ ] Hata yönetimi (yanlış tıklama, sayfa yüklenmedi, popup çıktı)
- [ ] Sandbox modu (tehlikeli görevleri önce simüle et)

### v0.5 — Agentic Operations & Ultra-Low Latency Pipeline (Jarvis Paradigm)

Bu fazın temel amacı; sistemin pasif bir "soru-cevap" asistanından çıkıp, **işletim sistemi seviyesinde otonom** (agentic) işlemleri **300ms** barajının altında tepki (R-T-T) vererek yürütebilmesidir. Başka bir AI ajanı projeyi devraldığında uygulanması gereken mimari prensipler şunlardır:

**1. Architectural Shift: Function Calling (Tool Use)**
- Gemini / Claude modellerinin `tools` veya `function_declarations` API'leri entegre edilecek.
- Model, kullanıcı komutunu ("CS:GO aç") anladığında önce metin üretmeyecek; doğrudan `{"name": "execute_program", "args": {"target": "csgo.exe"}}` JSON'ı dönecek.
- `main.py` üzerindeki event loop, bu JSON'u parse edip `pyautogui` veya `subprocess` ile paralel thread'de çalıştıracak.

**2. Ultra-Low Latency & Native Speech (Gemini Live Advantage)**
- Ağır lokal TTS modelleri (Chatterbox vb.) VRAM dar boğazına sebep olacağından kullanılmayacaktır. 
- Hedef: Halihazırda var olan `Gemini 3.1 Flash Live` modelinin doğal, stream'li "Native Audio Dialog" sistemi sonuna kadar sömürülecektir. Google'ın kendi sunucularından gelen 200-300ms gecikmeli ses sentezi, sistemi sıfır VRAM harcayarak akıcı tutar.

**3. Contextual Persona & Memory State**
- Sistem, kullanıcının envanterini bilecek (Oynanan oyunlar, kurulu dizinler, favori yayın sahneleri). Bu statik context, system prompt içerisine JSON state olarak yerleştirilecek.
- Örn: `{"user_context": {"favorite_game": "CS:GO", "obs_scene": "Gameplay"}}`

---

## Geliştirici

**Burak Emre Erdemci**
[burakerdemci.com](https://burakerdemci.com) · [github.com/BurakErdemci](https://github.com/BurakErdemci)

---

*"Bunu ben kullanabilirim" hissiyle başladı.*