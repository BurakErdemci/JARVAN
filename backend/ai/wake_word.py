import json
import os
from vosk import Model, KaldiRecognizer

class WakeWordEngine:
    def __init__(self, model_path: str, sample_rate: int = 16000):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Vosk model path not found: {model_path}")
        
        self.model = Model(model_path)
        # Sadece bu kelimelere odaklan (yanlış tespiti azaltır)
        # [unk] ifadesi bilinmeyen sesler için
        # Not: 'Jarvan' kelimesi model lügatinde olmadığı için 'uyan' anahtar kelime yapıldı.
        self.grammar = '["uyan", "uyu", "kapat kendini", "[unk]"]'
        self.rec = KaldiRecognizer(self.model, sample_rate, self.grammar)
        self.sample_rate = sample_rate

    def process_data(self, data: bytes) -> str | None:
        """Ses verisini işler ve eğer 'uyan' yakalanırsa döner."""
        if self.rec.AcceptWaveform(data):
            res = json.loads(self.rec.Result())
            text = res.get("text", "").lower()
            if "uyan" in text:
                return "uyan"
            if "uyu" in text or "kapat kendini" in text:
                return text
        return None

if __name__ == "__main__":
    import pyaudio
    try:
        engine = WakeWordEngine("models/vosk-tr")
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4000)
        print("Dinleniyor... ('Uyan' demeyi dene)")
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            result = engine.process_data(data)
            if result:
                print(f"Yakalandı: {result}")
    except Exception as e:
        print(f"Hata: {e}")
