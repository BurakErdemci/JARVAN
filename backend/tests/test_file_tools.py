"""Akıllı dosya katmanı testleri — normalize/skor, smart_find (walk fallback), edit_file.

Koşturma:  cd backend && python -m pytest tests/test_file_tools.py -q
Ses/Ollama/Everything GEREKMEZ (Everything entegrasyonu kuruluysa ayrıca test edilir).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import file_search
from tools.file_search import normalize, score_candidate, smart_find
from tools.filesystem import edit_file


# ─── Normalizasyon ──────────────────────────────────────────────────────
def test_normalize_turkish_chars():
    assert normalize("Şükrü'nün RAPORU (final).pdf") == "sukru nun raporu final pdf"


def test_normalize_mixed():
    assert normalize("Proje_Ödevi-V2") == "proje odevi v2"


# ─── Skorlama ───────────────────────────────────────────────────────────
def test_score_exact_beats_partial():
    exact = score_candidate("rapor final", r"C:\Users\x\Desktop\rapor_final.pdf")
    partial = score_candidate("rapor final", r"C:\Users\x\Desktop\rapor_taslak.pdf")
    assert exact > partial


def test_score_penalizes_system_dirs():
    user = score_candidate("rapor", r"C:\Users\x\Documents\rapor.pdf")
    system = score_candidate("rapor", r"C:\Windows\System32\rapor.pdf")
    assert user > system


def test_score_tolerates_inflection():
    # "rapor" araması "raporlar" klasörünü de makul skorlamalı (prefix toleransı)
    s = score_candidate("rapor", r"C:\Users\x\Desktop\raporlar")
    assert s > 0.4


# ─── smart_find (walk fallback — motor bağımsız) ────────────────────────
@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Everything/mdfind'i devre dışı bırak, tmp klasörünü arama köküne çevir."""
    (tmp_path / "odev_raporu_final.txt").write_text("icerik", encoding="utf-8")
    (tmp_path / "muzik_listesi.md").write_text("liste", encoding="utf-8")
    (tmp_path / "alakasiz.bin").write_text("x", encoding="utf-8")
    # pytest tmp'si AppData altında → konum cezası testin konusu değil, kapat
    monkeypatch.setattr(file_search, "_BAD_PARTS", ())
    monkeypatch.setattr(file_search, "_search_everything", lambda w, limit=100: None)
    monkeypatch.setattr(file_search, "_search_mdfind", lambda w, limit=100: None)
    monkeypatch.setattr(
        file_search, "_search_walk",
        lambda words, root, limit=100: [str(p) for p in tmp_path.iterdir()
                                        if any(w in normalize(p.name) for w in words)])
    return tmp_path


def test_smart_find_fuzzy_hit(sandbox):
    r = smart_find("ödev raporu")
    assert r["ok"] is True
    assert r["files"][0]["name"] == "odev_raporu_final.txt"
    assert r["suggestion"] is False  # güçlü eşleşme


def test_smart_find_suggests_instead_of_failing(sandbox):
    # Yanlış/eksik telaffuz: yine de aday dönmeli, 'bulunamadı' dememeli
    r = smart_find("muzik listem")
    assert r["ok"] is True
    assert any(f["name"] == "muzik_listesi.md" for f in r["files"])


def test_smart_find_empty_query():
    assert smart_find("")["ok"] is False


@pytest.mark.skipif(file_search._find_es() is None, reason="Everything (es.exe) kurulu değil")
def test_everything_integration():
    r = file_search._search_everything(["windows"])
    assert r is not None


# ─── edit_file ──────────────────────────────────────────────────────────
@pytest.fixture
def txt(tmp_path):
    p = tmp_path / "notlar.txt"
    p.write_text("satir bir\nsatir iki\n", encoding="utf-8")
    return p


def test_edit_replace(txt):
    r = edit_file(str(txt), "replace", new_text="satir 2", old_text="satir iki")
    assert r["ok"] is True and r["replaced"] == 1
    assert txt.read_text(encoding="utf-8") == "satir bir\nsatir 2\n"
    assert os.path.exists(r["backup"])  # yedek alınmış
    from pathlib import Path
    assert Path(r["backup"]).read_text(encoding="utf-8") == "satir bir\nsatir iki\n"


def test_edit_replace_missing_old_text(txt):
    r = edit_file(str(txt), "replace", new_text="x", old_text="olmayan metin")
    assert r["ok"] is False
    assert txt.read_text(encoding="utf-8") == "satir bir\nsatir iki\n"  # dokunulmadı


def test_edit_append(txt):
    r = edit_file(str(txt), "append", new_text="satir uc")
    assert r["ok"] is True
    assert txt.read_text(encoding="utf-8").endswith("satir iki\nsatir uc")


def test_edit_overwrite(txt):
    r = edit_file(str(txt), "overwrite", new_text="yepyeni")
    assert r["ok"] is True
    assert txt.read_text(encoding="utf-8") == "yepyeni"


def test_edit_rejects_binary(tmp_path):
    p = tmp_path / "resim.png"
    p.write_bytes(b"\x89PNG")
    r = edit_file(str(p), "append", new_text="x")
    assert r["ok"] is False


def test_edit_missing_file(tmp_path):
    r = edit_file(str(tmp_path / "yok.txt"), "append", new_text="x")
    assert r["ok"] is False


def test_edit_invalid_mode(txt):
    r = edit_file(str(txt), "delete", new_text="x")
    assert r["ok"] is False
