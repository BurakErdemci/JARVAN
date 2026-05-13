# JARVAN — Master Blueprint v2.0
# Sahibi: Burak Emre Erdemci
# Son güncelleme: Mayıs 2026

---

## 🧠 Felsefe

Jarvan bir chatbot değildir. Seni tanıyan, ekranını gören, sesini duyan, bilgisayarını kontrol eden ve sürekli öğrenen bir **Dijital İkiz**dir. Hedef: Tony Stark'ın JARVIS'i — reaktif değil, proaktif; komut beklemez, fark eder ve söyler.

**Temel kararlar:**
- **Neden Gemini?** Live API ~200ms gecikme, cömert ücretsiz limit, Google aboneliğiyle CLI bedava, multimodal lider.
- **Neden local model yok?** Test edildi, istenen kalite seviyesine ulaşılamadı. Cloud-first yapı bu projenin doğru seçimi.
- **Neden MCP?** Tüm araçları standart interface'e çekmek için. Bir tool FastMCP'ye yazılırsa hem Gemini CLI hem Live hem başka herhangi bir agent kullanabilir.
- **Neden Voicebox?** TTS + STT + ses klonlama + MCP server — hepsini tek local uygulamada çözüyor, veri dışarı çıkmıyor.

---

## 🏛️ Mimari (v2.0 — Gemini-Centric + MCP Hub)

```
┌─────────────────────────────────────────────────────┐
│                   KULLANICI                         │
│              (ses / ekran / Telegram)               │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              VOSK — Wake Word                       │
│         Offline, 7/24, "Uyan" algılama              │
└──────────────────────┬──────────────────────────────┘
                       │ uyanma sinyali
┌──────────────────────▼──────────────────────────────┐
│           FASTAPI BACKEND — Kalıcı Beyin            │
│                                                     │
│  memory.json ←→ ChromaDB (RAG + behavioral memory) │
│  Platform-aware config (Mac / Windows)              │
│  WebSocket /ws → Electron frontend                  │
└──────┬───────────────┬──────────────────────────────┘
       │               │ memory inject (her session)
       │    ┌──────────▼──────────────────────────┐
       │    │     GEMINI LIVE — Orchestrator       │
       │    │  gemini-3.1-flash-live-preview       │
       │    │  Ses (~200ms) + Ekran (1 FPS JPEG)   │
       │    │  tool_call → _handle_tool_calls()    │
       │    └──┬─────────┬──────────┬─────────────┘
       │       │         │          │
       │   ┌───▼──┐  ┌───▼───┐  ┌──▼──────────┐
       │   │Gemini│  │DeepS. │  │  Kimi K2.6  │
       │   │ CLI  │  │  V4   │  │(deep_resrch)│
       │   │(dev) │  │(fast) │  │via OpenRouter│
       │   └───┬──┘  └───┬───┘  └──┬──────────┘
       │       │          │         │
       └───────▼──────────▼─────────▼────────────────┐
                      MCP HUB (FastMCP)               │
         ┌──────────┬──────────┬──────────┬────────┐  │
         │Obsidian  │ Gmail    │ Browser  │Voicebox│  │
         │  MCP     │  MCP     │  MCP     │  MCP   │  │
         │(STDIO)   │(OAuth)   │(CDP+PW)  │/speak  │  │
         └──────────┴──────────┴──────────┴────────┘  │
                                                       │
         ┌──────────┬──────────┐                       │
         │Spotify   │ PC Use   │                       │
         │  MCP     │  MCP     │                       │
         │(pyauto)  │(Vision)  │                       │
         └──────────┴──────────┘                       │
```

**Kritik kural:** Hafıza FastAPI backend'de yaşar. Gemini CLI veya Live session bittiğinde hafıza ölmez. Her yeni session başında ChromaDB + memory.json backend'den inject edilir.

---

## 🤖 Model Routing — Hangi İş Hangi Model

