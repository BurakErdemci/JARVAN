import subprocess
import platform
from typing import Dict, Any


def open_url(url: str) -> Dict[str, Any]:
    """Varsayılan tarayıcıda URL açar."""
    if not url:
        return {"ok": False, "error": "URL boş"}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["start", url], shell=True)
        return {"ok": True, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}
