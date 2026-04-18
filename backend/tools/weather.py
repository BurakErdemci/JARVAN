"""Hızlı hava durumu servisi (wttr.in) — Saniyeler içinde net derece ve açıklama döndürür."""
import requests
import urllib.parse

def get_weather(location: str) -> dict:
    loc = (location or "").strip()
    if not loc:
        return {"ok": False, "error": "Konum belirtilmedi"}
    
    try:
        url = f"https://wttr.in/{urllib.parse.quote(loc)}?format=j1"
        resp = requests.get(url, timeout=4)
        
        if resp.status_code != 200:
             return {"ok": False, "error": f"Hava durumu servisi hata verdi: {resp.status_code}"}
        
        data = resp.json()
        current = data.get("current_condition", [{}])[0]
        
        if not current:
            return {"ok": False, "error": "Veri okunamadı."}
            
        temp = current.get("temp_C", "?")
        feels = current.get("FeelsLikeC", "?")
        desc = current.get("lang_tr", [{}])[0].get("value")
        if not desc:
            desc = current.get("weatherDesc", [{}])[0].get("value", "")
            
        weather_list = data.get("weather", [])
        tomorrow_info = ""
        if len(weather_list) > 1:
            tomorrow = weather_list[1]
            t_max = tomorrow.get("maxtempC", "?")
            t_min = tomorrow.get("mintempC", "?")
            tomorrow_info = f"Yarın ise en yüksek {t_max}°C, en düşük {t_min}°C bekleniyor."
        
        summary = f"{loc} için anlık hava: {temp}°C (Hissedilen: {feels}°C), Durum: {desc}. {tomorrow_info}"
        
        return {"ok": True, "weather": summary}
        
    except Exception as e:
        return {"ok": False, "error": f"Hava durumu çekilemedi: {str(e)}"}
