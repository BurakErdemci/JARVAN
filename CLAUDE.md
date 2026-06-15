# CLAUDE.md — Jarvan Local Voice Layer

> Bu dosya yapılacak işin brief'idir. Amaç: Jarvan'ın sesli erişimini Gemini Live API'sinden tamamen kurtarıp **local** bir sesli döngüye taşımak. Beyin = Gemma 4 12B (Ollama), ağız+kulak = Voicebox, eller = mevcut CLI'lar (AGY / Codex / Claude Code, abonelikle, MCP üzerinden).

---

## Bağlam ve neden

- Şu an sesli erişim **Gemini 3.1 Flash Live** ile, **API key** üzerinden yapılıyor. API key kullanımı abonelik dışı/ayrı faturalandığı için bu tek başına maliyet sızıntısı.
- Çözüm: sesi tamamen local'e al. Gemma 4 12B duyabiliyor ama **konuşamıyor** (audio in → text out), o yüzden konuşma için ayrı bir local TTS şart → **Voicebox** (STT + TTS, Türkçe Chatterbox Multilingual ile, MCP + REST sunar).
- Gerçek iş yükü zaten abonelikle çalışan CLI'larda kalacak. Gemma yalnızca **santral/dispatcher + hafif cevap** rolünde; ağır reasoning ona yıkılmayacak.

## Kapsam (bu task = Phase 1 / MVP)

Çalışan bir **local sesli döngü** kur:

```
Mikrofon → STT (Voicebox) → Gemma 4 12B (beyin/dispatcher) → [direkt cevap | dispatch | local tool] → TTS (Voicebox, TR) → Hoparlör
```

Phase 1'de CLI'lara gerçek iş paslamak ZORUNLU değil — dispatch **kararı** üretilsin ve loglansın, executor seam'i net olsun. Gerçek CLI çalıştırma Phase 2.

## Mimari bileşenler

| Katman | Teknoloji | Not |
|---|---|---|
| Orkestratör | Python + FastAPI | Voicebox ile aynı stack; sonradan panel bunun event log'unu okuyacak |
| STT (kulak) | Voicebox `POST /transcribe` (Whisper Turbo) | base: `http://127.0.0.1:17493` |
| Beyin | Gemma 4 12B via **Ollama** | `POST /api/chat`, tools (function-calling) açık; base: `http://localhost:11434` |
| TTS (ağız) | Voicebox `POST /speak` | Türkçe ses profili (Chatterbox Multilingual) |
| Executor | pluggable interface | Phase 1'de stub; Phase 2'de CLI |
| State | SQLite | event log: turn/stt/gemma/dispatch/tts |

## Yapılacaklar (build adımları)

1. **Repo iskeleti**: `uv` (ya da venv) + FastAPI. Yapı:
   ```
   jarvan_voice/
   ├── config.py          # .env'den okunur, hardcode secret YOK
   ├── clients/
   │   ├── voicebox.py    # transcribe(), speak(), health()
   │   └── gemma.py       # chat_with_tools(), streaming
   ├── dispatcher.py      # Gemma'nın karar mantığı + tool şeması
   ├── executors/
   │   ├── base.py        # abstract Executor.run(task) -> Result
   │   ├── local_tool.py  # basit local aksiyonlar (MVP: echo/no-op)
   │   └── cli.py         # STUB (Phase 2'de gerçeklenecek)
   ├── voice_loop.py      # mic → stt → gemma → exec → tts
   ├── events.py          # SQLite event log + replay
   └── main.py            # FastAPI app + CLI entrypoint
   ```

2. **Config** (`.env`): `VOICEBOX_URL=http://127.0.0.1:17493`, `OLLAMA_URL=http://localhost:11434`, `GEMMA_MODEL=<ollama tag>`, `TR_VOICE_PROFILE=<profile id/ad>`, `PTT_HOTKEY=<tuş>`. **Not:** Gemma'nın Ollama tag'ini varsayma — `ollama list` ile doğrulat, config'e öyle yaz.

3. **Voicebox client**: ince wrapper. `transcribe(audio_bytes) -> str`, `speak(text, profile) -> ok`, `health() -> bool`. REST endpoint'leri Voicebox docs'tan: `/transcribe`, `/speak`, `/profiles`.

4. **Gemma client (Ollama)**: `chat(messages, tools, stream=True)`. Function-calling açık. Token streaming desteklenecek (latency için kritik).

