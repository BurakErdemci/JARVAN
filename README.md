# JARVAN — Personal AI Digital Twin

> *"JARVAN is not just software; it is your sword, shield, and faithful companion in the digital world."*

JARVAN is a personal AI assistant inspired by Tony Stark's JARVIS. Not a chatbot — a **Digital Twin** that knows you, sees your screen, hears your voice, controls your computer, and continuously learns.

[🇹🇷 Türkçe README](README.tr.md)

---

## What Is It?

A few things set JARVAN apart from other assistants:

- **Voice + Vision**: Processes microphone audio and your screen simultaneously in real time
- **Persistent Memory**: Never resets between sessions — learns your preferences, habits, and routines
- **Proactive Behavior**: Doesn't wait for commands; notices what's happening and speaks first
- **Tool Integration**: Spotify, Gmail, weather, app control, file management, and more
- **Continuous Learning**: Extracts insights from every conversation and writes them to a vector database

---

## Architecture

```
User (voice + screen)
         │
         ▼
    Vosk Wake Word          ← "Uyan Jarvan" → wake up
         │
         ▼
  FastAPI Backend           ← persistent brain, all state lives here
    ├── memory.json         ← structured memory (preferences, routines)
    └── ChromaDB            ← behavioral RAG memory
         │
         ▼
   Gemini Live API          ← ~200ms voice latency, screen + audio simultaneously
    ├── gemini-3.1-flash-live-preview  (orchestrator)
    └── tool_calls → ToolExecutor
         │
    ┌────┼────┬────────────────┐
    ▼    ▼    ▼                ▼
Spotify Gmail Weather  …  Gemini CLI Worker
                           └── gemini-3.1-pro (heavy tasks)
```

**Critical rule:** Memory lives in the FastAPI backend. When a Gemini Live session ends, memory survives. Every new session injects ChromaDB + memory.json context.

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Voice Dialogue | Gemini Live (gemini-3.1-flash-live) | ~200ms latency, audio + screen simultaneously |
| Heavy Tasks | Gemini CLI (gemini-3.1-pro-preview) | 2M+ context, code writing, large refactors |
| Fast Decisions | gemini-3.1-flash-lite-preview | High quota, millisecond-level decisions |
| Research | Kimi K2.6 via OpenRouter | Deep web search, low hallucination |
| Persistent Memory | ChromaDB + Gemini Embedding v2 | Session-independent, semantic search |
| Wake Word | Vosk (Turkish) | Offline, 24/7, zero latency |
| TTS | Edge-TTS (for now) | Turkish, fast |
| Backend | FastAPI + WebSocket | All state and event management |
| Frontend | Electron + React + TypeScript | Cross-platform, system tray |
| Speech Processing | Silero VAD + Faster-Whisper | Production-grade VAD, fast STT |
| Music | Spotify Web API (spotipy) | Official API, stable, playlist support |
| Email | Gmail API (OAuth 2.0) | Secure, multi-account |
| Browser | Playwright MCP | Headless + visible mode, persistent profile |

---

## Project Structure

```
JARVAN/
├── backend/
│   ├── main.py                     # FastAPI server + WebSocket + Pipeline
│   ├── config.py                   # Environment variables, parameters
│   │
│   ├── ai/
│   │   ├── live_session.py         # Gemini Live orchestrator (~491 lines)
│   │   ├── memory_core.py          # ChromaDB RAG memory
│   │   ├── memory_manager.py       # Structural memory (memory.json)
│   │   ├── briefing_agent.py       # Morning briefing (Tavily + Gemini)
│   │   ├── insight_agent.py        # Autonomous learning from conversations
│   │   ├── wake_word.py            # Vosk local wake word
│   │   └── obsidian_manager.py     # Obsidian vault integration
│   │
│   ├── orchestration/
│   │   ├── tool_registry.py        # All tool declarations + system hints
│   │   └── tool_executor.py        # Tool handler logic + ExecutorContext
│   │
│   ├── workers/
│   │   └── gemini_cli_worker.py    # Async background task manager
│   │
│   ├── tools/                      # 12 tool implementations
│   │   ├── spotify.py              # Spotify Web API (spotipy)
│   │   ├── mail.py                 # Gmail API (send, read, search)
│   │   ├── app_control.py          # Open/close applications
│   │   ├── computer_use.py         # Screenshot + vision automation
│   │   ├── developer.py            # Create folders, save reports
│   │   ├── weather.py              # Weather lookup
│   │   ├── browser.py              # Open URLs
│   │   ├── obsidian.py             # Vault CRUD
│   │   ├── whatsapp.py             # WhatsApp messaging
│   │   ├── contacts.py             # Contact management
│   │   └── calculator.py           # Math expression evaluator
│   │
│   ├── mcp/
│   │   └── spotify_server.py       # Spotify FastMCP server
│   │
│   ├── modes/
│   │   ├── detector.py             # Active window detection (Unreal, Unity, VSCode)
│   │   └── prompts.py              # Context-aware system prompts
│   │
│   ├── audio/
│   │   ├── vad_gate.py             # Silero VAD speech detection
│   │   └── transcriber.py          # Faster-Whisper STT
│   │
│   ├── screen/
│   │   └── capture.py              # MSS screenshotting + vision encoding
│   │
│   ├── tts/
│   │   └── speaker.py              # Edge-TTS Turkish synthesis
│   │
│   └── data/
│       ├── memory.json             # Structured user profile
│       ├── briefing_state.json     # Briefing cache + deduplication state
│       └── chroma/                 # ChromaDB persistent vector store
│
└── frontend/
    ├── electron/
    │   ├── main.ts                 # Electron app lifecycle
    │   └── preload.ts              # IPC bridge
    └── src/
        ├── App.tsx
        ├── components/
        │   ├── LogPanel.tsx        # Real-time log display
        │   ├── Waveform.tsx        # Audio level visualization
        │   ├── StatusBar.tsx       # Connection status
        │   └── …
        └── hooks/
            └── useBackend.ts       # WebSocket connection hook
```

