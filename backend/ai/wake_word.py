import json
import os
from vosk import Model, KaldiRecognizer


class WakeWordEngine:
    """Hafif uyandırma kelimesi tespiti (Vosk). Grammar ile sadece wake word'e
    odaklanır → yanlış tetik az. Wake word + model dili config'den gelir
    (varsayılan: 'wake up' + İngilizce model)."""

    def __init__(self, model_path: str, sample_rate: int = 16000, wake_word: str = "wake up"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Vosk model path not found: {model_path}")

        self.model = Model(model_path)
        self.wake_word = (wake_word or "wake up").lower().strip()
        # Grammar'a wake word (çok kelimeli olabilir) + [unk] (bilinmeyen sesler).
        self.grammar = json.dumps([self.wake_word, "[unk]"])
        self.rec = KaldiRecognizer(self.model, sample_rate, self.grammar)
        self.sample_rate = sample_rate
        # Çok kelimeli wake word'de tek kelime yakalansa da tetikle (örn. "wake")
        self._first_word = self.wake_word.split()[0] if self.wake_word else ""

    def process_data(self, data: bytes) -> str | None:
        """Ses verisini işler; wake word yakalanırsa onu döner, yoksa None."""
        if self.rec.AcceptWaveform(data):
            res = json.loads(self.rec.Result())
            text = (res.get("text") or "").lower()
            if self.wake_word in text or (self._first_word and self._first_word in text.split()):
                return self.wake_word
        return None


if __name__ == "__main__":
    import pyaudio
    try:
        engine = WakeWordEngine("models/vosk-en-small", wake_word="wake up")
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4000)
        print(f"Dinleniyor... ('{engine.wake_word}' demeyi dene)")
        while True:
            data = stream.read(4000, exception_on_overflow=False)
            result = engine.process_data(data)
            if result:
                print(f"Yakalandı: {result}")
    except Exception as e:
        print(f"Hata: {e}")
