import pyaudio
import numpy as np
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_CHUNK_MS,
    VAD_GATE_SPEECH_THRESHOLD,
    VAD_GATE_HANGOVER_MS,
    VAD_GATE_FINALIZE_SILENCE_MS,
)

CHUNK = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)  # 480 sample @ 16kHz


class VADGate:
    """
    Silero VAD tabanlı konuşma tespit kapısı.
    State machine: SILENCE → SPEECH → HANGOVER → SILENCE
    """

    def __init__(self):
        from silero_vad import load_silero_vad
        self.model = load_silero_vad()
        self.state = "SILENCE"
        self._hangover_ms = 0
        self._silence_ms = 0

    def process_chunk(self, pcm_bytes: bytes) -> str:
        """
        Bir chunk PCM bytes alır, state döner: 'SILENCE' | 'SPEECH' | 'FINALIZE'
        FINALIZE → cümle bitti, transkripsiyon başlatılabilir.
        """
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        tensor = __import__("torch").tensor(audio)
        prob = self.model(tensor, AUDIO_SAMPLE_RATE).item()

        is_speech = prob >= VAD_GATE_SPEECH_THRESHOLD

        if self.state == "SILENCE":
            if is_speech:
                self.state = "SPEECH"
                self._hangover_ms = 0
                self._silence_ms = 0

        elif self.state == "SPEECH":
            if not is_speech:
                self.state = "HANGOVER"
                self._hangover_ms = 0

        elif self.state == "HANGOVER":
            if is_speech:
                self.state = "SPEECH"
                self._hangover_ms = 0
            else:
                self._hangover_ms += AUDIO_CHUNK_MS
                if self._hangover_ms >= VAD_GATE_HANGOVER_MS:
                    self.state = "SILENCE"
                    return "FINALIZE"

        return self.state

    def reset(self):
        self.state = "SILENCE"
        self._hangover_ms = 0
        self._silence_ms = 0


def test_vad():
    """Mikrofondan canlı VAD testi — Ctrl+C ile durdur."""
    print("VAD testi başlıyor... Konuş, dur, tekrar konuş. Ctrl+C ile çık.\n")

    gate = VADGate()
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=AUDIO_CHANNELS,
        rate=AUDIO_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    last_state = None
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            result = gate.process_chunk(data)

            if result == "FINALIZE":
                print("[FINALIZE] Cümle bitti → transkripsiyon tetiklenebilir")
                gate.reset()
            elif result != last_state:
                print(f"[{result}]")
                last_state = result

    except KeyboardInterrupt:
        print("\nDurduruldu.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    test_vad()
