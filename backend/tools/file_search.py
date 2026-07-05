"""Akıllı dosya arama — Everything (es.exe) → mdfind (Mac) → rglob fallback.

Eski find_file'ın sorunu: birebir substring ister, bulamayınca öneri vermeden
"bulunamadı" der. Burada sorgu normalize edilir (TR karakter toleransı), motor
gevşek arama yapar, adaylar fuzzy skor + güncellik + konum ile sıralanır.
Güçlü eşleşme yoksa en yakın adaylar `suggestion: true` ile döner — Gemma
"şunu mu kastettin?" diye sorabilsin.
"""
from __future__ import annotations

import difflib
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
HOME = Path.home()

ES_PATH = os.getenv("EVERYTHING_ES_PATH", "")

# ─── Normalizasyon ──────────────────────────────────────────────────────
_TR_MAP = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")


def normalize(s: str) -> str:
    """Küçük harf + TR karakterleri sadeleştir + noktalama → boşluk."""
    s = s.translate(_TR_MAP).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


# Tür bildiren dolgu kelimeleri — dosya ADINDA aranmaz ("zombi klasörü" → "zombi")
_STOPWORDS = {"folder", "file", "dosya", "dosyasi", "klasor", "klasoru", "kloser",
              "directory", "dizin", "document", "belge"}


def _words(query: str) -> list[str]:
    ws = [w for w in normalize(query).split() if len(w) > 1]
    meaningful = [w for w in ws if w not in _STOPWORDS]
    return meaningful or ws or normalize(query).split()


# ─── Skorlama ───────────────────────────────────────────────────────────
_GOOD_DIRS = ("desktop", "masaüstü", "documents", "belgeler", "downloads", "pictures", "music", "videos")
_BAD_PARTS = ("appdata", "node_modules", "__pycache__", ".git", "windows", "program files",
              "programdata", ".venv", "site-packages", "cache", "$recycle.bin")


def score_candidate(query: str, path: str, mtime: float = 0.0) -> float:
    """0-1+ arası skor: isim benzerliği + kelime kapsaması + konum + güncellik."""
    name = normalize(Path(path).stem)
    q = normalize(query)
    sim = difflib.SequenceMatcher(None, q, name).ratio()

    qw = set(q.split())
    nw = set(name.split())
    coverage = len(qw & nw) / len(qw) if qw else 0.0
    # kelime birebir geçmese de prefix eşleşmesi say (rapor ~ raporlar)
    if qw and coverage < 1.0:
        soft = sum(1 for w in qw if any(n.startswith(w) or w.startswith(n) for n in nw))
        coverage = max(coverage, soft / len(qw) * 0.9)

    s = 0.45 * sim + 0.45 * coverage

    low = path.replace("\\", "/").lower()
    if any(b in low for b in _BAD_PARTS):
        s -= 0.25
    if any(f"/{g}/" in low or low.rstrip("/").endswith(g) for g in _GOOD_DIRS):
        s += 0.10

    if mtime:
        age_days = max(0.0, (time.time() - mtime) / 86400)
        if age_days < 30:
            s += 0.05 * (1 - age_days / 30)
    return s


# ─── Motorlar ───────────────────────────────────────────────────────────
def _find_es() -> str | None:
    if ES_PATH and os.path.exists(ES_PATH):
        return ES_PATH
    found = shutil.which("es")
    if found:
        return found
    for c in (os.path.expandvars(r"%LOCALAPPDATA%\Everything\es.exe"),
              r"C:\Program Files\Everything\es.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\es.exe")):
        if os.path.exists(c):
            return c
    return None


