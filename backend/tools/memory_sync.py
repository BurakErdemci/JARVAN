"""
Jarvan çift-taraflı hafıza senkronizasyonu.

Her cihaz kendi local ChromaDB'sine yazar.
Mac her gece:
  1. Her iki cihazın export'larını okur
  2. Embedding benzerliğiyle duplikatları tespit eder (%92+ = duplikat)
  3. Tekilleştirilmiş hafızayı master ChromaDB'ye yazar
  4. Birleşik export'u JarvanShare'e geri koyar (Windows import eder)

Windows her gece:
  1. Kendi yeni hafızalarını JarvanShare/exports/windows/ altına atar
  2. Mac'in merge ettiği birleşik export'u import eder
"""
import json
import logging
import math
import os
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("jarvan.memory_sync")

IS_MAC = platform.system() == "Darwin"
THIS_DEVICE = "mac" if IS_MAC else "windows"

_BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SHARE_ROOT   = Path(os.getenv("JARVAN_SHARE_PATH",
    str(Path.home() / "JarvanShare") if IS_MAC else r"C:\JarvanShare"))
EXPORTS_DIR  = SHARE_ROOT / "exports"
MERGED_FILE  = SHARE_ROOT / "exports" / "merged.json"
MY_EXPORT    = EXPORTS_DIR / THIS_DEVICE / "memories.json"
STATE_FILE   = _BASE / "data" / "sync_state.json"

SIMILARITY_THRESHOLD = 0.92   # Bu üstü duplikat sayılır

# save_insight'ın eklediği '[2026-05-13 15:48:14] ' prefix'leri (zincir olabilir)
_TS_PREFIX = re.compile(r"^(?:\[\d{4}-\d{2}-\d{2}[^\]]*\]\s*)+")
_TS_ALL    = re.compile(r"\[(\d{4}-\d{2}-\d{2}[^\]]*)\]")


def _normalize_record(rec: Dict) -> Dict:
    """Dokümanın başındaki zaman damgası zincirini soyar; en eski damgayı
    metadata['timestamp']'e taşır. Eski merge bug'ı her gece yeni damga
    ekliyordu — aynı bilgi farklı zincirlerle 8-9 kopya olmuştu."""
    doc = rec.get("document", "")
    m = _TS_PREFIX.match(doc)
    if not m:
        return rec
    stamps = _TS_ALL.findall(m.group(0))
    rec = {**rec, "document": doc[m.end():].strip()}
    if stamps:
        meta = dict(rec.get("metadata") or {})
        meta["timestamp"] = min(stamps)  # ilk kayıt anı (zincirin en eskisi)
        rec["metadata"] = meta
    return rec


# ─── Yardımcılar ───────────────────────────────────────────────────

def _cosine(a: List[float], b: List[float]) -> float:
    dot  = sum(x * y for x, y in zip(a, b))
    na   = math.sqrt(sum(x * x for x in a))
    nb   = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _last_sync_time() -> Optional[str]:
    state = _load_json(STATE_FILE)
    return state.get("last_sync") if state else None


def _save_sync_time() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _save_json(STATE_FILE, {"last_sync": datetime.now().isoformat()})


# ─── Local temizlik (eski merge bug'ının mirasını onarır) ──────────

