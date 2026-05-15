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
            # Embedding yoksa metin prefix karşılaştırması
            text = rec.get("document", "")[:120].lower()
            for k in kept:
                if text and text == k.get("document", "")[:120].lower():
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
            records = data["records"]
            # Her kayda kaynak cihazı işaretle
            for r in records:
                r["source_device"] = device
            all_records.extend(records)
            seen_devices.append(f"{device}({len(records)})")

        if not all_records:
            return {"ok": False, "error": "Hiç export bulunamadı."}

        logger.info(f"[sync] Merge başladı: {', '.join(seen_devices)} → toplam {len(all_records)} kayıt")

        # Deduplikat
        merged = _deduplicate(all_records)

        # Master ChromaDB'ye yaz (önce temizle, sonra ekle — tam sync)
        from ai.memory_core import get_memory_core
        core = get_memory_core()
        existing = core.get_all_embeddings()
        if existing["ids"]:
            core.delete_by_ids(existing["ids"])
        for rec in merged:
            core.save_insight(
                text=rec["document"],
                type=rec.get("metadata", {}).get("type", "behavioral")
            )

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

    # 1. Her iki cihaz da önce kendi hafızasını export eder
    results["export"] = export_local_memories()

    if IS_MAC:
        # 2a. Mac merge eder
        results["merge"] = merge_and_deduplicate()
    else:
        # 2b. Windows Mac'in merge dosyasını import eder
        results["import"] = import_merged_memories()

    return results
