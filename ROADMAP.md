# JARVAN Roadmap

Bu dosya `CLAUDE.md` vizyonunun uygulanabilir geliştirme sırasıdır. Ana kural:
once stable core, sonra worker/MCP/proaktif katmanlar.

## Current Priority: v0.4 Stable Core

Hedef: Jarvan her acildiginda guvenilir sekilde konussun, uyusun/uyansin,
hafizayi inject etsin ve temel tool'lari calistirsin.

- `main.py -> Pipeline -> LiveSession` tek resmi runtime olsun.
- Eski VAD/router hattı legacy kalsin.
- `memory.json` yapisal hafiza olarak kalsin.
- ChromaDB davranissal hafiza olarak kalsin.
- ChromaDB veya embedding hatasi Live oturumunu dusurmesin.
- Insight agent sadece uykuya gecerken arka planda calissin.
- Live tool listesi kucuk ve stabil kalsin.

Done criteria:

- Backend aciliyor.
- Frontend backend'e baglaniyor.
- Start/stop calisiyor.
- Wake word sonrasi Live cevap veriyor.
- Sleep mode sonrasi transcript insight agent'a gidiyor.
- Hafiza hatasi olsa bile sesli oturum kapanmiyor.

## v0.5 Tool Registry

Hedef: `live_session.py` icindeki tool karmasasini azaltmak.

- `backend/orchestration/tool_registry.py` olustur.
- Function declaration listesini `live_session.py` disina cikar.
- Tool handler'lari `backend/orchestration/tool_executor.py` icine tasi.
- LiveSession sadece ses, session, receive loop ve prompt assembly yonetsin.
- Mevcut manuel tool'lar once korunarak registry'ye alinsin.

Done criteria:

- LiveSession icindeki tool declaration/handler kodu belirgin sekilde azalir.
- Tum mevcut stabil tool'lar ayni sekilde calisir.
- Yeni tool eklemek tek dosyada mumkun olur.

## v0.6 Gemini CLI Worker

Hedef: Gemini CLI'yi ana beyin degil, arka plandaki muhendis yapmak.

- `backend/workers/gemini_cli_worker.py` olustur.
- Async job modeli ekle: `job_id`, `status`, `result`, `error`.
- Worker'a compact memory context packet ver.
- Live'a sadece ust seviye worker tool'u ver:
  - `start_worker_task(task)`
  - `get_worker_result(job_id)`

Done criteria:

- Kod/analiz gibi uzun isler Live oturumunu bloklamaz.
- CLI sonucu backend'e kaydedilir.
- Jarvan sonucu kendi personasiyla ozetler.

## v0.7 MCP Worker Layer

Hedef: MCP'yi Live'in dogrudan tool listesi yapmak yerine worker katmaninin
arac seti yapmak.

- `ENABLE_MCP_HUB` feature flag altinda calissin.
- Once tek MCP server ile basla: filesystem veya Obsidian.
- Sonra browser, Gmail, Spotify ekle.
- Live MCP tool listesini dogrudan gormesin.
- MCP hatalari Live session restart'a sebep olmasin.

Done criteria:

- MCP server baglanti hatasi Jarvan'i dusurmez.
- Worker MCP tool cagirabilir.
- Live sadece sonucu alir ve kullaniciya anlatir.

## v0.8 Voicebox Layer

Hedef: TTS/STT/ses karakterini ayri bir ses katmani olarak stabilize etmek.

- `backend/tools/voice.py` Voicebox client olarak kalsin.
- Voicebox health check ekle.
- Profil listesi ve varsayilan `jarvan` profili kontrol edilsin.
- Gemini Live native audio ile Voicebox'un rol ayrimi netlensin.

Done criteria:

- Voicebox yoksa sistem net hata verir, Live core bozulmaz.
- Voicebox varsa secili profil ile konusma testi gecilir.

## v0.9 Proactive Engine

Hedef: Jarvan komut beklemeden ama rahatsiz etmeden dusuk riskli oneriler
uretebilsin.

- Backend event sistemi kur:
  - screen snapshot summary
  - active app
  - time spent
  - calendar/task context
- Proactive agent event uretsin, dogrudan konusmasin.
- Cooldown ve priority zorunlu olsun.
- Ilk kurallar dusuk riskli olsun:
  - uzun calisma
  - ayni hata ekranda uzun sure
  - yaklasan deadline

Done criteria:

- Proaktif oneriler rate limit ve cooldown ile gelir.
- Kullanici kapatinca tamamen susar.
- Yanlis pozitifler loglanabilir ve ayarlanabilir.

## v1.0 Daily Driver

Hedef: Jarvan gunluk kullanimda guvenilir dijital ikiz olur.

- Obsidian TODO ve aktif proje takibi.
- Calendar MCP.
- Ambient awareness.
- Worker/MCP/Memory katmanlari tek task state uzerinden konusur.
- Mac/Windows path ve config ayrimi tamamlanir.

## Development Rules

- Stable runtime'a deneysel kod dogrudan baglanmaz.
- Her yeni worker veya MCP path feature flag ile gelir.
- Hafiza backend'de yasar; model context'i sadece gecici kopyadir.
- Gemini Live persona ve real-time konusma katmanidir.
- Uzun isler async worker'a gider.
- Bir degisiklik Live oturumunu daha kirilgan yapiyorsa geri alinir.