| Görev | Model | Neden |
|-------|-------|-------|
| Sesli diyalog (orchestrator) | `gemini-3.1-flash-live` | ~200ms, En güncel LiveAPI, multimodal |
| Ekran analizi (vision) | `gemini-3.1-pro` | Multimodal lider, derin görsel zeka |
| Kod geliştirme / dosya yazma | Gemini CLI (`gemini-3.1-pro`) | 2M+ context, agentic, kodlama canavarı |
| Derin araştırma | Kimi K2.6 via OpenRouter | En derin web tarama ve reasoning |
| **Otonom İçgörü (Insight Agent)** | `gemini-3.1-flash-lite-preview` | **Hızlı, yüksek kota, otonom süzgeç** |
| Hızlı araç çağrıları | `gemini-3.1-flash-lite-preview` | Milisaniyelik karar verme |
| Hafıza embedding | `gemini-embedding-2` | Yeni nesil vektörleme, multimodal uyumlu |
| Mimari ve Stratejik Analiz | Claude Opus 4.6 | SWE-bench %74+, uzun analiz |
| Ses çıkışı (TTS) | Voicebox — Chatterbox Turbo | Local, Türkçe, ses klonlama |
| Ses girişi (STT) | Voicebox — Whisper Turbo | Local, hızlı, Türkçe |
| Wake word | Vosk (local, offline) | 7/24, sıfır gecikme, bedava |

**DeepSeek V4 nerede kullanılır:** Mail özetleme, basit tool kararları, sürekli arka planda dönen düşük öncelikli işler. Kimi K2.6 ile karıştırma — Kimi yalnızca `deep_research` için.

---

## 🛠️ MCP Sunucuları (FastMCP ile yazılır)

Her tool bir MCP server'a çevrilir. `~/.gemini/settings.json`'a eklenir, Gemini CLI otomatik keşfeder.

```python
# Örnek: Obsidian MCP
from fastmcp import FastMCP

mcp = FastMCP("obsidian")

@mcp.tool()
def obsidian_create(title: str, content: str, folder: str = "") -> str:
    """Obsidian vault'ta yeni not oluşturur"""
    ...

@mcp.tool()
def obsidian_search(query: str) -> list[dict]:
    """Vault'ta semantik arama yapar"""
    ...
```

### MCP Sunucu Listesi

| Sunucu | Transport | Araçlar |
|--------|-----------|---------|
| `obsidian-mcp` | STDIO | create, read, search, list, link |
| `gmail-mcp` | SSE (OAuth) | send, read, list, search |
| `browser-mcp` | STDIO (CDP) | navigate, click, type, extract, screenshot |
| `voicebox-mcp` | HTTP `/mcp` | speak, transcribe, list_profiles |
| `spotify-mcp` | STDIO | play, pause, search, playlist |
| `computer-mcp` | STDIO | screenshot, click, type, scroll |
| `memory-mcp` | STDIO | save_insight, query, forget |
| `calendar-mcp` | SSE (OAuth) | list_events, create_event, update |

### Gemini CLI settings.json şablonu

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "python",
      "args": ["/path/to/jarvan/backend/mcp/obsidian_server.py"],
      "trust": false
    },
    "voicebox": {
      "url": "http://127.0.0.1:17493/mcp",
      "headers": { "X-Voicebox-Client-Id": "jarvan" }
    },
    "gmail": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

---

## 🔊 Ses Katmanı (Voicebox Entegrasyonu)

Voicebox (`github.com/jamiepine/voicebox`) — local-first, MIT lisans, 23k star.

**Kurulum:**
```bash
# Windows MSI veya macOS DMG indir
# voicebox.sh/download
```

**Jarvan entegrasyonu:**
```python
# backend/tools/voice.py
import httpx

VOICEBOX_URL = "http://127.0.0.1:17493"

async def speak(text: str, profile: str = "jarvan") -> None:
    """Metni JARVAN sesiyle çalar"""
    async with httpx.AsyncClient() as client:
        await client.post(f"{VOICEBOX_URL}/speak", json={
            "text": text,
            "profile": profile
        })

async def transcribe(audio_path: str) -> str:
    """Ses dosyasını metne çevirir"""
    async with httpx.AsyncClient() as client:
        with open(audio_path, "rb") as f:
            r = await client.post(
                f"{VOICEBOX_URL}/transcribe",
                files={"audio": f},
                data={"model": "whisper-turbo"}
            )
        return r.json()["text"]
```

