"""CloudBrain format dönüştürücü testleri — Ollama ↔ Gemini mesaj/tool çevrimi.

Koşturma:  cd backend && python -m pytest tests/test_cloud_brain.py -q
API key/ağ GEREKMEZ — sadece saf dönüşüm fonksiyonları test edilir.
"""
import base64
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.cloud_brain import _to_gemini, _to_gemini_tools, _from_gemini


# ─── Ollama → Gemini (mesaj geçmişi) ────────────────────────────────────
def test_system_ayrilir_user_cevrilir():
    system, contents = _to_gemini([
        {"role": "system", "content": "Sen Jarvan'sın."},
        {"role": "user", "content": "merhaba"},
    ])
    assert system == "Sen Jarvan'sın."
    assert len(contents) == 1
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "merhaba"


def test_tool_call_ve_sonucu_eslesir():
    """Ollama tool mesajı fonksiyon adı taşımaz — önceki assistant'ın
    tool_calls adlarıyla sırayla eşleşmeli."""
    result = {"ok": True, "temp": "22C"}
    system, contents = _to_gemini([
        {"role": "user", "content": "hava nasıl?"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "get_weather", "arguments": {"city": "Ankara"}}},
        ]},
        {"role": "tool", "content": json.dumps(result)},
    ])
    assert contents[1].role == "model"
    fc = contents[1].parts[0].function_call
    assert fc.name == "get_weather"
    assert dict(fc.args) == {"city": "Ankara"}
    fr = contents[2].parts[0].function_response
    assert fr.name == "get_weather"
    assert dict(fr.response) == result


def test_coklu_tool_call_sirali_eslesme():
    system, contents = _to_gemini([
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "a", "arguments": {}}},
            {"function": {"name": "b", "arguments": {}}},
        ]},
        {"role": "tool", "content": "{}"},
        {"role": "tool", "content": "{}"},
    ])
    assert contents[1].parts[0].function_response.name == "a"
    assert contents[2].parts[0].function_response.name == "b"


def test_tool_sonucu_json_degilse_sarilir():
    _, contents = _to_gemini([
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "x", "arguments": {}}},
        ]},
        {"role": "tool", "content": "düz metin sonuç"},
    ])
    assert dict(contents[1].parts[0].function_response.response) == {"result": "düz metin sonuç"}


# ─── Tool şemaları ──────────────────────────────────────────────────────
def test_ollama_tool_semasi_acilir():
    tools = _to_gemini_tools([
        {"type": "function", "function": {
            "name": "find_file",
            "description": "dosya bul",
            "parameters": {"type": "object", "properties": {"name": {"type": "string"}}},
        }},
    ])
    assert len(tools) == 1
    decl = tools[0].function_declarations[0]
    assert decl.name == "find_file"
    assert decl.description == "dosya bul"


def test_bos_tools_none_doner():
    assert _to_gemini_tools(None) is None
    assert _to_gemini_tools([]) is None


# ─── Gemini → Ollama (yanıt) ────────────────────────────────────────────
def _mock_response(text=None, parts=()):
    all_parts = list(parts)
    if text is not None:
        all_parts.append(SimpleNamespace(function_call=None, text=text, thought_signature=None))
    return SimpleNamespace(candidates=[
        SimpleNamespace(content=SimpleNamespace(parts=all_parts)),
    ])


def test_duz_metin_yanit():
    r = _mock_response(text="Good evening, sir.")
    assert _from_gemini(r) == {"content": "Good evening, sir."}


def test_tool_calls_yanit():
    r = _mock_response(parts=[SimpleNamespace(
        function_call=SimpleNamespace(name="sleep_mode", args={}),
        thought_signature=None, text=None,
    )])
    msg = _from_gemini(r)
    assert msg["content"] == ""
    assert msg["tool_calls"] == [{"function": {"name": "sleep_mode", "arguments": {}}}]


def test_thought_signature_round_trip():
    """Gemini 3.x imzası yanıttan alınıp geçmişe AYNEN geri verilmeli —
    verilmezse API 400 INVALID_ARGUMENT döner (canlıda görüldü, TRT 1 vakası)."""
    r = _mock_response(parts=[SimpleNamespace(
        function_call=SimpleNamespace(name="open_url", args={"url": "https://x.com"}),
        thought_signature=b"imza-bytes", text=None,
    )])
    msg = _from_gemini(r)
    # Yanıttan imza base64 olarak yakalanır
    tc = msg["tool_calls"][0]
    assert base64.b64decode(tc["_thought_signature"]) == b"imza-bytes"
    # Geçmişe geri kurarken parçaya aynen takılır
    _, contents = _to_gemini([
        {"role": "assistant", "content": "", "tool_calls": [tc]},
        {"role": "tool", "content": "{}"},
    ])
    assert contents[0].parts[0].thought_signature == b"imza-bytes"