def clean_local_memories() -> dict:
    """Local ChromaDB'deki damga zincirlerini soyar ve tam-metin duplikatları
    siler. Her cihazda export'tan ÖNCE çalışır — böylece export'lar temiz gider
    ve eski bug'la şişmiş DB'ler (224 kayıt / 46 gerçek bilgi) kendini onarır."""
    try:
        from ai.memory_core import get_memory_core
        core = get_memory_core()
        data = core.get_all_embeddings()
        if not data["ids"]:
            return {"ok": True, "cleaned": 0, "total": 0}

        seen_texts = set()
        changed = []   # damgası soyulan kayıtlar (aynı id ile güncellenecek)
        dup_ids = []   # tam-metin duplikat/boş kayıtlar (silinecek)
        total_kept = 0
        for i, doc_id in enumerate(data["ids"]):
            rec = _normalize_record({
                "id": doc_id,
                "document": data["documents"][i],
                "metadata": data["metadatas"][i],
            })
            key = rec["document"].strip().lower()
            if not key or key in seen_texts:
                dup_ids.append(doc_id)
                continue
            seen_texts.add(key)
            total_kept += 1
            if rec["document"] != data["documents"][i]:
                changed.append(rec)

        if not changed and not dup_ids:
            return {"ok": True, "cleaned": 0, "total": total_kept}

        # ÖNCE yaz — yazma başarısızsa (API/embedding hatası) silme YAPILMAZ.
        if changed and core.upsert_verbatim(changed) == 0:
            return {"ok": False, "error": "Normalize edilen kayıtlar yazılamadı — silme atlandı."}
        core.delete_by_ids(dup_ids)
        logger.info(f"[sync] Local temizlik: {len(data['ids'])} → {total_kept} kayıt "
                    f"({len(dup_ids)} duplikat silindi, {len(changed)} damga soyuldu)")
        return {"ok": True, "cleaned": len(dup_ids), "total": total_kept}
    except Exception as e:
        logger.error(f"[sync] Local temizlik hatası: {e}")
        return {"ok": False, "error": str(e)}


# ─── Export (her cihaz kendi hafızasını atar) ──────────────────────

def export_local_memories() -> dict:
    """Bu cihazın hafızasını JarvanShare/exports/{cihaz}/memories.json'a yazar."""
    try:
        from ai.memory_core import get_memory_core
        records = get_memory_core().export_all()
        MY_EXPORT.parent.mkdir(parents=True, exist_ok=True)
        _save_json(MY_EXPORT, {
            "device": THIS_DEVICE,
            "exported_at": datetime.now().isoformat(),
            "count": len(records),
            "records": records,
        })
        logger.info(f"[sync] {len(records)} hafıza export edildi → {MY_EXPORT}")
        return {"ok": True, "exported": len(records)}
    except Exception as e:
        logger.error(f"[sync] Export hatası: {e}")
        return {"ok": False, "error": str(e)}


# ─── Merge + Deduplicate (sadece Mac çalıştırır) ───────────────────

def _deduplicate(all_records: List[Dict]) -> List[Dict]:
    """
    Embedding benzerliği %92+ olan kayıtları tekilleştirir.
    Embedding yoksa metin benzerliği kullanır.
    """
    kept: List[Dict] = []
    kept_embeddings: List[Optional[List[float]]] = []

    for rec in all_records:
        emb = rec.get("embedding")
        is_dup = False

        if emb and kept_embeddings:
            for ke in kept_embeddings:
                if ke and _cosine(emb, ke) >= SIMILARITY_THRESHOLD:
                    is_dup = True
                    break
        else:
            # Embedding yoksa tam metin karşılaştırması (kayıtlar normalize
            # edilmiş geliyor — damga prefix'leri soyulmuş durumda)
            text = rec.get("document", "").strip().lower()
            for k in kept:
                if text and text == k.get("document", "").strip().lower():
                    is_dup = True
                    break

        if not is_dup:
            kept.append(rec)
            kept_embeddings.append(emb)

    removed = len(all_records) - len(kept)
    if removed:
        logger.info(f"[sync] {removed} duplikat filtrelendi ({len(all_records)} → {len(kept)})")
    return kept


