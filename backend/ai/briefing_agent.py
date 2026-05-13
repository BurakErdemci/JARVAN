import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
from google import genai

from config import GEMINI_API_KEY, TAVILY_API_KEY

logger = logging.getLogger("jarvan.briefing")

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEFING_STATE_PATH = os.path.join(_BASE, "data", "briefing_state.json")

MIN_HOURS_BETWEEN_BRIEFINGS = 4

INTEREST_QUERIES = [
    "artificial intelligence AI breakthrough news today",
    "video game gaming news release announcement today",
    "software developer tools programming news today",
]


class BriefingAgent:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self._state = self._load_state()
        self._cached: Optional[str] = None   # hazır brifing
        self._prefetch_done: bool = False     # fetch tamamlandı mı

    def _load_state(self) -> dict:
        try:
            with open(BRIEFING_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_briefing": None, "seen_hashes": []}

    def _save_state(self):
        os.makedirs(os.path.dirname(BRIEFING_STATE_PATH), exist_ok=True)
        with open(BRIEFING_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def _should_brief(self) -> bool:
        last = self._state.get("last_briefing")
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
            return datetime.now() - last_dt > timedelta(hours=MIN_HOURS_BETWEEN_BRIEFINGS)
        except Exception:
            return True

    def _is_seen(self, title: str) -> bool:
        h = hashlib.md5(title.lower().strip().encode()).hexdigest()
        return h in self._state.get("seen_hashes", [])

    def _mark_seen(self, titles: list):
        seen = self._state.get("seen_hashes", [])
        for title in titles:
            h = hashlib.md5(title.lower().strip().encode()).hexdigest()
            if h not in seen:
                seen.append(h)
        self._state["seen_hashes"] = seen[-500:]
        self._state["last_briefing"] = datetime.now().isoformat()
        self._save_state()

    async def _fetch_news(self) -> list:
        if not TAVILY_API_KEY:
            logger.warning("TAVILY_API_KEY yok, briefing atlanıyor.")
            return []

        results = []
        async with httpx.AsyncClient(timeout=15) as client:
            for query in INTEREST_QUERIES:
                try:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": TAVILY_API_KEY,
                            "query": query,
                            "topic": "news",
                            "max_results": 5,
                            "days": 1,
                        }
                    )
                    if resp.status_code == 200:
                        results.extend(resp.json().get("results", []))
                except Exception as e:
                    logger.warning(f"Tavily hata ({query}): {e}")

        return results

    async def _evaluate(self, news_items: list) -> Optional[str]:
        # Görülmeyenleri al, deduplicate et
        new_items = [i for i in news_items if not self._is_seen(i.get("title", ""))]
        seen_titles: set = set()
        unique = []
        for item in new_items:
            key = item.get("title", "").lower()[:60]
            if key not in seen_titles:
                seen_titles.add(key)
                unique.append(item)

        if not unique:
            logger.debug("Yeni haber yok, briefing atlanıyor.")
            return None

        news_text = "\n".join(
            f"- {item.get('title', '')} [{item.get('url', '')[:50]}]"
            for item in unique[:15]
        )

        prompt = (
            "Aşağıdaki haberlerden Burak için gerçekten dikkat çekici olanları seç.\n\n"
            "ÖNCELİK SIRASI:\n"
            "1. Yapay zeka / AI — yeni model, araştırma kırılımı, önemli duyuru (EN ÖNEMLİ)\n"
            "2. Oyun dünyası — büyük çıkış, önemli duyuru (sadece gerçekten dikkat çekiciyse)\n"
            "3. Yazılım/geliştirici araçları — yeni framework, önemli update (sadece gerçekten dikkat çekiciyse)\n\n"
            f"Haberler:\n{news_text}\n\n"
            "Kurallar:\n"
            "- Gerçekten önemli olanları seç, max 3 madde. Sıradan haberleri ATLA.\n"
            "- Hiçbiri gerçekten dikkat çekici değilse sadece 'YOK' yaz.\n"
            "- Türkçe, doğal konuşma diliyle yaz.\n"
            "- Giriş: 'Bu arada şunu söyleyeyim:' veya 'Açılırken dikkatimi çeken bir şey var:'\n"
            "- Her madde 1 cümle. Kaynak adını doğal söyle ('TechCrunch'a göre' gibi).\n\n"
            "Cevap:"
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=prompt
            )
            result = (response.text or "").strip()
            if not result or result.upper() == "YOK":
                return None

            self._mark_seen([i.get("title", "") for i in unique[:15]])
            return result

        except Exception as e:
            logger.error(f"Briefing değerlendirme hatası: {e}")
            return None

    async def prefetch(self) -> None:
        """Session açılınca arka planda çağrılır. Brifing hazırlanır, cache'e yazılır."""
        if not self._should_brief():
            logger.debug("Son brifingden 4 saat geçmedi, prefetch atlanıyor.")
            self._prefetch_done = True
            return

        try:
            news = await self._fetch_news()
            self._cached = await self._evaluate(news) if news else None
        except Exception as e:
            logger.error(f"Briefing prefetch hatası: {e}")
            self._cached = None
        finally:
            self._prefetch_done = True
            logger.info(f"Briefing prefetch tamamlandı. Brifing: {'var' if self._cached else 'yok'}")

    def get_cached(self) -> Optional[str]:
        """Wake word sonrası anlık döner — prefetch tamamsa cache'den, değilse None."""
        result = self._cached
        self._cached = None       # bir kez kullanılır
        self._prefetch_done = False
        return result


_agent = None

def get_briefing_agent() -> BriefingAgent:
    global _agent
    if _agent is None:
        _agent = BriefingAgent()
    return _agent
