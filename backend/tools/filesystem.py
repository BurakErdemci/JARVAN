"""Dosya sistemi araçları — arama, okuma, listeleme."""
import os
import platform
from pathlib import Path
from typing import Optional

IS_WIN = platform.system() == "Windows"
HOME = Path.home()

def _get_desktop() -> Path:
    """OneDrive gibi redirected desktop'ları da doğru bulur."""
    if IS_WIN:
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.shell32.SHGetFolderPathW(0, 0x0010, 0, 0, buf)
            if buf.value:
                return Path(buf.value)
        except Exception:
            pass
    return HOME / "Desktop"

DESKTOP = _get_desktop()

# Kısa takma adlar → tam yol
_ALIASES = {
    "masaüstü": DESKTOP,
    "masaustu": DESKTOP,
    "desktop": DESKTOP,
    "belgeler": HOME / "Documents",
    "documents": HOME / "Documents",
    "indirmeler": HOME / "Downloads",
    "downloads": HOME / "Downloads",
    "resimler": HOME / "Pictures",
    "pictures": HOME / "Pictures",
    "müzik": HOME / "Music",
    "music": HOME / "Music",
    "videolar": HOME / "Videos",
    "videos": HOME / "Videos",
    "jarvan": Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).parent,
}


def resolve_path(raw: str) -> Path:
    """
    Kullanıcının söylediği yolu tam Path'e çevirir.
    'masaüstü/rapor.pdf', '~/Downloads/x.zip', 'C:/...' hepsini anlar.
    """
    raw = raw.strip().replace("\\", "/")

    # Takma ad kontrolü (ilk segment)
    parts = raw.split("/", 1)
    alias = parts[0].lower()
    if alias in _ALIASES:
        rest = parts[1] if len(parts) > 1 else ""
        base = _ALIASES[alias]
        return (base / rest) if rest else base

    p = Path(raw).expanduser()
    if p.is_absolute():
        return p
    # Göreceli yol → önce masaüstünde, yoksa home'da ara
    for base in [DESKTOP, HOME / "Documents", HOME / "Downloads", HOME]:
        candidate = base / p
        if candidate.exists():
            return candidate
    return p  # bulunamazsa olduğu gibi döndür


def find_file(name: str, search_in: Optional[str] = None) -> dict:
    """
    Dosya/klasör adına göre arama yapar.
    search_in verilmezse Desktop, Documents, Downloads, Home'da arar.
    """
    search_root = resolve_path(search_in) if search_in else None
    search_dirs = [search_root] if search_root else [
        DESKTOP, HOME / "Documents", HOME / "Downloads", HOME / "Pictures", HOME
    ]

    found = []
    name_lower = name.lower()

    for d in search_dirs:
        if not d.exists():
            continue
        try:
            for item in d.rglob("*"):
                if name_lower in item.name.lower():
                    found.append({
                        "path": str(item),
                        "name": item.name,
                        "type": "folder" if item.is_dir() else "file",
                        "size_kb": item.stat().st_size // 1024 if item.is_file() else None,
                    })
                    if len(found) >= 20:
                        break
        except PermissionError:
            continue
        if len(found) >= 20:
            break

    if not found:
        return {"ok": False, "error": f"'{name}' bulunamadı."}
    return {"ok": True, "count": len(found), "files": found}


