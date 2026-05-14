# JARVAN — Kişisel Yapay Zeka Dijital İkiz

> *"Jarvan sadece bir yazılım değildir; o, senin dijital dünyadaki kılıcın, kalkanın ve sadık yoldaşındır."*

JARVAN, Tony Stark'ın JARVIS'inden ilham alan kişisel bir yapay zeka asistanıdır. Sıradan bir chatbot değil — seni tanıyan, ekranını gören, sesini duyan, bilgisayarını kontrol eden ve sürekli öğrenen bir **Dijital İkiz**dir.

[🇬🇧 English README](README.md)

---

## Nedir?

JARVAN'ı diğer asistanlardan ayıran birkaç temel özellik:

- **Ses + Görme**: Mikrofondan sesi ve ekranı aynı anda alıp anlık yorum yapar
- **Kalıcı Hafıza**: Konuşmalar arasında sıfırlanmaz — ne sevdiğini, ne zaman verimli çalıştığını öğrenir
- **Proaktif Davranış**: Komut beklemez; ekrandaki durumu fark edip önce o konuşur
- **Araç Entegrasyonu**: Spotify, Gmail, hava durumu, uygulama kontrolü, dosya yönetimi ve daha fazlası
- **Sürekli Öğrenme**: Her konuşma sonunda arka planda insight çıkarır, ChromaDB'ye yazar

---

## Mimari

```
Kullanıcı (ses + ekran)
         │
         ▼
    Vosk Wake Word          ← "Uyan Jarvan" → uyandır
         │
         ▼
  FastAPI Backend           ← kalıcı beyin, tüm state burada
    ├── memory.json         ← yapısal hafıza (tercihler, rutinler)
    └── ChromaDB            ← davranışsal RAG hafızası
         │
         ▼
   Gemini Live API          ← ~200ms ses gecikme, ekran + ses aynı anda
    ├── gemini-3.1-flash-live-preview  (orchestrator)
    └── tool_calls → ToolExecutor
         │
    ┌────┼────┬────────────────┐
    ▼    ▼    ▼                ▼
Spotify Gmail Hava  …  Gemini CLI Worker
                           └── gemini-3.1-pro (ağır görevler)
```

**Kritik kural:** Hafıza FastAPI backend'de yaşar. Gemini Live oturumu bittiğinde hafıza ölmez. Her yeni oturumda ChromaDB + memory.json inject edilir.

---

## Teknoloji Yığını

| Katman | Teknoloji | Gerekçe |
|--------|-----------|---------|
| Sesli Diyalog | Gemini Live (gemini-3.1-flash-live) | ~200ms gecikme, ses + ekran aynı anda |
| Ağır Görevler | Gemini CLI (gemini-3.1-pro-preview) | 2M+ context, kod yazma, refactor |
| Hızlı Kararlar | gemini-3.1-flash-lite-preview | Yüksek kota, milisaniye kararlar |
| Araştırma | Kimi K2.6 via OpenRouter | Derin web tarama, düşük hallüsinasyon |
| Kalıcı Hafıza | ChromaDB + Gemini Embedding v2 | Session bağımsız, semantik arama |
| Wake Word | Vosk (Türkçe) | Offline, 7/24, sıfır gecikme |
| TTS | Edge-TTS (şimdilik) | Türkçe, hızlı |
| Backend | FastAPI + WebSocket | Tüm state ve event yönetimi burada |
| Frontend | Electron + React + TypeScript | Cross-platform, sistem tray |
| Ses Tanıma | Silero VAD + Faster-Whisper | Üretim kalitesi VAD, hızlı STT |
| Müzik | Spotify Web API (spotipy) | Resmi API, kararlı, playlist desteği |
| E-posta | Gmail API (OAuth 2.0) | Güvenli, multi-account |
| Tarayıcı | Playwright MCP | Başsız + görünür mod, kalıcı profil |

---

## Proje Yapısı

