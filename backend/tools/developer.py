import os
import httpx
import json
from typing import Dict, Any, Optional
from config import OPENROUTER_API_KEY

# Model Tanımları (OpenRouter ID'leri)
ARCHITECT_MODEL = "anthropic/claude-opus-4.7"
DEVELOPER_MODEL = "openai/gpt-5.4"
SUPERVISOR_MODEL = "google/gemini-3.1-pro-preview"

# Dizin Tanımları
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLUEPRINTS_DIR = os.path.join(BASE_DIR, "blueprints")

async def _ask_openrouter(model_id: str, system_prompt: str, user_prompt: str) -> str:
    """OpenRouter üzerinden spesifik bir modele soru sorar."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code != 200:
                print(f"[OpenRouter Error] Status: {response.status_code}")
                print(f"[Error Body] {response.text}")
                response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Request Failed] Model: {model_id}, Error: {str(e)}")
        raise e

async def autonomous_develop(task: str, use_architect: bool = False, blueprint_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Claude (Architect) -> GPT (Developer) -> Gemini (Supervisor) döngüsünü yönetir.
    blueprint_name verilirse Claude'un planı kaydedilir/yüklenir.
    """
    print(f"\n[Lead Developer] Görev başlatıldı: {task}")
    
    plan = ""
    blueprint_path = None
    
    # Blueprint kontrolü ve Akıllı Eşleşme
    if blueprint_name:
        os.makedirs(BLUEPRINTS_DIR, exist_ok=True)
        
        # 1. Tam eşleşme kontrolü
        blueprint_path = os.path.join(BLUEPRINTS_DIR, f"{blueprint_name}.json")
        
        # 2. Akıllı eşleşme (Eğer tam eşleşme yoksa benzer isimlileri ara)
        if not os.path.exists(blueprint_path):
            existing_blueprints = [f.replace(".json", "") for f in os.listdir(BLUEPRINTS_DIR) if f.endswith(".json")]
            for existing in existing_blueprints:
                # Basit benzerlik kontrolü (örn: SistemTakip vs SistemTakibi)
                if blueprint_name.lower() in existing.lower() or existing.lower() in blueprint_name.lower():
                    print(f"[SmartMatch] '{blueprint_name}' yerine mevcut '{existing}' taslağı bulundu! ✅")
                    blueprint_name = existing
                    blueprint_path = os.path.join(BLUEPRINTS_DIR, f"{existing}.json")
                    break

        if os.path.exists(blueprint_path):
            with open(blueprint_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                plan = saved_data.get("plan", "")
                print(f"[Blueprint] '{blueprint_name}' taslağı dosyadan yüklendi. (Claude tasarrufu sağlandı! 💎)")

    try:
        # 1. ADIM: HASAN USTA (Architect)
        if use_architect and not plan:
            print(f"[Hasan Usta - {ARCHITECT_MODEL}] Stratejik plan hazırlanıyor (Mimarımız iş başında!)...")
            architect_prompt = f"Sen Hasan Usta'sın, Jarvan'ın emektar mimarısın. Bu karmaşık görev için mimari planı hazırla: {task}"
            plan = await _ask_openrouter(ARCHITECT_MODEL, "Teknik mimari planı hazırla.", architect_prompt)
            print(f"\n--- HASAN USTA'NIN PLANI ---\n{plan}\n--- PLAN BİTTİ ---\n")
            
            # Blueprint olarak kaydet
            if blueprint_name:
                with open(blueprint_path, "w", encoding="utf-8") as f:
                    json.dump({"task": task, "plan": plan}, f, ensure_ascii=False, indent=4)
                print(f"[Blueprint] Yeni plan '{blueprint_name}.json' olarak kaydedildi.")
        elif not plan:
            print(f"[Info] Hasan Usta bugün dinleniyor, Elliot liderliği devraldı.")

        # 2. ADIM VE DÖNGÜ: ELLIOT & JARVAN IV
        current_code = ""
        feedback = ""
        attempts = 0
        max_attempts = 2

        while attempts <= max_attempts:
            # ELLIOT (Developer)
            print(f"[Elliot - {DEVELOPER_MODEL}] Kapüşonunu çekti, kod yazıyor (Deneme {attempts + 1})...")
            dev_system = "Sen Elliot'sın, Jarvan'ın dahi yazılımcısısın. Mr. Robot tarzında, en verimli Python kodunu yaz. Sadece kod döndür."
            dev_user = f"GÖREV:\n{task}\n\nHASAN USTA'NIN PLANI (Varsa):\n{plan}\n\nJARVAN IV GERİ BİLDİRİMİ (Varsa):\n{feedback}\n\nLütfen kodu yaz."
            current_code = await _ask_openrouter(DEVELOPER_MODEL, dev_system, dev_user)
            print(f"[Elliot] Kod yazımı tamamlandı. (Boyut: {len(current_code)} karakter)")

            # JARVAN IV (Supervisor)
            print(f"[Jarvan IV - {SUPERVISOR_MODEL}] Demacia adına denetliyor...")
            sup_system = (
                "Sen Jarvan IV'sün, Demacia'nın kralı ve bu ekibin denetçisisin. Pragmatik ol. "
                "1. KRİTİK HATALAR: Syntax/Mantık hatası varsa ELEŞTİR ve 'OK' verme. "
                "2. KÜÇÜK KUSURLAR: Ufak detayları belirt ama kod güvenliyse 'OK' ver. "
                "3. ONAY: Sadece 'OK' yaz."
            )
            sup_user = f"GÖREV:\n{task}\n\nELLIOT'IN KODU:\n{current_code}\n\nKod Demacia standartlarına uygun mu?"
            review = await _ask_openrouter(SUPERVISOR_MODEL, sup_system, sup_user)

            if "OK" in review.upper() and len(review) < 15:
                print("[Jarvan IV] Kod onaylandı! Demacia için! ✅")
                break
            else:
                feedback = review
                attempts += 1
                print(f"\n--- JARVAN IV ELEŞTİRİSİ (Deneme {attempts}) ---\n{review}\n--- ELEŞTİRİ BİTTİ ---\n")
                print(f"[Jarvan IV] Kod beğenilmedi! Elliot'tan düzeltme isteniyor...")

        return {
            "ok": attempts <= max_attempts,
            "plan": plan if plan else "Blueprint/Otonom",
            "code": current_code,
            "review": review if 'review' in locals() else "N/A",
            "attempts": attempts
        }

    except Exception as e:
        print(f"[Multi-Agent Error] {str(e)}")
        return {"ok": False, "error": str(e)}

def save_report(filename: str, content: str) -> Dict[str, Any]:
    """Masaüstüne Markdown raporu kaydeder."""
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not filename.endswith(".md"): filename += ".md"
        file_path = os.path.join(desktop, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": file_path, "message": f"Başarıyla kaydedildi: {filename}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def create_project_file(file_path: str, content: str) -> Dict[str, Any]:
    """Proje dizininde dosya oluşturur."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "file": file_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}