**Ses klonlama:** Voicebox'ta "jarvan" profili oluştur, 10-30 sn referans ses yükle. Chatterbox Turbo engine seç — `[laugh]` `[sigh]` `[hmm]` gibi tag'leri anlıyor, karakteri daha canlı yapıyor.

---

## 🧬 Hafıza Sistemi (Kalıcı Kişiselleştirme)

Bu Jarvan'ın gerçek JARVIS'e en çok yaklaştığı yer. İki katmanlı:

### Katman 1: memory.json (yapısal)
```json
{
  "user": {
    "name": "Burak",
    "music": {
      "mood_map": {
        "odaklanma": ["Radiohead", "NieR OST", "Persona OST"],
        "enerji": ["Gripin", "Manga", "Linkin Park"],
        "rahatlama": ["Teoman", "Pink Floyd"]
      }
    },
    "work_patterns": {
      "peak_hours": ["14:00-18:00", "22:00-02:00"],
      "low_energy": ["09:00-11:00"]
    },
    "active_projects": [],
    "preferences": {}
  }
}
```

### Katman 2: ChromaDB (behavioral RAG)
```python
# backend/ai/memory_core.py
import chromadb
from chromadb.utils import embedding_functions

class MemoryCore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/chroma")
        self.ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=GEMINI_API_KEY,
            model_name="models/text-embedding-004"
        )
        self.collection = self.client.get_or_create_collection(
            "jarvan_memory",
            embedding_function=self.ef
        )

    def save_insight(self, text: str, metadata: dict) -> None:
        """Konuşmadan insight üretip kaydet"""
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[f"insight_{datetime.now().timestamp()}"]
        )

    def query(self, context: str, n: int = 5) -> list[str]:
        """Bağlama göre ilgili hafızaları getir"""
        results = self.collection.query(
            query_texts=[context],
            n_results=n
        )
        return results["documents"][0]

    def build_session_context(self) -> str:
        """Her session başında inject edilecek hafıza özetini üret"""
        recent = self.query("genel kullanıcı profili ve alışkanlıklar", n=10)
        return "\n".join(recent)
```

### Insight Üretici Ajan
Her konuşma sonunda arka planda çalışır, behavioral pattern öğrenir:
```python
async def extract_insights(conversation: list[dict]) -> None:
    """Konuşmadan öğrenilecek şeyleri ChromaDB'ye yaz"""
    prompt = f"""
    Bu konuşmadan kullanıcı hakkında kalıcı öğrenilecek bir şey var mı?
    Varsa tek cümleyle yaz. Yoksa boş döndür.
    Konuşma: {conversation[-5:]}
    """
    insight = await gemini_flash.generate(prompt)
    if insight.strip():
        memory_core.save_insight(insight, {
            "timestamp": datetime.now().isoformat(),
            "type": "behavioral"
        })
```

---

## 👁️ Proaktif Davranış (Anomaly Detection)

Jarvan senden komut beklemez. Şu kurallarla proaktif davranır:

```python
# backend/ai/proactive.py

PROACTIVE_RULES = [
    {
        "id": "stuck_on_error",
        "condition": "ekranda aynı hata mesajı 10+ dakikadır görünüyor",
        "action": "Burak, {error}'da takılı kaldın. Yardım edeyim mi?",
        "cooldown_minutes": 15
    },
    {
        "id": "deadline_reminder", 
        "condition": "takvimde yakın deadline var ve proje dosyaları açık",
        "action": "Yarın deadline var, {project} ne durumda?",
        "cooldown_minutes": 120
    },
    {
        "id": "music_context",
        "condition": "çalışma başladı, müzik yok",
        "action": "Müzik açayım mı? Son çalıştığın proje için Radiohead vardı.",
        "cooldown_minutes": 60
    },
    {
        "id": "long_session",
        "condition": "3 saattir mola yok",
        "action": "3 saattir duraksız çalışıyorsun.",
        "cooldown_minutes": 180
    }
]

class ProactiveEngine:
    def __init__(self):
        self.last_triggered = {}  # rule_id -> timestamp

    async def check(self, screen_context: str, memory: dict) -> str | None:
        """Her dakika çağrılır, tetiklenecek kural varsa döndürür"""
        for rule in PROACTIVE_RULES:
            if self._is_on_cooldown(rule["id"]):
                continue
            triggered = await self._evaluate(rule["condition"], screen_context, memory)
            if triggered:
                self.last_triggered[rule["id"]] = datetime.now()
                return rule["action"]
        return None
```

