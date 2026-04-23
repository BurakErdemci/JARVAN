import os
from ai.obsidian_manager import ObsidianManager

# Varsayılan Vault yolu (JarvanVault içindeki JARVAN klasörü)
DEFAULT_VAULT_PATH = "/Users/burakemreerdemci/Documents/JarvanVault/JARVAN"

# Singleton instance
_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = ObsidianManager(DEFAULT_VAULT_PATH)
    return _manager

def obsidian_manage(action: str, title: str = None, content: str = None, folder: str = None, query: str = None):
    """
    Obsidian notlarını yöneten ana araç fonksiyonu.
    """
    mgr = get_manager()
    
    try:
        if action == "create":
            if not title or not content:
                return {"ok": False, "error": "Başlık ve içerik gerekli."}
            path = mgr.create_note(title, content, folder=folder, overwrite=True)
            return {"ok": True, "message": f"'{title}' notu oluşturuldu.", "path": str(path)}
            
        elif action == "read":
            if not title:
                return {"ok": False, "error": "Okunacak notun başlığı gerekli."}
            note = mgr.read_note(title, folder=folder)
            return {"ok": True, "note": note}
            
        elif action == "search":
            if not query:
                return {"ok": False, "error": "Arama sorgusu gerekli."}
            results = mgr.search_notes(query)
            return {"ok": True, "results": results}
            
        elif action == "list":
            notes = mgr.list_notes(folder=folder)
            return {"ok": True, "notes": notes}
            
        else:
            return {"ok": False, "error": f"Geçersiz işlem: {action}"}
            
    except Exception as e:
        return {"ok": False, "error": str(e)}