```
JARVAN/
├── backend/
│   ├── main.py                     # FastAPI sunucusu + WebSocket + Pipeline
│   ├── config.py                   # Ortam değişkenleri, parametreler
│   │
│   ├── ai/
│   │   ├── live_session.py         # Gemini Live orchestrator (~491 satır)
│   │   ├── memory_core.py          # ChromaDB RAG hafızası
│   │   ├── memory_manager.py       # Yapısal hafıza (memory.json)
│   │   ├── briefing_agent.py       # Sabah brifingi (Tavily + Gemini)
│   │   ├── insight_agent.py        # Konuşmadan otonom öğrenme
│   │   ├── wake_word.py            # Vosk yerel wake word
│   │   └── obsidian_manager.py     # Obsidian vault entegrasyonu
│   │
│   ├── orchestration/
│   │   ├── tool_registry.py        # Tüm tool tanımlamaları + system hint'ler
│   │   └── tool_executor.py        # Tool handler mantığı + ExecutorContext
│   │
│   ├── workers/
│   │   └── gemini_cli_worker.py    # Async arka plan görev yöneticisi
│   │
│   ├── tools/                      # 12 araç implementasyonu
│   │   ├── spotify.py              # Spotify Web API (spotipy)
│   │   ├── mail.py                 # Gmail API (gönder, oku, ara)
│   │   ├── app_control.py          # Uygulama aç/kapat
│   │   ├── computer_use.py         # Ekran görüntüsü + vision otomasyon
│   │   ├── developer.py            # Klasör oluştur, rapor kaydet
│   │   ├── weather.py              # Hava durumu
│   │   ├── browser.py              # URL aç
│   │   ├── obsidian.py             # Vault CRUD
│   │   ├── whatsapp.py             # WhatsApp mesajlaşma
│   │   ├── contacts.py             # Kişi yönetimi
│   │   └── calculator.py           # Matematik ifade değerlendirici
│   │
│   ├── mcp/
│   │   └── spotify_server.py       # Spotify FastMCP sunucusu
│   │
│   ├── modes/
│   │   ├── detector.py             # Aktif pencere tespiti (Unreal, Unity, VSCode)
│   │   └── prompts.py              # Bağlam bazlı sistem prompt'ları
│   │
│   ├── audio/
│   │   ├── vad_gate.py             # Silero VAD konuşma tespiti
│   │   └── transcriber.py          # Faster-Whisper STT
│   │
│   ├── screen/
│   │   └── capture.py              # MSS ekran görüntüsü + vision kodlama
│   │
│   ├── tts/
│   │   └── speaker.py              # Edge-TTS Türkçe sentezi
│   │
│   └── data/
│       ├── memory.json             # Yapısal kullanıcı profili
│       ├── briefing_state.json     # Brifing önbelleği + tekrar engelleme
│       └── chroma/                 # ChromaDB kalıcı vektör deposu
│
└── frontend/
    ├── electron/
    │   ├── main.ts                 # Electron yaşam döngüsü
    │   └── preload.ts              # IPC köprüsü
    └── src/
        ├── App.tsx
        ├── components/
        │   ├── LogPanel.tsx        # Gerçek zamanlı log ekranı
        │   ├── Waveform.tsx        # Ses seviyesi görselleştirme
        │   ├── StatusBar.tsx       # Bağlantı durumu
        │   └── …
        └── hooks/
            └── useBackend.ts       # WebSocket bağlantı hook'u
```

---

## Temel Özellikler

### Kalıcı Hafıza (İki Katmanlı)

**Yapısal (memory.json):** Müzik tercihleri, çalışma saatleri, aktif projeler gibi elle düzenlenebilir profil bilgisi.

**Davranışsal (ChromaDB RAG):** Her konuşma sonunda `InsightAgent` çalışır, öğrenilecek bilgileri ayıklar ve vektör veritabanına yazar. Bir sonraki oturumda bu bilgiler semantik olarak sorgulanıp inject edilir.

```
Örnek öğrenilen içgörüler:
"Burak odaklanma için Radiohead ve NieR OST dinler"
"Burak sabah 9-11 arası verimsiz çalışır, gece 22 sonrası peak saatleri"
"Burak şekersiz americano içer"
```

### Otonom Öğrenme (InsightAgent)

Oturum bitişinde arka planda sessizce çalışır:
1. Konuşma dökümünü `gemini-3.1-flash-lite-preview` ile analiz eder
2. Kaydedilmeye değer kalıcı bilgileri filtreler (geçici bilgileri atar)
3. Tekrar engelleme kontrolü yapar (semantik benzerlik eşiği: 0.85)
4. Yeni içgörüleri ChromaDB'ye yazar

### Sabah Brifingi

Oturum açıldığında arka planda başlatılır, "Uyan Jarvan" dendiğinde hazır olur:
- Tavily API ile yapay zeka, oyun ve yazılım geliştirme haberleri çeker
- Gemini ile önem sırasına göre filtreler
- Görülen haberler MD5 hash ile takip edilir (tekrar gösterilmez)
- Minimum 4 saat bekleme süresi

