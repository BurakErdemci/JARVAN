"""Gömülü TTS — Kokoro ONNX (İngilizce, bm_george). Voicebox'ın yerini alır.

Jarvan TR+EN anlar ama HER ZAMAN İngilizce konuşur (İngilizce sesler çok daha iyi).
Model tek sefer yüklenir (~0.9s). Cümle cümle look-ahead: cümle n çalarken cümle n+1
arka planda sentezlenir → ilk ses <1s'de başlar (RTF ~0.45, CPU).

Bağımlılıklar: kokoro-onnx, espeakng-loader (G2P, spacy/blis YOK), sounddevice.
"""

from __future__ import annotations

import queue
import re
import threading
from typing import Callable, Iterable

import numpy as np
import sounddevice as sd

from config import (
    KOKORO_MODEL_PATH, KOKORO_VOICES_PATH,
    KOKORO_VOICE, KOKORO_LANG, KOKORO_SPEED,
)

# Cümle sınırı — TTS'e parça parça beslemek için (latency düşür).
_SENTENCE_RE = re.compile(r"[^.!?…\n]+[.!?…]*", re.UNICODE)

# espeak emoji/sembolleri "exo exo" gibi artefakta çevirir → TTS öncesi temizle.
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"  # emoji, pictographs, symbols
    "\U00002600-\U000027BF"  # misc symbols + dingbats
    "\U00002190-\U000021FF"  # arrows
    "\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U00002000-\U0000206F"  # genel noktalama (•, —, ‹›, vb. bir kısmı)
    "]+",
    flags=re.UNICODE,
)
_MD_RE = re.compile(r"[*_`#>|~\[\]]+")          # markdown sembolleri
_BULLET_RE = re.compile(r"(?m)^\s*[-•·●▪*]\s+")  # satır başı madde imleri


def clean_for_tts(text: str) -> str:
    """Sesli okunacak metni temizler: emoji, markdown, madde imi, fazla boşluk."""
    text = text or ""
    text = _EMOJI_RE.sub(" ", text)
    text = _BULLET_RE.sub("", text)
    text = _MD_RE.sub(" ", text)
    text = text.replace("\n", ". ")
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"(\.\s*){2,}", ". ", text)  # üst üste binen noktaları sadeleştir
    return text.strip()


def split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [m.group(0).strip() for m in _SENTENCE_RE.finditer(text)]
    return [p for p in parts if p]


class KokoroTTS:
    """Lazy-loaded Kokoro sentezleyici. Thread-safe sentez (tek lock)."""

    def __init__(self) -> None:
        self._kokoro = None
        self._sr = 24000
        self._lock = threading.Lock()

    # ─── Yükleme ────────────────────────────────────────────────────
    def _ensure_loaded(self) -> None:
        if self._kokoro is not None:
            return
        with self._lock:
            if self._kokoro is not None:
                return
            import espeakng_loader
            from kokoro_onnx import Kokoro, EspeakConfig
            esp = EspeakConfig(
                lib_path=espeakng_loader.get_library_path(),
                data_path=espeakng_loader.get_data_path(),
            )
            self._kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH, espeak_config=esp)

    def warmup(self) -> None:
        """Model + espeak'i önceden yükle (ilk cevapta gecikme olmasın)."""
        self._ensure_loaded()

    @property
    def ready(self) -> bool:
        return self._kokoro is not None

    # ─── Sentez ─────────────────────────────────────────────────────
    def synth(self, text: str) -> tuple[np.ndarray, int]:
        """Metni tek parça sentezler → (float32 samples, sample_rate)."""
        self._ensure_loaded()
        with self._lock:
            samples, sr = self._kokoro.create(
                text, voice=KOKORO_VOICE, speed=KOKORO_SPEED, lang=KOKORO_LANG,
            )
        self._sr = sr
        return samples, sr

    # ─── Çalma (cümle cümle look-ahead) ─────────────────────────────
    def speak(self, text: str, should_stop: Callable[[], bool] | None = None) -> None:
        """Metni cümlelere bölüp sı, çalarken bir sonrakini sentezler.

        should_stop() True olursa cümle sınırında durur (barge-in için)."""
        sentences = split_sentences(clean_for_tts(text))
        if not sentences:
            return
        self.speak_sentences(sentences, should_stop=should_stop)

    def speak_sentences(self, sentences: Iterable[str],
                        should_stop: Callable[[], bool] | None = None) -> None:
        stop = should_stop or (lambda: False)
        # Üretici thread bir sonraki cümleyi sentezlerken tüketici (bu thread) çalar.
        q: queue.Queue = queue.Queue(maxsize=2)
        SENTINEL = object()

        def _producer():
            try:
                for s in sentences:
                    if stop():
                        break
                    samples, sr = self.synth(s)
                    q.put((samples, sr))
            except Exception as e:  # sentez hatası tüketiciyi düşürmesin
                q.put(("__error__", str(e)))
            finally:
                q.put(SENTINEL)

        t = threading.Thread(target=_producer, daemon=True)
        t.start()
        try:
            while True:
                item = q.get()
                if item is SENTINEL:
                    break
                samples, sr = item
                if isinstance(samples, str):  # ("__error__", msg)
                    raise RuntimeError(f"Kokoro sentez hatası: {sr}")
                if stop():
                    break
                sd.play(samples, sr)
                sd.wait()
        finally:
            t.join(timeout=0.1)

    def stop_playback(self) -> None:
        """Anlık çalmayı kes (barge-in)."""
        try:
            sd.stop()
        except Exception:
            pass


# Tekil instance — local_voice buradan kullanır.
tts = KokoroTTS()
