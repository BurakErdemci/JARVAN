import os
from typing import Dict, Any

HOME = os.path.expanduser("~")
DESKTOP = os.path.join(HOME, "Desktop")
JARVAN_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Kısa yol takma adları — model "Desktop/foo.py" veya "masaüstü/foo.py" diyebilir
_ALIASES = {
    "desktop":   DESKTOP,
    "masaüstü":  DESKTOP,
    "masaustu":  DESKTOP,
    "home":      HOME,
    "ev":        HOME,
    "jarvan":    JARVAN_DIR,
    "proje":     JARVAN_DIR,
}

def _resolve(path: str) -> str:
    """
    Verilen yolu mutlak gerçek yola çevirir.
    - Zaten mutlaksa olduğu gibi döner.
    - İlk bileşen bir takma adsa expand eder (Desktop/foo.py → ~/Desktop/foo.py).
    - Sadece dosya adıysa masaüstüne koyar.
    """
    path = path.strip()

    if os.path.isabs(path):
        return path

    parts = path.replace("\\", "/").split("/", 1)
    alias = _ALIASES.get(parts[0].lower())
    if alias:
        return os.path.join(alias, parts[1]) if len(parts) > 1 else alias

    # Sadece dosya adı (klasör yok) → masaüstü
    if len(parts) == 1:
        return os.path.join(DESKTOP, path)

    # Diğer relative path'ler → proje kökü altına
    return os.path.join(JARVAN_DIR, path)


def save_report(filename: str, content: str) -> Dict[str, Any]:
    """Masaüstüne Markdown raporu kaydeder."""
    try:
        if not filename.endswith(".md"):
            filename += ".md"
        file_path = os.path.join(DESKTOP, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": file_path, "message": f"Başarıyla kaydedildi: {filename}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_project_file(file_path: str, content: str) -> Dict[str, Any]:
    """Dosyayı belirtilen konuma kaydeder. Desktop, masaüstü, ~ gibi kısa yolları anlar."""
    try:
        resolved = _resolve(file_path)
        parent = os.path.dirname(resolved)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "file": resolved, "message": f"Kaydedildi: {resolved}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_folder(folder_path: str) -> Dict[str, Any]:
    """Klasör oluşturur. Desktop, masaüstü, ~ gibi kısa yolları anlar."""
    try:
        resolved = _resolve(folder_path)
        os.makedirs(resolved, exist_ok=True)
        return {"ok": True, "path": resolved, "message": f"Klasör oluşturuldu: {resolved}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
