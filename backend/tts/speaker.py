import asyncio
import tempfile
import os
import edge_tts
import pygame

VOICE = "tr-TR-EmelNeural"


async def _generate_speech(text: str) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(tmp.name)
    return tmp.name


def speak(text: str):
    mp3_path = asyncio.run(_generate_speech(text))
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(mp3_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    finally:
        pygame.mixer.quit()
        os.unlink(mp3_path)


if __name__ == "__main__":
    text = input("Test cümlesi: ") or "Merhaba, ben Jarvan. Seni duyabiliyorum ve ekranını görebiliyorum."
    print("Seslendiriliyor...")
    speak(text)
    print("Bitti.")