def read_file(path: str, max_chars: int = 4000) -> dict:
    """
    Metin dosyasını okur. PDF, kod, markdown, txt vb.
    max_chars: çok büyük dosyalarda ilk N karakter döner.
    """
    p = resolve_path(path)
    if not p.exists():
        return {"ok": False, "error": f"Dosya bulunamadı: {p}"}
    if p.is_dir():
        return {"ok": False, "error": f"Bu bir klasör, dosya değil: {p}"}

    suffix = p.suffix.lower()

    # PDF
    if suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(p))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            truncated = len(text) > max_chars
            return {
                "ok": True,
                "path": str(p),
                "content": text[:max_chars],
                "truncated": truncated,
                "pages": doc.page_count if not doc.is_closed else None,
            }
        except ImportError:
            return {"ok": False, "error": "PDF okuma için PyMuPDF gerekli: pip install pymupdf"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # Metin dosyası
    text_types = {
        ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
        ".html", ".css", ".csv", ".xml", ".toml", ".ini", ".env",
        ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".swift",
    }
    if suffix in text_types or suffix == "":
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_chars
            return {
                "ok": True,
                "path": str(p),
                "content": content[:max_chars],
                "truncated": truncated,
                "total_chars": len(content),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {"ok": False, "error": f"Desteklenmeyen dosya türü: {suffix}. Metin veya PDF olmalı."}


_DENY_NAMES = {"authorized_keys", "known_hosts", ".netrc", ".npmrc"}


def _edit_deny_reason(p: Path) -> Optional[str]:
    """LLM'in yazmaması gereken hedefler: anahtar/kimlik dosyaları, sistem ve
    başlangıç klasörleri, .ssh/.git/.venv içi. Symlink hilesine karşı realpath."""
    try:
        rp = Path(os.path.realpath(p))
    except OSError:
        rp = p
    name = rp.name.lower()
    if name in _DENY_NAMES or name.startswith("id_") or rp.suffix.lower() in (".pem", ".key"):
        return "hassas anahtar/kimlik dosyası"
    parts = {q.lower() for q in rp.parts}
    if parts & {".ssh", ".git", ".venv", "site-packages", "node_modules", "__pycache__"}:
        return "korumalı klasör"
    low = str(rp).replace("\\", "/").lower()
    for env_var in ("WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        base = os.environ.get(env_var, "")
        if base and (low + "/").startswith(base.replace("\\", "/").lower() + "/"):
            return "sistem klasörü"
    if "/start menu/programs/startup" in low or low.startswith("/etc/"):
        return "başlangıç/sistem klasörü"
    return None


def edit_file(path: str, mode: str, new_text: str, old_text: str = "") -> dict:
    """
    Metin dosyasının içeriğini değiştirir.
    mode: 'replace' (old_text → new_text), 'append' (sona ekle), 'overwrite' (tamamını yaz).
    Güvenlik: değişiklikten önce ~/.jarvan/file_backups/ altına zaman damgalı yedek alınır.
    """
    import shutil
    import time as _time

    if not (path or "").strip():
        return {"ok": False, "error": "path parametresi EKSİK. Düzenlenecek dosyanın tam "
                "yolunu ver — önce find_file/read_file ile yolu bul, sonra edit_file'ı "
                "path ile TEKRAR çağır."}
    p = resolve_path(path)
    if not p.exists():
        return {"ok": False, "error": f"Dosya bulunamadı: {p}. Önce find_file ile ara."}
    if p.is_dir():
        return {"ok": False, "error": f"Bu bir klasör, dosya değil: {p}. Klasörün İÇİNDEKİ "
                "dosyanın tam yolunu ver (list_directory ile içine bakabilirsin)."}

    _EDITABLE = {
        ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
        ".html", ".css", ".csv", ".xml", ".toml", ".ini", ".env", ".cfg", ".conf",
        ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".swift", ".sh", ".bat", ".ps1",
    }
    # Uzantısız dosyalar: serbest bırakma (authorized_keys vb. uzantısızdır) —
    # sadece bilinen zararsız isimler.
    _NOEXT_OK = {"makefile", "dockerfile", "license", "readme", "todo", "changelog",
                 "notes", ".gitignore", ".gitattributes", ".env", ".editorconfig"}
    if p.suffix.lower() not in _EDITABLE:
        if not (p.suffix == "" and p.name.lower() in _NOEXT_OK):
            return {"ok": False, "error": f"Bu tür düzenlenemez: '{p.name}'. Sadece metin dosyaları."}

    deny = _edit_deny_reason(p)
    if deny:
        return {"ok": False, "error": f"Bu dosya düzenlenemez ({deny}): {p}"}
    try:
        if p.stat().st_size > 1_000_000:
            return {"ok": False, "error": "Dosya 1 MB'den büyük — bu işi start_gemini_task ile codex'e ver."}
    except OSError as e:
        return {"ok": False, "error": str(e)}

    mode = (mode or "").strip().lower()
    if mode not in ("replace", "append", "overwrite"):
        return {"ok": False, "error": "mode 'replace', 'append' veya 'overwrite' olmalı."}

    # Yedek al
    backup_dir = HOME / ".jarvan" / "file_backups"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = _time.strftime("%Y%m%d-%H%M%S")
        backup = backup_dir / f"{p.stem}.{stamp}{p.suffix}"
        shutil.copy2(p, backup)
    except Exception as e:
        return {"ok": False, "error": f"Yedek alınamadı, düzenleme iptal: {e}"}

    try:
        if mode == "overwrite":
            p.write_text(new_text, encoding="utf-8")
        elif mode == "append":
            content = p.read_text(encoding="utf-8", errors="replace")
            sep = "" if (not content or content.endswith("\n")) else "\n"
            p.write_text(content + sep + new_text, encoding="utf-8")
        else:  # replace
            if not old_text:
                return {"ok": False, "error": "replace modunda old_text zorunlu."}
            content = p.read_text(encoding="utf-8", errors="replace")
            count = content.count(old_text)
            if count == 0:
                return {"ok": False, "error": "old_text dosyada bulunamadı. read_file ile içeriğe "
                        "bak ve old_text'i dosyadaki haliyle BİREBİR ver.",
                        "backup": str(backup)}
            content = content.replace(old_text, new_text)
            p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(p), "mode": mode,
                "replaced": count if mode == "replace" else None,
                "backup": str(backup),
                "result": f"Dosya güncellendi ({mode})."}
    except Exception as e:
        return {"ok": False, "error": f"Düzenleme hatası: {e}", "backup": str(backup)}


def list_directory(path: str = "desktop") -> dict:
    """Klasörün içindekileri listeler."""
    p = resolve_path(path)
    if not p.exists():
        return {"ok": False, "error": f"Klasör bulunamadı: {p}"}
    if not p.is_dir():
        return {"ok": False, "error": f"Bu bir dosya, klasör değil: {p}"}

    items = []
    try:
        for item in sorted(p.iterdir()):
            if item.name.startswith("."):
                continue
            items.append({
                "name": item.name,
                "type": "folder" if item.is_dir() else "file",
                "size_kb": item.stat().st_size // 1024 if item.is_file() else None,
            })
    except PermissionError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "path": str(p), "count": len(items), "items": items}
