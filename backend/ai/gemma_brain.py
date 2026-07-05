"""Gemma 4 12B beyni — Ollama /api/chat üzerinden local dispatcher/santral.

LiveSession'daki Gemini'nin yerini alır: ses→metin (Whisper) sonrası metni alır,
function-calling / kısa cevap üretir. Ağır iş `start_gemini_task` ile CLI'ya gider.

Ölçülmüş latency dersleri (config.py'de de not düşüldü):
  - base_url '127.0.0.1' OLMALI (localhost → Windows'ta IPv6 timeout, +~2.2s/çağrı).
  - Kalıcı httpx.Client → her çağrıda yeni TCP handshake yok.
  - think=False → gemma4 reasoning token'ları üretmesin (santral rolünde ~4-5s tasarruf).
Birlikte: dispatch ~8s → ~1s.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

import httpx

from config import OLLAMA_URL, GEMMA_MODEL, GEMMA_THINK, GEMMA_NUM_CTX, GEMMA_NUM_GPU, GEMMA_TIMEOUT


class GemmaError(RuntimeError):
    """Ollama erişilemediğinde veya hata döndürdüğünde."""


class GemmaBrain:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        think: bool | None = None,
    ) -> None:
        if timeout is None:
            timeout = GEMMA_TIMEOUT
        self.base_url = (base_url or OLLAMA_URL).rstrip("/")
        self.model = model or GEMMA_MODEL
        self.think = GEMMA_THINK if think is None else think
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def unload(self) -> None:
        """Modeli Ollama'dan boşalt (keep_alive=0) — uyku modunda RAM/VRAM serbest.
        Sonraki chat çağrısı modeli yeniden yükler."""
        try:
            self._client.post("/api/generate",
                              json={"model": self.model, "keep_alive": 0}, timeout=10.0)
        except httpx.HTTPError:
            pass

    # ─── Sağlık ─────────────────────────────────────────────────────
    def health(self) -> bool:
        """Ollama ayakta ve model yüklü mü?"""
        try:
            r = self._client.get("/api/tags", timeout=3.0)
            if r.status_code != 200:
                return False
            names = [m.get("name", "") for m in r.json().get("models", [])]
            return any(self.model == n or self.model in n for n in names)
        except httpx.HTTPError:
            return False

    # ─── İstek gövdesi ──────────────────────────────────────────────
    def _body(self, messages: list[dict], *, stream: bool, json_mode: bool,
              tools: list[dict] | None, options: dict[str, Any] | None) -> dict:
        # num_ctx default 8192 — 27 tool şeması 4096'ya sığmıyor. Çağıran override edebilir.
        opts = {"num_ctx": GEMMA_NUM_CTX}
        # 12GB kartta 12B@8k sınırda: VRAM'e nefes alanı için katmanların bir kısmı
        # RAM'e taşınabilir (GEMMA_NUM_GPU, -1 = hepsi GPU'da).
        if GEMMA_NUM_GPU >= 0:
            opts["num_gpu"] = GEMMA_NUM_GPU
        opts.update(options or {})
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": opts,
            "think": self.think,
            "keep_alive": "30m",   # model RAM/VRAM'de kalsın
        }
        if json_mode:
            body["format"] = "json"
        if tools:
            body["tools"] = tools
        return body

    # ─── Tek seferlik chat ──────────────────────────────────────────
    def chat(self, messages: list[dict], *, json_mode: bool = False,
             tools: list[dict] | None = None, options: dict[str, Any] | None = None) -> dict:
        """Tam yanıt mesaj nesnesini döndürür ({"content":..., "tool_calls":...})."""
        body = self._body(messages, stream=False, json_mode=json_mode, tools=tools, options=options)
        try:
            r = self._client.post("/api/chat", json=body)
            r.raise_for_status()
            return r.json().get("message", {}) or {}
        except httpx.HTTPError as e:
            raise GemmaError(f"Ollama chat başarısız: {e}") from e

    def describe_image(self, image_bytes: bytes, prompt: str) -> str:
        """Görüntü + prompt → açıklama. gemma4 vision (local, see_screen için)."""
        import base64
        b64 = base64.b64encode(image_bytes).decode()
        msg = [{"role": "user", "content": prompt, "images": [b64]}]
        return (self.chat(msg).get("content") or "").strip()

    def chat_json(self, messages: list[dict], *, options: dict[str, Any] | None = None) -> dict:
        """JSON modunda chat → parse edilmiş dict."""
        raw = (self.chat(messages, json_mode=True, options=options).get("content") or "").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise GemmaError(f"Gemma JSON döndürmedi: {raw[:200]!r}") from e

    # ─── Streaming (TTS'e cümle cümle besleme seam'i) ───────────────
    def chat_stream(self, messages: list[dict], *,
                    options: dict[str, Any] | None = None) -> Iterator[str]:
        """Token akışı — düz cevapları cümle cümle Kokoro'ya beslemek için."""
        body = self._body(messages, stream=True, json_mode=False, tools=None, options=options)
        try:
            with self._client.stream("POST", "/api/chat", json=body) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    piece = obj.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if obj.get("done"):
                        break
        except httpx.HTTPError as e:
            raise GemmaError(f"Ollama stream başarısız: {e}") from e
