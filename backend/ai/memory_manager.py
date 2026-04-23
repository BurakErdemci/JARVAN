import json
import os
from pathlib import Path

class MemoryManager:
    def __init__(self, memory_file="backend/data/memory.json"):
        # Çalışma dizinine göre yolu ayarla
        base_path = Path(__file__).parent.parent
        self.memory_path = base_path / "data" / "memory.json"
        self.memory = self._load()

    def _load(self):
        if not self.memory_path.exists():
            return {}
        try:
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Memory load error: {e}")
            return {}

    def save(self):
        try:
            os.makedirs(self.memory_path.parent, exist_ok=True)
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Memory save error: {e}")

    def get_summary_for_prompt(self) -> str:
        """Gemini sistem promptuna enjekte edilecek metni döner."""
        if not self.memory:
            return ""
        
        user = self.memory.get("user", {})
        playlists = user.get("preferences", {}).get("spotify_playlists", {})
        
        summary = "[🧠 JARVAN'IN UZUN SÜRELİ BELLEĞİ]\n"
        summary += f"Kullanıcı: {user.get('name', 'Bilinmiyor')} ({user.get('role', '')})\n"
        
        if playlists:
            summary += "\n[ÖZEL ÇALMA LİSTESİ NUMARALARI]\n"
            for num, name in playlists.items():
                summary += f"- {num}. Playlist: \"{name}\"\n"
            summary += "NOT: Kullanıcı numara verirse (örn: '1. playlisti çal') yukarıdaki gerçek ismi kullan.\n"
        
        knowledge = self.memory.get("knowledge", {})
        projects = knowledge.get("projects", [])
        if projects:
            summary += "\n[AKTİF PROJELER]\n"
            for p in projects:
                summary += f"- {p.get('name')}: {p.get('role')} ({p.get('status')})\n"
        
        return summary

    def update_insight(self, insight: str):
        """Kullanıcı hakkında yeni bir bilgi (insight) ekler."""
        if "insights" not in self.memory:
            self.memory["insights"] = []
        self.memory["insights"].append(insight)
        self.save()