---

## 🧬 Gemini CLI Entegrasyonu

CLI ana beyin değil — **güçlü bir dev aracı**. Hafıza FastAPI'de yaşar, CLI subprocess olarak spawn edilir.

```python
# backend/tools/developer.py
import asyncio
import json

async def gemini_cli_task(prompt: str, context_files: list[str] = []) -> str:
    """
    Gemini CLI'yi subprocess olarak çalıştır.
    1M context sayesinde tüm proje dosyalarını okuyabilir.
    """
    # Memory'den session context oluştur
    memory_ctx = memory_core.build_session_context()
    
    full_prompt = f"""
    Kullanıcı profili:
    {memory_ctx}
    
    Görev:
    {prompt}
    """
    
    cmd = ["gemini", "--model", "gemini-2.5-pro", "--yolo"]
    
    # Context dosyalarını @ syntax ile ekle
    for f in context_files:
        full_prompt += f"\n@{f}"
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await proc.communicate(full_prompt.encode())
    return stdout.decode()
```

**CLI ne zaman çağrılır:**
- `crazy_mode` / multi-agent dev pipeline
- Büyük refactor işleri (tüm codebase context gerektirir)
- Git commit + PR açma
- Yeni dosya/modül yaratma

**CLI ne zaman çağrılmaz:**
- Real-time ses diyaloğu (Gemini Live halleder)
- Hızlı araç çağrıları (DeepSeek V4)
- Araştırma (Kimi K2.6)

---

## 📁 Dosya Yapısı (Hedef v2.0)

```
jarvan/
├── CLAUDE.md                    # Bu dosya
├── backend/
│   ├── main.py                  # FastAPI + WebSocket
│   ├── config.py                # Platform-aware (Mac/Win)
│   ├── ai/
│   │   ├── live_session.py      # Gemini Live orchestrator
│   │   ├── memory_core.py       # ChromaDB RAG + memory.json
│   │   ├── proactive.py         # Anomaly detection + kurallar
│   │   ├── insight_agent.py     # Konuşmadan öğrenme
│   │   ├── wake_word.py         # Vosk
│   │   └── obsidian_manager.py  # Nöral ağ
│   ├── mcp/                     # FastMCP server'lar
│   │   ├── obsidian_server.py
│   │   ├── gmail_server.py
│   │   ├── browser_server.py
│   │   ├── spotify_server.py
│   │   ├── computer_server.py
│   │   └── memory_server.py
│   ├── tools/                   # Mevcut araçlar (wrapper)
│   │   ├── mail.py
│   │   ├── computer_use.py
│   │   ├── developer.py         # Gemini CLI subprocess
│   │   ├── voice.py             # Voicebox HTTP client
│   │   └── obsidian.py
│   └── data/
│       ├── memory.json
│       └── chroma/              # ChromaDB persistent
├── frontend/                    # Electron + React
└── .gemini/
    └── settings.json            # MCP server config
```

---

## ✅ Kesinlikle Olması Gereken Özellikler

### 1. Kalıcı Kişilik Hafızası (ChromaDB RAG)
**Sorun:** Şu an her session sıfırlanıyor. "Burak sabahları verimsiz çalışır" gibi pattern'ler öğrenilemiyor.
**Çözüm:** Her konuşma sonunda insight_agent çalışır, ChromaDB'ye yazar. Session başında inject edilir.
**Öncelik:** KRİTİK — bu olmadan gerçek JARVIS deneyimi imkansız.