def _run(cmd: list[str], timeout: int = 10) -> list[str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             encoding="utf-8", errors="replace")
        if out.returncode != 0:
            return []
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def _search_everything(words: list[str], limit: int = 100) -> list[str] | None:
    """es.exe ile ara. Everything servisi yoksa None (fallback'e düş)."""
    es = _find_es()
    if not es:
        return None
    paths = _run([es, "-n", str(limit), *words])
    if not paths:
        # gevşet: kelimeleri ilk 4 karaktere indir (yazım/telaffuz toleransı)
        loose = [w[:4] for w in words if len(w) >= 4]
        if loose:
            paths = _run([es, "-n", str(limit), *loose])
    if not paths:
        # son çare: VEYA + kısaltılmış formlar ("zombie" söylenir, klasör "zombi"dir) —
        # herhangi biri geçsin, sıralamayı skor yapar
        alts = {w for w in words} | {w[:4] for w in words if len(w) >= 4}
        paths = _run([es, "-n", str(limit), "|".join(sorted(alts))])
    return paths


def _search_mdfind(words: list[str], limit: int = 100) -> list[str] | None:
    if not IS_MAC or not shutil.which("mdfind"):
        return None
    q = " ".join(words)
    paths = _run(["mdfind", "-name", q])
    if not paths and words:
        paths = _run(["mdfind", "-name", words[0]])
    return paths[:limit]


def _search_walk(words: list[str], search_root: Path | None, limit: int = 100) -> list[str]:
    """Motor yoksa: bilinen klasörlerde gevşek rglob (eski davranışın akıllısı)."""
    roots = [search_root] if search_root else [
        HOME / "Desktop", HOME / "Documents", HOME / "Downloads", HOME / "Pictures"]
    hits: list[str] = []
    for root in roots:
        if not root or not root.exists():
            continue
        try:
            for item in root.rglob("*"):
                n = normalize(item.name)
                if any(w in n for w in words):
                    hits.append(str(item))
                    if len(hits) >= limit:
                        return hits
        except (PermissionError, OSError):
            continue
    return hits


# ─── Ana giriş ──────────────────────────────────────────────────────────
STRONG_MATCH = 0.62  # üstü: "buldum" — altı: "şunu mu kastettin?"


def smart_find(name: str, search_in: str | None = None, max_results: int = 6) -> dict:
    """Fuzzy dosya arama. Asla çıplak 'bulunamadı' demez — aday önerir."""
    words = _words(name)
    if not words:
        return {"ok": False, "error": "Aranacak isim boş."}

    root: Path | None = None
    if search_in:
        from tools.filesystem import resolve_path
        root = resolve_path(search_in)

    engine = "everything"
    paths = _search_everything(words)
    if paths is None:
        engine = "mdfind"
        paths = _search_mdfind(words)
    if paths is None:
        engine = "walk"
        paths = _search_walk(words, root)

    if root is not None:
        prefix = os.path.normcase(str(root))
        paths = [p for p in paths if os.path.normcase(p).startswith(prefix)]

    scored: list[tuple[float, str, os.stat_result | None]] = []
    seen: set[str] = set()
    for p in paths:
        key = os.path.normcase(p)
        if key in seen:
            continue
        seen.add(key)
        try:
            st = os.stat(p)
            mtime = st.st_mtime
        except OSError:
            st, mtime = None, 0.0
        # skoru dolgu kelimeleri atılmış sorguyla hesapla ("zombi klasörü" → "zombi")
        scored.append((score_candidate(" ".join(words), p, mtime), p, st))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:max_results]

    if not top:
        return {"ok": False, "engine": engine,
                "error": f"'{name}' için hiç aday bulunamadı.",
                "hint": "Farklı bir kelimeyle ya da klasör belirterek tekrar dene."}

    files = []
    for s, p, st in top:
        is_dir = bool(st and os.path.isdir(p))
        files.append({
            "path": p,
            "name": os.path.basename(p),
            "type": "folder" if is_dir else "file",
            "size_kb": (st.st_size // 1024) if (st and not is_dir) else None,
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)) if st else None,
            "score": round(s, 2),
        })

    strong = top[0][0] >= STRONG_MATCH
    result = {"ok": True, "engine": engine, "count": len(files),
              "files": files, "suggestion": not strong}
    if not strong:
        result["note"] = ("Tam eşleşme yok — bunlar en yakın adaylar. "
                          "Kullanıcıya hangisini kastettiğini SOR, tahmin etme.")
    return result