5. **Dispatcher**:
   - Türkçe sistem promptu: Gemma'nın rolü = **santral memuru**. Kullanıcıyı karşılar, niyetini anlar, üç şeyden birini yapar: (a) basit/anlık soruyu kendi cevaplar, (b) işi bir CLI'ya paslar, (c) bir local tool çağırır.
   - **Tool şeması dar ve açık** olacak. En az: `answer_directly(text)`, `dispatch_to_cli(target: enum[claude_code|codex|agy], task: str, reason: str)`, `run_local_tool(name, args)`.
   - Çıktı yapılandırılmış (tool call) olarak parse edilecek; serbest metinle iş paslanmayacak.
   - Açık-uçlu ağır muhakeme Gemma'ya verilmeyecek; karar + kısa cevapla sınırlı.

6. **Executor seam**: `base.Executor.run(task) -> Result`. `local_tool` minimal çalışsın. `cli` STUB olsun ama imzası net: hangi CLI, hangi task, dönen sonuç. (Phase 2 buradan devam edecek.)

7. **Voice loop**: push-to-talk hotkey ile kayıt → `transcribe` → `dispatcher` → executor (gerekiyorsa) → cevabı **cümle cümle stream ederek** `speak`. Gemma token üretirken cümle bittikçe TTS'e besle (tüm cevabı bekleme).

8. **Event log (SQLite)**: her turda `turn.start`, `stt.done`, `gemma.decision`, `dispatch.start/done`, `tts.done` yaz. Replay/debug + ileride panel bunu okuyacak.

9. **README**: kurulum (Voicebox + Ollama + gemma 4 12b çalışıyor olmalı), `.env` örneği, çalıştırma komutu, health check.

## Kısıtlar (non-negotiable)

- **Hiçbir yerde Gemini Live yok, Google API key yok.** Ses %100 local (Voicebox).
- I/O dili **Türkçe**. TTS Türkçe ses profili kullanacak.
- Secret hardcode YOK → hepsi `.env`.
- Gemma'nın işi dispatch + hafif cevap; ağır reasoning'i CLI'lara bırak.
- TTS cümle cümle stream → latency düşür. Ollama'da varsa Gemma 4'ün speculative decoding (MTP) avantajını kullan.
- Type hints + temiz modüler yapı. Her client/executor bağımsız test edilebilir olsun.

## Kabul kriterleri (MVP biterse)

- [ ] Servis tek komutla ayağa kalkıyor; health check Voicebox + Ollama erişimini doğruluyor.
- [ ] Uçtan uca: Türkçe konuş → Türkçe sesli cevap geliyor (Gemma + Voicebox, sıfır Google).
- [ ] Bir "işi paslama" cümlesinde Gemma `dispatch_to_cli` kararı üretiyor ve event log'a hedef + structured task yazılıyor (executor stub olsa da).
- [ ] Event log sorgulanabilir (replay için).
- [ ] Kod modüler; Voicebox/Gemma client'ları ve executor'lar ayrı ayrı test edilebilir.

## Fazlar

- **Phase 1 (bu task):** sesli döngü + Gemma dispatcher + stub executor + event log.
- **Phase 2:** gerçek CLI executor + MCP tool'ları + Tapo/ev otomasyonu + offline fallback (ağ/limit yokken Gemma temel işi yürütür).
- **Phase 3:** event log üstünde okuma-amaçlı panel/dashboard (task akışı + anlık durum).

## Burak'ın netleştirmesi gereken açık sorular (VARSAYMA, sor)

1. **CLI dispatch mekanizması (Phase 2):** Gemma bir CLI'ya programatik nasıl paslayacak? Seçenekler: headless `claude -p` (15 Haz'dan beri ayrı kredi havuzu — istemiyorsun), remote routines (API/event ile tetik), ya da yarı-otomatik (Gemma task'ı hazırlar, sen onaylayıp CLI session'ına verirsin). MVP bunu stub bırakıyor; Phase 2'de karar gerekiyor.
2. **STT kaynağı:** Voicebox Whisper mı yoksa Gemma'nın native audio'su mu? MVP basitlik için Voicebox `/transcribe` kullanıyor (tek nokta). Gemma native audio'ya geçmek istersen ayrı seam.
3. **Türkçe TTS kalitesi:** Chatterbox Multilingual Türkçe'yi listeliyor ama prozodi kalitesi garanti değil — kurulumda bir profil seç ve kulağınla doğrula; kötüyse alternatif motor/ses dene.
