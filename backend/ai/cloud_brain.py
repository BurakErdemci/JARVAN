"""CloudBrain — Gemini Flash text API üzerinden bulut beyin (Mac için).

GemmaBrain'in local_voice tarafından kullanılan arayüzünü (chat / describe_image /
health / unload) aynen sunar; .env'de BRAIN_PROVIDER=gemini ile seçilir.
LocalVoiceSession mesajları Ollama formatında tutar — dönüşüm burada yapılır,
çağıran taraf hangi beynin çalıştığını bilmez.

NOT: Bu Gemini LIVE değil — düz generate_content (text). Maliyet sızıntısı
Live audio'daydı; text çağrıları free tier içinde kalıyor.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_BRAIN_MODEL
from ai.gemma_brain import GemmaError


# ─── Format dönüşümleri (Ollama ↔ Gemini) ───────────────────────────────

def _to_gemini(messages: list[dict]) -> tuple[str, list[types.Content]]:
    """Ollama-format mesaj geçmişi → (system_instruction, Gemini contents).

    Ollama 'tool' mesajı fonksiyon adı taşımaz — tool sonuçları, önceki
    assistant mesajındaki tool_calls adlarıyla SIRAYLA eşleştirilir
    (local_voice her tool_call için sırayla bir tool mesajı ekliyor)."""
    system = ""
    contents: list[types.Content] = []
    pending_names: list[str] = []
    for m in messages:
        role = m.get("role", "")
        text = m.get("content") or ""
        if role == "system":
            system = text
        elif role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=text)]))
        elif role == "assistant":
            parts: list[types.Part] = []
            if text:
                parts.append(types.Part(text=text))
            pending_names = []
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                pending_names.append(name)
                part = types.Part.from_function_call(
                    name=name, args=fn.get("arguments") or {})
                # Gemini 3.x: functionCall geçmişe imzasız dönerse 400 INVALID_ARGUMENT
                if sig := tc.get("_thought_signature"):
                    part.thought_signature = base64.b64decode(sig)
                parts.append(part)
            if parts:
                contents.append(types.Content(role="model", parts=parts))
        elif role == "tool":
            name = pending_names.pop(0) if pending_names else "tool"
            try:
                resp = json.loads(text)
                if not isinstance(resp, dict):
                    resp = {"result": resp}
            except json.JSONDecodeError:
                resp = {"result": text}
            contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(name=name, response=resp)]))
    return system, contents


def _to_gemini_tools(tools: list[dict] | None) -> list[types.Tool] | None:
    """Ollama tool şemaları → Gemini Tool. (tool_registry şemaları zaten
    Gemini formatında; _ollama_tools'un sardığını burada geri açıyoruz.)"""
    if not tools:
        return None
    decls = [
        types.FunctionDeclaration(
            name=t["function"]["name"],
            description=t["function"].get("description", ""),
            parameters=t["function"].get("parameters") or None,
        )
        for t in tools
    ]
    return [types.Tool(function_declarations=decls)]


def _from_gemini(response: Any) -> dict:
    """Gemini yanıtı → Ollama-format mesaj ({"content":..., "tool_calls":[...]}).

    Parçalar tek tek gezilir (response.function_calls kısayolu yerine) çünkü
    Gemini 3.x'in thought_signature'ı parça üstünde — geçmişe geri verilmezse
    sonraki çağrı 400 INVALID_ARGUMENT döner. İmza tool_call dict'inde taşınır."""
    tool_calls = []
    texts = []
    candidates = response.candidates or []
    parts = (candidates[0].content.parts or []) if candidates and candidates[0].content else []
    for p in parts:
        if p.function_call:
            tc: dict[str, Any] = {"function": {
                "name": p.function_call.name,
                "arguments": dict(p.function_call.args or {}),
            }}
            if p.thought_signature:
                tc["_thought_signature"] = base64.b64encode(p.thought_signature).decode()
            tool_calls.append(tc)
        elif p.text:
            # response.text kısayolu yerine parçalardan topla — kısayol,
            # function_call'lı yanıtta her seferinde SDK warning'i basıyor.
            texts.append(p.text)
    msg: dict[str, Any] = {"content": "".join(texts).strip()}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


# ─── Beyin ───────────────────────────────────────────────────────────────

class CloudBrain:
    needs_warmup = False  # bulutta ısıtma çağrısı = kota israfı (local_voice atlar)

    def __init__(self, model: str | None = None) -> None:
        if not GEMINI_API_KEY:
            raise GemmaError("GEMINI_API_KEY yok — bulut beyin başlatılamaz.")
        self.model = model or GEMINI_BRAIN_MODEL
        self._client = genai.Client(api_key=GEMINI_API_KEY)

    def unload(self) -> None:
        """GemmaBrain uyumluluğu — bulutta boşaltılacak model yok."""

    def health(self) -> bool:
        """API key + model erişilebilir mi? (count_tokens: ücretsiz, hafif)"""
        try:
            self._client.models.count_tokens(model=self.model, contents="ping")
            return True
        except Exception:
            return False

    def chat(self, messages: list[dict], *, json_mode: bool = False,
             tools: list[dict] | None = None, options: dict[str, Any] | None = None) -> dict:
        """Tam yanıt mesajını Ollama formatında döndürür. `options` Ollama'ya
        özgü (num_ctx vb.) — arayüz uyumu için alınır, yok sayılır."""
        system, contents = _to_gemini(messages)
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            tools=_to_gemini_tools(tools),
            response_mime_type="application/json" if json_mode else None,
        )
        try:
            r = self._client.models.generate_content(
                model=self.model, contents=contents, config=config)
        except Exception as e:
            raise GemmaError(f"Gemini chat başarısız: {e}") from e
        return _from_gemini(r)

    def describe_image(self, image_bytes: bytes, prompt: str) -> str:
        """Görüntü + prompt → açıklama (see_screen için, Gemini vision)."""
        try:
            r = self._client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            )
        except Exception as e:
            raise GemmaError(f"Gemini vision başarısız: {e}") from e
        return (r.text or "").strip()
