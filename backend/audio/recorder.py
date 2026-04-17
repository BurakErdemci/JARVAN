import pyaudio
import wave
import tempfile
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_MS

CHUNK = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)  # 30ms chunk = 480 sample


def list_microphones():
    p = pyaudio.PyAudio()
    print("Mevcut mikrofonlar:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            print(f"  [{i}] {info['name']}")
    p.terminate()


def record_seconds(duration: int = 3) -> bytes:
    """Belirtilen süre kadar mikrofon kaydı alır, ham PCM bytes döner."""
    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=AUDIO_CHANNELS,
        rate=AUDIO_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    print(f"Kayıt başlıyor ({duration} saniye)... Konuş!")
    frames = []
    total_chunks = int(AUDIO_SAMPLE_RATE / CHUNK * duration)

    for _ in range(total_chunks):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    print("Kayıt bitti.")
    stream.stop_stream()
    stream.close()
    p.terminate()

    return b"".join(frames)


def play_audio(pcm_data: bytes):
    """Ham PCM bytes'ı hoparlörden oynatır."""
    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=AUDIO_CHANNELS,
        rate=AUDIO_SAMPLE_RATE,
        output=True,
    )

    print("Geri oynatılıyor...")
    stream.write(pcm_data)
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Bitti.")


def save_wav(pcm_data: bytes, path: str):
    """PCM bytes'ı WAV dosyasına kaydeder."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(2)  # paInt16 = 2 byte
        wf.setframerate(AUDIO_SAMPLE_RATE)
        wf.writeframes(pcm_data)


if __name__ == "__main__":
    list_microphones()
    print()
    audio = record_seconds(3)
    play_audio(audio)
