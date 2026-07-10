"""Hafıza küratörü testleri — verdict parse/validasyon (LLM/API GEREKMEZ).

Koşturma:  cd backend && python -m pytest tests/test_memory_curator.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.memory_curator import _parse_verdicts


IDS = {"a", "b", "c"}


def test_gecerli_verdictler_parse_edilir():
    raw = json.dumps([
        {"id": "a", "verdict": "keep", "reason": "kalıcı tercih"},
        {"id": "b", "verdict": "expired", "reason": "tarihi geçti"},
        {"id": "c", "verdict": "STALE", "reason": "belirsiz"},
    ])
    v = _parse_verdicts(raw, IDS)
    assert v["a"]["verdict"] == "keep"
    assert v["b"]["verdict"] == "expired"
    assert v["c"]["verdict"] == "stale"  # büyük harf normalize edilir


def test_bilinmeyen_id_ve_verdict_atlanir():
    raw = json.dumps([
        {"id": "yok", "verdict": "junk", "reason": "x"},   # id listede yok
        {"id": "a", "verdict": "delete", "reason": "x"},    # geçersiz verdict
        {"id": "b", "verdict": "junk", "reason": "x"},
    ])
    v = _parse_verdicts(raw, IDS)
    assert "yok" not in v and "a" not in v
    assert v["b"]["verdict"] == "junk"


def test_bozuk_json_bos_doner():
    assert _parse_verdicts("model saçmaladı, JSON yok", IDS) == {}
    assert _parse_verdicts('{"tek": "obje, dizi değil"}', IDS) == {}


def test_uzun_reason_kirpilir():
    raw = json.dumps([{"id": "a", "verdict": "keep", "reason": "x" * 500}])
    v = _parse_verdicts(raw, IDS)
    assert len(v["a"]["reason"]) == 200
