import os
import logging
import asyncio
from typing import List, Optional
from google import genai
from ai.memory_core import get_memory_core
from config import GEMINI_API_KEY

logger = logging.getLogger("jarvan.insight")

INSIGHT_PROMPT = """
Aşağıdaki konuşma dökümünü analiz et ve kullanıcı (Burak) hakkında KESİNLİKLE UNUTULMAMASI GEREKEN önemli içgörüleri çıkar.
Sadece şu kategorilerdeki bilgileri ayıkla:
- Kullanıcı tercihleri ve alışkanlıkları (örn: "Şekersiz americano içer")
- Proje detayları ve hedefler (örn: "JARVAN'ı dünyanın en zeki asistanı yapmayı hedefliyor")
- Kişisel önemli bilgiler (örn: "Eskişehir'de yaşıyor")
- JARVAN'a verilen özel talimatlar (örn: "Kod çıktılarını dosya olarak masaüstüne kaydet")

Kurallar:
- Eğer kaydedilmeye değer somut bir bilgi YOKSA, kesinlikle hiçbir şey yazma. Tamamen boş döndür.
- Asla "Boş", "Yok", kategori başlıkları veya açıklama yazma.
- Her satıra yalnızca bir içgörü cümlesi yaz. Numara, tire veya etiket ekleme.
- "Kullanıcı dedi ki..." yerine doğrudan içgörü cümlesi yaz.

Konuşma Dökümü:
---
{transcript}
---
İçgörüler:
"""

# Kaydedilmemesi gereken gürültü kalıpları
_NOISE_PATTERNS = [
    "(boş)", "boş)", ": (boş", "yok)", ": yok",
    "çıkarılan içgörüler", "içgörüler:", "kategori",
    "konuşma dökümü", "---",
]

class InsightAgent:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.memory = get_memory_core()

    async def process_session(self, transcript: str):
        """
        Bir konuşma dökümünü analiz eder ve yeni içgörüleri otonom olarak kaydeder.
        """
        if not transcript or len(transcript) < 50:
            return

        # 503 Hatalarına karşı retry döngüsü (Kota sorunu değil, anlık yoğunluk için)
        max_retries = 3
        retry_delay = 2  # saniye

        for attempt in range(max_retries):
            try:
                # 1. İçgörüleri LLM ile ayıkla (3.1-flash-lite: Hızlı ve otonom dostu)
                response = self.client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=INSIGHT_PROMPT.format(transcript=transcript)
                )
                
                raw_insights = (response.text or "").strip().split("\n")

                for insight in raw_insights:
                    # Markdown temizliği (numara, tire, yıldız, boşluk)
                    insight = insight.strip()
                    insight = insight.lstrip("0123456789.-* ").strip()
                    if not insight or len(insight) < 10:
                        continue

                    # Gürültü filtresi — prompt şablonu veya boş kategori kaçtıysa at
                    lower = insight.lower()
                    if any(pat in lower for pat in _NOISE_PATTERNS):
                        continue

                    # 2. Mükerrer (Deduplication) Kontrolü
                    is_new = await self._is_new_insight(insight)
                    if is_new:
                        # 3. Otonom Kayıt
                        self.memory.save_insight(insight, type="autonomous_learning")
                        logger.info(f"Yeni içgörü kaydedildi: {insight}")
                
                # Başarılı olursa döngüden çık
                break

            except Exception as e:
                # Sadece geçici yoğunluk (503) hatalarında bekle ve tekrar dene
                if "503" in str(e) and attempt < max_retries - 1:
                    print(f"DEBUG: Google geçici yoğunluk (503), {retry_delay}sn sonra tekrar deneniyor... (Deneme {attempt+1})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Üssel bekleme
                else:
                    logger.error(f"Insight Agent hatası: {e}")
                    break

    async def _is_new_insight(self, insight: str, threshold: float = 0.85) -> bool:
        """
        Bu içgörü zaten hafızada benzer bir şekilde var mı kontrol eder.
        """
        similar_memories = self.memory.query(insight, n_results=3)
        if not similar_memories:
            return True
            
        for mem in similar_memories:
            if insight.lower() in mem.lower() or mem.lower() in insight.lower():
                return False
        return True

# Singleton
_insight_agent = None

def get_insight_agent() -> InsightAgent:
    global _insight_agent
    if _insight_agent is None:
        _insight_agent = InsightAgent()
    return _insight_agent