def merge_and_deduplicate() -> dict:
    """
    Mac'te çalışır. Tüm cihaz export'larını okur, tekilleştirir,
    master ChromaDB'ye yazar ve merged.json'ı JarvanShare'e koyar.
    """
    if not IS_MAC:
        return {"ok": False, "error": "Merge sadece Mac'te çalışır."}

    try:
        all_records: List[Dict] = []
        seen_devices = []

        for device_dir in EXPORTS_DIR.iterdir():
            if not device_dir.is_dir():
                continue
            export_file = device_dir / "memories.json"
            if not export_file.exists():
                continue
            data = _load_json(export_file)
            if not data or "records" not in data:
                continue
            device = data.get("device", device_dir.name)
            # Damga zincirlerini soy + kaynak cihazı işaretle
            records = [_normalize_record(r) for r in data["records"]]
            for r in records:
                r["source_device"] = device
            all_records.extend(records)
            seen_devices.append(f"{device}({len(records)})")

        if not all_records:
            return {"ok": False, "error": "Hiç export bulunamadı."}

        logger.info(f"[sync] Merge başladı: {', '.join(seen_devices)} → toplam {len(all_records)} kayıt")

        # Deduplikat
        merged = _deduplicate(all_records)

        # Master ChromaDB'ye yaz. upsert_verbatim ŞART: save_insight her kayda
        # yeni '[tarih]' prefix'i ekliyordu → her gece merge hafızayı kartopu
        # gibi şişiriyordu. Sıra da önemli: ÖNCE yaz, başarılıysa artıkları sil.
        from ai.memory_core import get_memory_core
        core = get_memory_core()
        existing = core.get_all_embeddings()
        if core.upsert_verbatim(merged) == 0 and merged:
            return {"ok": False, "error": "Merge master'a yazılamadı — mevcut kayıtlar korundu."}
        merged_ids = {r["id"] for r in merged}
        core.delete_by_ids([i for i in existing["ids"] if i not in merged_ids])

        # JarvanShare'e geri yaz (Windows okur)
        _save_json(MERGED_FILE, {
            "merged_at": datetime.now().isoformat(),
            "source_devices": seen_devices,
            "count": len(merged),
            "records": merged,
        })

        _save_sync_time()
        logger.info(f"[sync] Merge tamamlandı: {len(merged)} kayıt master'a yazıldı.")
        return {
            "ok": True,
            "result": f"Hafıza birleştirildi: {len(merged)} kayıt ({', '.join(seen_devices)})",
            "merged_count": len(merged),
            "removed_duplicates": len(all_records) - len(merged),
        }

    except Exception as e:
        logger.error(f"[sync] Merge hatası: {e}")
        return {"ok": False, "error": str(e)}


# ─── Import (Windows merge sonucunu alır) ──────────────────────────

def import_merged_memories() -> dict:
    """Windows'ta çalışır. Mac'in merge ettiği birleşik hafızayı import eder."""
    if IS_MAC:
        return {"ok": False, "error": "Import sadece Windows'ta çalışır."}

    if not MERGED_FILE.exists():
        return {"ok": False, "error": "Henüz merge dosyası yok, Mac sync yapmamış."}

    try:
        data = _load_json(MERGED_FILE)
        if not data or "records" not in data:
            return {"ok": False, "error": "Merge dosyası bozuk."}

        from ai.memory_core import get_memory_core
        count = get_memory_core().import_insights(data["records"], source="mac_merge")
        _save_sync_time()
        return {
            "ok": True,
            "result": f"Mac'ten {count} yeni hafıza import edildi.",
            "imported": count,
        }
    except Exception as e:
        logger.error(f"[sync] Import hatası: {e}")
        return {"ok": False, "error": str(e)}


# ─── Gece Rutini (main.py'dan çağrılır) ────────────────────────────

def nightly_sync() -> dict:
    """
    Her cihazda gece çalışır.
    Mac: export → merge → deduplicate
    Windows: export → (Mac merge eder) → import
    """
    results = {}

    # 0. Eski merge bug'ının şişirdiği local DB'yi onar (damga zinciri + duplikat)
    results["clean"] = clean_local_memories()

    # 1. Her iki cihaz da önce kendi hafızasını export eder
    results["export"] = export_local_memories()

    if IS_MAC:
        # 2a. Mac merge eder
        results["merge"] = merge_and_deduplicate()
        # 3. Küratör: eskimiş/gereksiz bilgileri arşivle, bayatları işaretle
        from tools.memory_curator import curate_memories
        results["curate"] = curate_memories()
        if results["curate"].get("archived") or results["curate"].get("stale"):
            _refresh_merged_from_master()  # Windows küratörden geçmiş halini alsın
    else:
        # 2b. Windows Mac'in merge dosyasını import eder
        results["import"] = import_merged_memories()

    return results


def _refresh_merged_from_master() -> None:
    """Küratör master'ı değiştirdikten sonra merged.json'ı güncel haliyle yazar."""
    try:
        from ai.memory_core import get_memory_core
        records = get_memory_core().export_all()
        _save_json(MERGED_FILE, {
            "merged_at": datetime.now().isoformat(),
            "source_devices": ["master_post_curation"],
            "count": len(records),
            "records": records,
        })
    except Exception as e:
        logger.error(f"[sync] merged.json tazelenemedi: {e}")
