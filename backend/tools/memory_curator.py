"""Gece hafıza küratörü — "bu bilgi hâlâ güncel mi, gerekli mi?" sorgusu.

Mac'te nightly_sync'in merge adımından SONRA çalışır. Master'daki tüm kayıtları
bugünün tarihiyle birlikte bulut beyne verir; her kayıt için tek karar alır:

  keep    → dokunma (kalıcı tercih/bilgi)
  expired → tarihi geçmiş olay/plan → arşive taşı + master'dan sil
  junk    → kalıcı hafızada yeri olmayan tek seferlik komut → arşive taşı + sil
  stale   → muhtemelen bayat ama emin değil → SİLME, metadata'ya işaretle
            (Jarvan cevap verirken "bu bilgi eskimiş olabilir" diyebilsin)

Güvenlik: silinen hiçbir şey kaybolmaz — önce JarvanShare/exports/archive.json'a
yazılır, yazma başarısızsa silme yapılmaz. Bilinmeyen id/verdict → keep sayılır.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("jarvan.memory_curator")

VALID_VERDICTS = {"keep", "expired", "stale", "junk"}

CURATOR_PROMPT = """Sen Jarvan adlı asistanın hafıza küratörüsün. Bugünün tarihi: {today}.

Aşağıda kalıcı hafıza kayıtları var. Her biri için karar ver:
- "keep": kalıcı geçerli bilgi, tercih veya talimat (örn. kahve tercihi, çalışma alışkanlığı)
- "expired": tarihi bugüne göre GEÇMİŞ olay/plan (örn. geçmiş bir seyahat araştırması)
- "stale": muhtemelen artık güncel değil ama emin olamazsın (örn. "şu an X'i test ediyor")
- "junk": kalıcı hafızada yeri olmayan tek seferlik komut veya önemsiz detay

Kararsızsan "keep" seç — silmek geri alınabilir ama yanlış silmemek daha iyi.
SADECE şu formatta bir JSON dizisi döndür, başka hiçbir şey yazma:
[{{"id": "...", "verdict": "keep", "reason": "kısa gerekçe"}}]

KAYITLAR:
{records}"""


def _parse_verdicts(raw: str, valid_ids: set) -> Dict[str, dict]:
    """Model çıktısından {id: {verdict, reason}} çıkarır. Bilinmeyen id veya
    geçersiz verdict sessizce atlanır (= keep). Bozuk JSON → boş dict."""
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"[curator] Model JSON döndürmedi: {raw[:120]!r}")
        return {}
    if not isinstance(items, list):
        return {}
    out: Dict[str, dict] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        rid = it.get("id")
        verdict = (it.get("verdict") or "").strip().lower()
        if rid in valid_ids and verdict in VALID_VERDICTS:
            out[rid] = {"verdict": verdict, "reason": (it.get("reason") or "")[:200]}
    return out


def curate_memories() -> dict:
    """Master hafızayı gözden geçirir; expired/junk → arşiv+sil, stale → işaretle."""
    from config import GEMINI_API_KEY
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY yok — küratör atlandı."}

    try:
        from ai.cloud_brain import CloudBrain
        from ai.memory_core import get_memory_core
        from tools.memory_sync import SHARE_ROOT, _load_json, _save_json

        core = get_memory_core()
        records = core.export_all()
        if not records:
            return {"ok": True, "reviewed": 0, "archived": 0, "stale": 0}

        listing = "\n".join(
            f"[{r['id']}] (kayıt: {(r.get('metadata') or {}).get('timestamp', '?')}) {r['document']}"
            for r in records
        )
        today = datetime.now().strftime("%d %B %Y, %A")
        prompt = CURATOR_PROMPT.format(today=today, records=listing)

        brain = CloudBrain()
        msg = brain.chat([{"role": "user", "content": prompt}], json_mode=True)
        verdicts = _parse_verdicts(msg.get("content") or "", {r["id"] for r in records})
        if not verdicts:
            return {"ok": False, "error": "Küratör karar üretemedi (JSON parse edilemedi)."}

        to_archive = []   # expired + junk
        to_flag = []      # stale
        for r in records:
            v = verdicts.get(r["id"])
            if not v:
                continue
            if v["verdict"] in ("expired", "junk"):
                to_archive.append({**r, **v, "archived_at": datetime.now().isoformat()})
            elif v["verdict"] == "stale":
                meta = dict(r.get("metadata") or {})
                meta["stale"] = v["reason"] or "güncelliği belirsiz"
                to_flag.append({**r, "metadata": meta})

        # ÖNCE arşive yaz — yazılamazsa silme YAPILMAZ.
        if to_archive:
            archive_file = SHARE_ROOT / "exports" / "archive.json"
            archive = _load_json(archive_file) or []
            archive.extend(to_archive)
            _save_json(archive_file, archive)
            core.delete_by_ids([r["id"] for r in to_archive])
        if to_flag:
            core.upsert_verbatim(to_flag)

        for r in to_archive:
            logger.info(f"[curator] Arşivlendi ({r['verdict']}): {r['document'][:70]} — {r['reason']}")
        for r in to_flag:
            logger.info(f"[curator] Bayat işaretlendi: {r['document'][:70]}")

        return {"ok": True, "reviewed": len(records),
                "archived": len(to_archive), "stale": len(to_flag)}

    except Exception as e:
        logger.error(f"[curator] Hata: {e}")
        return {"ok": False, "error": str(e)}