---

## Core Features

### Two-Layer Persistent Memory

**Structural (memory.json):** Manually editable profile — music preferences, work hours, active projects.

**Behavioral (ChromaDB RAG):** After every conversation, `InsightAgent` runs in the background, extracts learnings, and writes them to the vector database. On the next session, these memories are semantically queried and injected into context.

```
Example learned insights:
"Burak listens to Radiohead and NieR OST when focusing"
"Burak is unproductive between 9–11 AM, peaks after 10 PM"
"Burak drinks his americano without sugar"
```

### Autonomous Learning (InsightAgent)

Runs silently in the background after each session ends:
1. Analyzes the conversation transcript with `gemini-3.1-flash-lite-preview`
2. Filters for genuinely persistent learnings (discards transient info)
3. Deduplication check (semantic similarity threshold: 0.85)
4. Writes new insights to ChromaDB

### Morning Briefing

Starts prefetching in the background when a session opens — ready instantly when you say "Uyan Jarvan":
- Fetches AI, gaming, and software development news via Tavily API
- Filters and ranks by relevance with Gemini
- Tracks seen articles by MD5 hash (no repeats)
- 4-hour minimum cooldown between briefings

### Context Awareness (Mode System)

System prompt automatically adapts based on the active window:

| Window | Mode | Behavior |
|--------|------|---------|
| Unreal Engine | `unreal` | Game design focused responses |
| Unity | `unity` | Unity workflow support |
| VSCode / Cursor | `code` | Code development mode |
| Other | `default` | General assistant mode |

### Gemini CLI Worker

Long-running heavy tasks (large code generation, refactors, analysis) don't block the main voice session:

```
User: "Analyze all Python files in this project and write an architecture report"
    │
    ▼
start_gemini_task(prompt, heavy=True) → job_id
    │
    ▼
Gemini CLI subprocess starts in background (gemini-3.1-pro-preview)
    │
    ▼ (when complete)
Notification queue → LiveSession → "Analysis complete, shall I read the results?"
```

---

## Setup

### Requirements

- Python 3.11+
- Node.js 18+
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) (`brew install gemini-cli`)
- Spotify Premium account (for Web API)
- Gmail account + Google Cloud project (for OAuth)
- Tavily API key (for briefing)

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/jarvan.git
cd jarvan

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Set up environment variables
cp backend/.env.example backend/.env
# Edit .env with your API keys
```

### `.env` File

```env
GEMINI_API_KEY=...
TAVILY_API_KEY=...
OPENROUTER_API_KEY=...       # For Kimi K2.6 (optional)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
MY_WHATSAPP=+1234567890      # For WhatsApp messaging
```

### Gmail OAuth Setup

1. Create a project in Google Cloud Console
2. Enable the Gmail API
3. Download OAuth 2.0 credentials → `backend/credentials.json`
4. On first run, a browser window opens — authorize it
5. Token is saved to `backend/data/`

Full guide: [backend/GMAIL_SETUP.md](backend/GMAIL_SETUP.md)

### Spotify Setup

1. Log in to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app, set Redirect URI: `http://127.0.0.1:8888/callback`
3. Add Client ID and Secret to `.env`
4. On first run, a browser window opens — log in

### Wake Word Model (Turkish)

