"""Gömülü STT — faster-whisper. Voicebox'ın /transcribe'ının yerini alır.

Mevcut config (config.py) yeniden kullanılır: WHISPER_MODEL_SIZE / WHISPER_DEVICE /
WHISPER_COMPUTE_TYPE / WHISPER_LANGUAGE. Dil boş = otomatik (TR+EN karışık giriş).
Model tek sefer yüklenir; ses int16 PCM (16kHz mono) ya da float32 ndarray olarak verilir.
"""

from __future__ import annotations

import threading

import numpy as np

from config import (
    WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE, WHISPER_CPU_THREADS, AUDIO_SAMPLE_RATE,
)


class WhisperSTT:
    def __init__(self) -> None:
        self._model = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
                cpu_threads=WHISPER_CPU_THREADS,
            )

    def warmup(self) -> None:
        """Modeli önceden yükle (ilk konuşmada gecikme olmasın)."""
        self._ensure_loaded()

    @property
    def ready(self) -> bool:
        return self._model is not None

    # ─── Transkripsiyon ─────────────────────────────────────────────
    def transcribe(self, audio: np.ndarray) -> str:
        """float32 mono ses (16kHz, [-1,1]) → metin."""
        self._ensure_loaded()
        lang = WHISPER_LANGUAGE or None  # "" → None = otomatik dil
        with self._lock:
            segments, _info = self._model.transcribe(
                audio,
                language=lang,
                beam_size=1,        # greedy — CPU'da çok daha hızlı (5 → ~2-3x hızlanma)
                vad_filter=True,    # sessizlik/gürültü segmentlerini ele
                condition_on_previous_text=False,  # turlar arası halüsinasyon kaymasını engelle
            )
            text = "".join(seg.text for seg in segments)
        return text.strip()

    def transcribe_pcm(self, pcm: bytes, sample_rate: int | None = None) -> str:
        """int16 PCM bytes (16kHz mono) → metin."""
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        # faster-whisper 16kHz bekler; config zaten 16kHz (AUDIO_SAMPLE_RATE).
        return self.transcribe(audio)


# Tekil instance — local_voice buradan kullanır.
stt = WhisperSTT()
