import os
import httpx
import json
from datetime import datetime
from typing import Dict, Any

async def get_tavily_data(query: str, max_results: int = 5) -> str:
    """
    Tavily API üzerinden sessizce (tarayıcı açmadan) internet verisi toplar.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Hata: TAVILY_API_KEY bulunamadı."
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": True,
                },
                timeout=15.0,
            )
            r.raise_for_status()
            data = r.json()
            
            results_text = []
            if data.get("answer"):
                results_text.append(f"Özet Bilgi: {data['answer']}\n")
            
            for item in data.get("results", []):
                results_text.append(f"Başlık: {item.get('title')}\nURL: {item.get('url')}\nİçerik: {item.get('content')}\n")
            
            return "\n---\n".join(results_text)
    except Exception as e:
        return f"İnternet taraması sırasında hata oluştu: {str(e)}"

async def deep_research(query: str) -> str:
    """
    OpenRouter üzerinden Kimi k2.6 modelini kullanarak derinlemesine internet araştırması yapar.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Hata: OPENROUTER_API_KEY bulunamadı. Lütfen .env dosyasına ekleyin."

    try:
        current_date = datetime.now().strftime("%d %B %Y")
        print(f"[Jarvan] İnternet verileri toplanıyor: {query}")
        # 1. Önce internetten güncel bilgileri sessizce topla
        search_results = await get_tavily_data(query)
        
        # 2. Toplanan verileri Gelişmiş Analiz motoruna gönder
        prompt = f"""
Bugünün Tarihi: {current_date}
Soru: {query}

Veriler:
{search_results}

Analiz Hedefi:
- Lütfen doğrudan tabloya ve stratejik karara odaklan.
- Gereksiz giriş ve kapanış cümleleri kurmadan, veriyi Markdown formatında sun.
- 1. Karşılaştırma Tablosu (Fiyat, Saat, Bagaj, Havayolu).
- 2. Stratejik Karar (Hangi bilet en mantıklı ve neden? - Maks 2 cümle).
"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://jarvan.ai",
            "X-Title": "JARVAN AI",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "moonshotai/kimi-k2.6",
            "messages": [
                {"role": "system", "content": "Sen JARVAN'ın profesyonel analiz modülüsün. Stratejik ve veri odaklı raporlar hazırlarsın."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 16384, # Kimi'nin düşünmesi için tam kapasite
            "include_reasoning": True # Eğer sağlayıcı destekliyorsa akıl yürütmeyi de al
        }

        async with httpx.AsyncClient() as client:
            print(f"[Jarvan] Analiz ediliyor (Bu işlem Kimi'nin derin düşünmesi nedeniyle 1-2 dk sürebilir)...")
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=300.0 # 5 dakika tam kapasite
            )
            
            if response.status_code != 200:
                print(f"[OpenRouter] HATA: {response.status_code} - {response.text}")
                return f"Hata: Analiz motoru (Kod: {response.status_code})"
            
            result = response.json()
            choice = result.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content")
            reasoning = message.get("reasoning_content") or message.get("reasoning")
            
            # Eğer içerik boş ama düşünce varsa, düşünceyi içerik yap
            final_result = content or reasoning
            
            if not final_result:
                print(f"[Jarvan] HATA: Kimi tamamen boş döndü. Yanıt: {json.dumps(result)}")
                return "Hata: Analiz motoru bir sonuç üretemedi. Lütfen tekrar deneyin."
                
            print(f"[Jarvan] Analiz başarıyla tamamlandı.")
            return final_result

    except Exception as e:
        print(f"[Jarvan] HATA: {str(e)}")
        return f"Hata: {str(e)}"