### Bağlam Farkındalığı (Mod Sistemi)

Aktif pencereye göre sistem promptu otomatik değişir:

| Pencere | Mod | Davranış |
|---------|-----|---------|
| Unreal Engine | `unreal` | Oyun tasarımı odaklı yanıtlar |
| Unity | `unity` | Unity workflow desteği |
| VSCode / Cursor | `code` | Kod geliştirme modu |
| Diğer | `default` | Genel asistan modu |

### Gemini CLI Worker

Uzun süren ağır görevler (büyük kod yazma, refactor, analiz) ana ses oturumunu bloke etmez:

```
Kullanıcı: "Bu projedeki tüm Python dosyalarını analiz et ve mimari rapor yaz"
    │
    ▼
start_gemini_task(prompt, heavy=True) → job_id
    │
    ▼
Arka planda Gemini CLI subprocess başlar (gemini-3.1-pro-preview)
    │
    ▼ (iş bittiğinde)
Notification queue → LiveSession → "Analiz tamamlandı, sonucu okuyayım mı?"
```

---

## Kurulum

### Gereksinimler

- Python 3.11+
- Node.js 18+
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) (`brew install gemini-cli`)
- Spotify Premium hesabı (Web API için)
- Gmail hesabı + Google Cloud projesi (OAuth için)
- Tavily API anahtarı (brifing için)

### Backend Kurulumu

```bash
# 1. Depoyu klonla
git clone https://github.com/kullanici/jarvan.git
cd jarvan

# 2. Sanal ortam oluştur
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r backend/requirements.txt

# 4. Ortam değişkenlerini ayarla
cp backend/.env.example backend/.env
# .env dosyasını düzenle (API anahtarları)
```

### `.env` Dosyası

```env
GEMINI_API_KEY=...
TAVILY_API_KEY=...
OPENROUTER_API_KEY=...       # Kimi K2.6 için (isteğe bağlı)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
MY_WHATSAPP=+905xxxxxxxxx    # WhatsApp mesajları için
```

### Gmail OAuth Kurulumu

1. Google Cloud Console'da proje oluştur
2. Gmail API'yi etkinleştir
3. OAuth 2.0 kimlik bilgileri indir → `backend/credentials.json`
4. İlk çalıştırmada tarayıcı açılır, izin ver
5. Token `backend/data/` altına kaydedilir

Detaylar için: [backend/GMAIL_SETUP.md](backend/GMAIL_SETUP.md)

### Spotify Kurulumu

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)'a giriş yap
2. Uygulama oluştur, Redirect URI: `http://127.0.0.1:8888/callback`
3. Client ID ve Secret'ı `.env`'e yaz
4. İlk çalıştırmada tarayıcı açılır, giriş yap

### Wake Word Modeli (Türkçe)

```bash
mkdir -p backend/models
cd backend/models
wget https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip
unzip vosk-model-small-tr-0.3.zip
mv vosk-model-small-tr-0.3 vosk-tr
```

### Frontend Kurulumu

```bash
cd frontend
npm install
```

---

## Çalıştırma

### Backend

```bash
# Proje kök dizininden çalıştır
.venv/bin/python backend/main.py
# veya
source .venv/bin/activate && python backend/main.py
```

Sunucu `http://127.0.0.1:8765` adresinde başlar.

### Frontend

```bash
cd frontend

# Geliştirme modu
npm run dev

# Electron ile çalıştır
npm run start
```

### Sadece Backend Test

```bash
python backend/test_pipeline.py
```

---

## Kullanım

### Wake Word Komutları

| Komut | Etki |
|-------|------|
| "Uyan Jarvan" | Asistanı uyandırır, dinlemeye başlar |
| "Uyu" | Uyku moduna geçer |
| "Kapat kendini" | Oturumu sonlandırır |

### Örnek Kullanım Senaryoları

```
"Uyan Jarvan, Spotify'da odaklanma playlistimi çalar mısın?"
"Hava durumu nasıl bugün?"
"Masaüstünde bir proje klasörü oluştur"
"Gmail'deki okunmamış maillere bak"
"Bu kodu incele ve iyileştirme öner" (ekranı görür)
```

### Gemini CLI Görevleri (Ağır İşler)

```
"Backend kodunu analiz et ve mimari rapor yaz"
"Tüm Python dosyalarındaki hataları bul ve düzelt"
```