```bash
mkdir -p backend/models
cd backend/models
wget https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip
unzip vosk-model-small-tr-0.3.zip
mv vosk-model-small-tr-0.3 vosk-tr
```

### Frontend Setup

```bash
cd frontend
npm install
```

---

## Running

### Backend

```bash
# Run from the project root directory
.venv/bin/python backend/main.py
# or
source .venv/bin/activate && python backend/main.py
```

Server starts at `http://127.0.0.1:8765`.

### Frontend

```bash
cd frontend

# Development mode
npm run dev

# Run with Electron
npm run start
```

### Backend-only Test

```bash
python backend/test_pipeline.py
```

---

## Usage

### Wake Words

| Command | Effect |
|---------|--------|
| "Uyan Jarvan" | Wakes the assistant, starts listening |
| "Uyu" | Enters sleep mode |
| "Kapat kendini" | Ends the session |

### Example Scenarios

```
"Uyan Jarvan, play my focus playlist on Spotify"
"What's the weather today?"
"Create a project folder on the desktop"
"Check my unread Gmail"
"Review this code and suggest improvements"  (sees your screen)
```

### Gemini CLI Tasks (Heavy Work)

```
"Analyze the backend code and write an architecture report"
"Find and fix all errors across the Python files"
```

These tasks run in the background and JARVAN notifies you when done.

---

## Available Tools

| Tool | Example Command |
|------|----------------|
| Spotify | "Play Radiohead", "pause music", "next track" |
| Gmail | "Check my mail", "Send an email to John" |
| Weather | "Weather in London" |
| App Control | "Open Spotify", "Close Chrome" |
| Screen Analysis | "What's on my screen?" (always sees screen) |
| File/Folder | "Create a reports folder on the desktop" |
| WhatsApp | "WhatsApp my mom, tell her I'll be late" |
| Calculator | "What is 385 times 47?" |
| Obsidian | "Create a note: project ideas" |
| Browser | "Open GitHub" |

---

## Memory System — How It Works

```
Conversation happens
      │
      ▼
Session ends → InsightAgent triggered in background
      │
      ▼
Gemini Flash Lite: "Is there anything permanently worth learning from this conversation?"
      │
      ├── Yes → Deduplication check (semantic similarity ≥ 0.85)
      │              │
      │              ├── New → Write to ChromaDB
      │              └── Duplicate → Skip
      │
      └── No → Write nothing
      │
      ▼
Next session start:
memory_core.get_session_context() → injected into Gemini
```

### Memory Types

- **Structural:** `data/memory.json` — music preferences, work hours, profile
- **Behavioral:** ChromaDB — patterns learned from conversations
- **Briefing State:** `data/briefing_state.json` — seen articles tracker

---

## MCP Servers

JARVAN is migrating its tools to the standard MCP interface so both Gemini Live and Gemini CLI can use the same tools.

### Current

| Server | Status | Description |
|--------|--------|-------------|
| Spotify MCP | ✅ Working | `mcp/spotify_server.py` (FastMCP) |
| Playwright MCP | ✅ Working | `@playwright/mcp` (npm) — browser automation |
| Tavily MCP | ✅ Working | `tavily-mcp` (npm) — web research |
| Filesystem MCP | ✅ Working | Gemini CLI file access |

### Planned

| Server | Priority |
|--------|----------|
| Gmail MCP | High |
| Memory MCP | High |
| Calendar MCP | Medium |
| Computer Use MCP | Medium |
| Obsidian MCP | Low |

---

## Roadmap

| Version | Focus | Status |
|---------|-------|--------|
| v0.3 | Gemini Live + memory.json + Obsidian | ✅ Done |
| v0.4 | ChromaDB RAG + InsightAgent | ✅ Done |
| v0.5 | Gemini CLI Worker + Spotify API + Mail + Tool Registry | ✅ Done |
| v0.6 | MCP stabilization + Playwright + Briefing | ✅ Done |
| v0.9 | Proactive Engine (anomaly detection) | 🔄 Planned |
| v1.0 | Task tracking + ambient awareness | 🔄 Long-term |

---

## Design Decisions

**Why Gemini?** Live API offers ~200ms latency, handles audio and screen input simultaneously, generous free tier.

**Why no local model?** Tested extensively — quality was insufficient for the digital twin experience required.

**Why MCP?** Standardizing all tools to MCP means both Gemini CLI and Gemini Live (and any future agent) can use them interchangeably.

**Why ChromaDB?** Session-independent persistent memory. The app can restart; memory doesn't.

**Why Vosk for wake word?** Runs fully offline, can listen 24/7, zero latency, free.

---

## License

[MIT](LICENSE) © 2026 Burak Emre Erdemci
