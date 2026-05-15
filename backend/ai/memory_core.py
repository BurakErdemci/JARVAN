import chromadb
import os
from datetime import datetime
import logging
from typing import List, Dict, Any
import google.generativeai as genai
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

logger = logging.getLogger("jarvan.memory")

class CustomGoogleEmbeddingFunction(EmbeddingFunction):
    """
    ChromaDB için özel Google Generative AI Embedding fonksiyonu.
    Hazır kütüphanelerdeki versiyon çatışmalarını engeller.
    """
    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-2"):
        self.model_name = model_name
        genai.configure(api_key=api_key)

    def __call__(self, input: Documents) -> Embeddings:
        # Metinleri vektörlere çevir
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=input
            )
            
            # Google SDK'dan veriyi çekme mantığı (En Garanti Yol)
            raw_data = None
            if hasattr(result, "embeddings"):
                raw_data = result.embeddings
            elif hasattr(result, "embedding"):
                raw_data = result.embedding
            elif isinstance(result, dict):
                raw_data = result.get("embeddings") or result.get("embedding")
            
            if raw_data is None:
                logger.error(f"Hata: Veri çekilemedi. Keys: {dir(result)}")
                return []

            # Ham veriyi temizleyip Liste[Liste[float]] formatına getir
            # result.embedding bazen doğrudan ContentEmbedding nesnesi olabilir, .values ile listeye çevir
            if hasattr(raw_data, "values"):
                raw_data = raw_data.values

            # Eğer tekil bir vektör geldiyse (list değilse veya listenin ilk elemanı sayıysa)
            # Onu bir liste içine alalım
            if not isinstance(raw_data, list):
                raw_data = [raw_data]
            
            # Eğer listenin ilk elemanı sayıysa (tek bir vektör), onu List[List] yap
            if len(raw_data) > 0 and not isinstance(raw_data[0], list) and not hasattr(raw_data[0], "__iter__"):
                raw_data = [raw_data]

            # Son temizlik: Her şeyi saf float listesine çevir
            final_embeddings = []
            for item in raw_data:
                # İçerideki nesneyi (ContentEmbedding veya list) float listesine çevir
                values = item.values if hasattr(item, "values") else item
                final_embeddings.append([float(x) for x in values])
                
            return final_embeddings

        except Exception as e:
            logger.error(f"Embedding sırasında kritik hata: {e}")
            return []

class MemoryCore:
    """
    JARVAN'ın Semantik Hafıza Çekirdeği (ChromaDB tabanlı).
    Anıları ve içgörüleri zaman damgalı olarak vektör tabanında saklar.
    """
    def __init__(self, db_path: str = "./data/chroma"):
        # MEMORY_READ_ONLY=1 → Windows gibi ikincil cihazlarda yazma engellenir,
        # okuma normal PersistentClient üzerinden yapılır (Syncthing sync'ten faydalanır).
        self._read_only = os.getenv("MEMORY_READ_ONLY", "0") == "1"

        if not os.path.exists(db_path):
            os.makedirs(db_path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=db_path)
        if self._read_only:
            logger.info("[memory] Read-only mod aktif — hafiza yazma devre disi.")
        
        # API anahtarını al
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY bulunamadı!")
            
        # Özel embedding fonksiyonumuzu bağla
        self.ef = CustomGoogleEmbeddingFunction(api_key=api_key)
        
        # Koleksiyonu al veya oluştur
        self.collection = self.client.get_or_create_collection(
            name="jarvan_behavioral_memory",
            embedding_function=self.ef,
            metadata={"description": "JARVAN'ın kullanıcı davranış ve içgörü hafızası"}
        )

    def save_insight(self, text: str, type: str = "behavioral") -> str:
        """
        Yeni bir içgörü veya anı kaydeder. Otomatik zaman damgası ekler.
        Read-only modda (ikincil cihaz) sessizce pas geçer.
        """
        if self._read_only:
            logger.debug("[memory] Read-only: save_insight atlandi.")
            return "read_only"
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
        insight_id = f"insight_{now.timestamp()}"
        
        # Bilgiyi zaman damgasıyla birleştirerek kaydet
        contextual_text = f"[{timestamp_str}] {text}"
        
        metadata = {
            "timestamp": timestamp_str,
            "type": type,
            "day": now.strftime("%A"),
            "year": now.year
        }
        
        self.collection.add(
            documents=[contextual_text],
            metadatas=[metadata],
            ids=[insight_id]
        )
        logger.info(f"Hafıza kaydedildi: {text[:50]}...")
        return insight_id

    def query(self, context: str, n_results: int = 5) -> List[str]:
        """
        Verilen bağlama (context) göre en alakalı hafızaları getirir.
        """
        try:
            results = self.collection.query(
                query_texts=[context],
                n_results=n_results
            )
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            logger.error(f"Hafıza sorgulama hatası: {e}")
            return []

    def export_all(self) -> List[Dict[str, Any]]:
        """Tüm hafızaları dışa aktarır — sync için kullanılır."""
        try:
            result = self.collection.get(include=["documents", "metadatas", "embeddings"])
            records = []
            for i, doc_id in enumerate(result["ids"]):
                records.append({
                    "id": doc_id,
                    "document": result["documents"][i],
                    "metadata": result["metadatas"][i],
                })
            return records
        except Exception as e:
            logger.error(f"Export hatası: {e}")
            return []

    def import_insights(self, records: List[Dict[str, Any]], source: str = "sync") -> int:
        """Dışarıdan gelen hafızaları import eder, zaten varsa atlar."""
        imported = 0
        for r in records:
            try:
                doc_id = f"{r['id']}_{source}"
                existing = self.collection.get(ids=[doc_id])
                if existing["ids"]:
                    continue
                self.collection.add(
                    documents=[r["document"]],
                    metadatas=[{**r.get("metadata", {}), "source": source}],
                    ids=[doc_id],
                )
                imported += 1
            except Exception as e:
                logger.debug(f"Import atlandı ({r.get('id')}): {e}")
        if imported:
            logger.info(f"[memory] {imported} hafıza import edildi (kaynak: {source})")
        return imported

    def get_all_embeddings(self) -> Dict[str, Any]:
        """Deduplikasyon için tüm kayıtları embedding'leriyle döner."""
        try:
            return self.collection.get(include=["documents", "metadatas", "embeddings"])
        except Exception as e:
            logger.error(f"Embedding getirme hatası: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}

    def delete_by_ids(self, ids: List[str]) -> None:
        """Belirtilen id'leri siler — deduplication sonrası kullanılır."""
        if ids:
            self.collection.delete(ids=ids)
            logger.info(f"[memory] {len(ids)} duplikat silindi.")

    def get_session_context(self) -> str:
        """
        Session başında JARVAN'ın 'bilinçaltına' enjekte edilecek özet hafızayı oluşturur.
        """
        # Genel profil ve son alışkanlıklar üzerine bir sorgu atar
        memories = self.query("kullanıcı alışkanlıkları, tercihleri ve aktif durumu", n_results=10)
        if not memories:
            return "Henüz kalıcı bir anı yok. Yeni anılar biriktirmeye hazırız."
            
        return "\n".join([f"- {m}" for m in memories])

# Singleton örneği
_memory_instance = None

def get_memory_core() -> MemoryCore:
    global _memory_instance
    if _memory_instance is None:
        _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default = os.path.join(_base, "data", "chroma")
        db_path = os.getenv("CHROMA_DB_PATH", default)
        _memory_instance = MemoryCore(db_path=db_path)
    return _memory_instance