Bu tür görevler arka planda çalışır, bittiğinde JARVAN bildirir.

---

## Mevcut Araçlar

| Araç | Komut Örneği |
|------|-------------|
| Spotify | "Radiohead çal", "müziği durdur", "sonraki şarkıya geç" |
| Gmail | "Maillerimi kontrol et", "Ahmet'e mail at" |
| Hava Durumu | "Ankara hava durumu" |
| Uygulama Kontrolü | "Spotify'ı aç", "Chrome'u kapat" |
| Ekran Analizi | "Ekranımda ne var?" (her zaman ekranı görür) |
| Dosya/Klasör | "Masaüstünde rapor klasörü oluştur" |
| WhatsApp | "Annem'e WhatsApp yaz, geç kalacağım de" |
| Hesap Makinesi | "385 * 47 kaç eder?" |
| Obsidian | "Not oluştur: proje fikirleri" |
| Tarayıcı | "GitHub aç" |

---

## Hafıza Sistemi — Nasıl Çalışır

```
Konuşma oluyor
      │
      ▼
Session bitti → InsightAgent arka planda tetiklenir
      │
      ▼
Gemini Flash Lite: "Bu konuşmada öğrenilecek kalıcı bilgi var mı?"
      │
      ├── Varsa → Deduplication kontrolü (semantik benzerlik ≥ 0.85)
      │              │
      │              ├── Yeni → ChromaDB'ye yaz
      │              └── Tekrar → Atla
      │
      └── Yoksa → Hiçbir şey yazma
      │
      ▼
Bir sonraki session başında:
memory_core.get_session_context() → Gemini'ye inject edilir
```

### Hafıza Türleri

- **Yapısal:** `data/memory.json` — müzik tercihleri, çalışma saatleri, profil
- **Davranışsal:** ChromaDB — konuşmalardan öğrenilen örüntüler
- **Brifing Durumu:** `data/briefing_state.json` — görülen haberler

---

## MCP Sunucuları

JARVAN araçlarını standart MCP interface'ine taşıma çalışması sürmektedir. Bu sayede hem Gemini Live hem Gemini CLI aynı araçları kullanabilir.

### Mevcut

| Sunucu | Durum | Açıklama |
|--------|-------|---------|
| Spotify MCP | ✅ Çalışıyor | `mcp/spotify_server.py` (FastMCP) |
| Playwright MCP | ✅ Çalışıyor | `@playwright/mcp` (npm) — tarayıcı otomasyonu |
| Tavily MCP | ✅ Çalışıyor | `tavily-mcp` (npm) — web araştırma |
| Filesystem MCP | ✅ Çalışıyor | Gemini CLI dosya erişimi |

### Planlanmış

| Sunucu | Öncelik |
|--------|---------|
| Gmail MCP | Yüksek |
| Memory MCP | Yüksek |
| Calendar MCP | Orta |
| Computer Use MCP | Orta |
| Obsidian MCP | Düşük |

---

## Geliştirme Yol Haritası

| Versiyon | Odak | Durum |
|----------|------|-------|
| v0.3 | Gemini Live + memory.json + Obsidian | ✅ Tamamlandı |
| v0.4 | ChromaDB RAG + InsightAgent | ✅ Tamamlandı |
| v0.5 | Gemini CLI Worker + Spotify API + Mail okuma + Tool Registry | ✅ Tamamlandı |
| v0.6 | MCP stabilizasyonu + Playwright + Brifing | ✅ Tamamlandı |
| v0.9 | Proaktif Motor (anomaly detection) | 🔄 Planlandı |
| v1.0 | Görev takibi + ambient awareness | 🔄 Uzun vade |

---

## Tasarım Kararları

**Neden Gemini?** Live API ~200ms gecikme, ses ve ekranı aynı anda alıyor, cömert ücretsiz limit.

**Neden yerel model yok?** Test edildi, istenen kalite seviyesine ulaşılamadı. Bu projenin doğru seçimi cloud-first.

**Neden MCP?** Tüm araçları standart interface'e çekince hem Gemini CLI hem Live hem başka agent kullanabiliyor.

**Neden ChromaDB?** Session bağımsız kalıcı hafıza. Uygulama kapanınca hafıza ölmüyor.

**Neden Vosk wake word?** Offline çalışıyor, 7/24 dinleyebiliyor, sıfır gecikme, ücretsiz.

---

## Lisans

Kişisel kullanım projesi. Lisans koşulları için iletişime geçin.
