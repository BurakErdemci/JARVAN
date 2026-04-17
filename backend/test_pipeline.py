import pyaudio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_MS
from audio.vad_gate import VADGate
from audio.transcriber import Transcriber
from screen.capture import capture_screenshot_pil
from ai.router import route
from tts.speaker import speak

CHUNK = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)


def main():
    print("Whisper yükleniyor...")
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

    print("\nJarvan dinliyor... Ctrl+C ile çık.\n")

    buffer = []

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            result = gate.process_chunk(data)

            if result in ("SPEECH", "HANGOVER"):
                buffer.append(data)

            if result == "FINALIZE":
                if buffer:
                    print("Sen: ", end="", flush=True)
                    audio_bytes = b"".join(buffer)
                    transcript = transcriber.transcribe(audio_bytes)
                    print(transcript)

                    if transcript:
                        screenshot = capture_screenshot_pil()
                        provider, response = route(transcript, screenshot)
                        print(f"Jarvan [{provider}]: {response}")
                        speak(response)
                    else:
                        print("(ses anlaşılamadı, atlandı)")

                    print()

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
