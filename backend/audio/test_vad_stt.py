import pyaudio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_MS
from audio.vad_gate import VADGate
from audio.transcriber import Transcriber

CHUNK = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)


def main():
    transcriber = Transcriber()
    gate = VADGate()

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=AUDIO_CHANNELS,
        rate=AUDIO_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    print("\nDinleniyor... Bir şeyler söyle, dur, transkripsiyon göreceksin. Ctrl+C ile çık.\n")

    buffer = []

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            result = gate.process_chunk(data)

            if result in ("SPEECH", "HANGOVER"):
                buffer.append(data)

            if result == "FINALIZE":
                if buffer:
                    print("Transkribe ediliyor...", end=" ", flush=True)
                    audio_bytes = b"".join(buffer)
                    text = transcriber.transcribe(audio_bytes)
                    print(f'"{text}"' if text else "(boş)")
                buffer = []
                gate.reset()

    except KeyboardInterrupt:
        print("\nDurduruldu.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    main()