### 2. Proaktif Davranış (Anomaly Detection)
**Sorun:** Jarvan reaktif — sen söylemedikçe konuşmuyor.
**Çözüm:** ProactiveEngine her dakika screen context + memory'yi değerlendiriyor. Tetiklenirse konuşuyor.
**Öncelik:** YÜKSEK — JARVIS'i JARVIS yapan şey bu.

### 3. Voicebox Entegrasyonu
**Sorun:** TTS, STT, ses klonlama ayrı ayrı yönetiliyor.
**Çözüm:** Voicebox local çalışıyor, REST API + MCP server ship ediyor. Hasan Usta sesi için ses klonu oluştur, Chatterbox Turbo ile `[laugh]` tag'leri kullan.
**Öncelik:** YÜKSEK — karakter tutarlılığı için.

### 4. Tüm Araçları MCP'ye Taşımak
**Sorun:** Her araç farklı interface, sadece Gemini Live kullanabiliyor.
**Çözüm:** FastMCP ile her tool MCP server olur. Gemini CLI de, Live da, başka herhangi bir agent da kullanabilir.
**Öncelik:** ORTA — uzun vadeli esneklik için kritik.

### 5. Ambient Awareness (Takvim + Dosya Sistemi)
**Sorun:** Jarvan ses ve ekranı biliyor ama takvim, açık dosyalar, sistem durumu bilmiyor.
**Çözüm:** Calendar MCP, filesystem watcher, aktif uygulama listesi → memory'ye beslenir.
**Öncelik:** ORTA — proaktif davranışı güçlendirir.

### 6. Görev Takibi ve Süreklilik
**Sorun:** "Bu task 2 gündür bekliyor" diyemiyor, yarım kalan işleri bilmiyor.
**Çözüm:** Obsidian'daki TODO notları + memory.json'daki aktif proje listesi → periyodik kontrol.
**Öncelik:** ORTA.

### 7. Gemini CLI Dev Pipeline
**Sorun:** crazy_mode hâlâ eski multi-agent loop, 1M context kullanmıyor.
**Çözüm:** CLI subprocess entegrasyonu — büyük refactor ve yeni modül işlerini CLI'ye devret.
**Öncelik:** DÜŞÜK — sadece dev workflow'u etkiler.

---

## 🗺️ Versiyon Yol Haritası

| Versiyon | Odak | Durum |
|----------|------|-------|
| v0.3 | Gemini Live + memory.json + Obsidian | ✅ Tamamlandı |
| v0.4 | ChromaDB RAG + insight_agent | 🔄 Sıradaki |
| v0.5 | Voicebox entegrasyonu + ses karakteri | 🔄 Planlandı |
| v0.6 | ProactiveEngine + anomaly detection | 🔄 Planlandı |
| v0.7 | Tüm araçlar FastMCP'ye taşındı | 🔄 Planlandı |
| v0.8 | Gemini CLI subprocess + Calendar MCP | 🔄 Planlandı |
| v1.0 | Görev takibi + ambient awareness | 🔄 Uzun vade |

---

## 🛡️ Teknik Kararlar ve Gerekçeler

| Karar | Gerekçe |
|-------|---------|
| Gemini Live orchestrator | ~200ms gecikme, ses + ekran aynı anda |
| Local model yok | Test edildi, kalite yetersiz |
| DeepSeek V4 hızlı araçlar için | $0.28/M token, Gemini limit tasarrufu |
| Kimi K2.6 sadece deep_research | 300 alt-ajan, hallucination düşük, nadir çağrılır |
| Voicebox TTS/STT | Local, MIT, MCP built-in, Türkçe, ses klonlama |
| FastMCP Python | `@mcp.tool()` decorator ile dakikada server |
| ChromaDB persistent | Hafıza session'a bağlı değil, kalıcı |
| Syncthing Mac/Win sync | Bulut gerektirmiyor, P2P, ücretsiz |
| FastAPI backend | Tüm hafıza ve state burada yaşar |

---

*"Jarvan sadece bir yazılım değildir; o, senin dijital dünyadaki kılıcın, kalkanın ve sadık yoldaşındır."* ⚔️🛡️🤖