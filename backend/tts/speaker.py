import asyncio
import tempfile
import os
import edge_tts
import sounddevice as sd
import numpy as np
from pydub import AudioSegment

VOICE = "tr-TR-EmelNeural"


async def _generate_speech(text: str) -> str:
    """Edge TTS ile metni MP3'e çevirir, dosya yolunu döner."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(tmp.name)
    return tmp.name


def speak(text: str):
    """Metni seslendirir ve hoparlörden oynatır."""
    mp3_path = asyncio.run(_generate_speech(text))

    try:
        audio = AudioSegment.from_mp3(mp3_path)
        samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
        sd.play(samples, samplerate=audio.frame_rate)
        sd.wait()
    finally:
        os.unlink(mp3_path)


if __name__ == "__main__":
    text = input("Test cümlesi: ") or "Merhaba, ben Jarvan. Seni duyabiliyorum ve ekranını görebiliyorum."
    print("Seslendiriliyor...")
    speak(text)
    print("Bitti.")
