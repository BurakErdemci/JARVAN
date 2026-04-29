"""Tarayıcıda URL açma — Gizli sekmeli Windows optimize."""
import os
import subprocess
import sys
import urllib.parse
import webbrowser

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TAVILY_API_KEY

def _find_opera_gx_win() -> str | None:
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    for path in [
        os.path.join(local, r"Programs\Opera GX\opera.exe"),
        os.path.join(program_files, r"Opera GX\opera.exe"),
    ]:
        if path and os.path.exists(path):
            return path
    return None

def open_url(url: str, incognito: bool = False) -> dict:
    target = (url or "").strip()
    if not target:
        return {"ok": False, "error": "URL boş"}

    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    try:
        if incognito:
            exe = _find_opera_gx_win()
            if exe:
                subprocess.Popen([exe, "--private", target])
            else:
                # Opera GX yok — Edge InPrivate ile fallback
                subprocess.Popen(["cmd", "/c", "start", "msedge", "--inprivate", target], shell=False)
            return {"ok": True, "url": target, "incognito": True}
        else:
            opened = webbrowser.open(target, new=2)
            if not opened:
                return {"ok": False, "error": "Tarayıcı açılamadı"}
            return {"ok": True, "url": target, "incognito": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def search_web(query: str, incognito: bool = True) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "Arama sorgusu boş"}
    url = "https://www.google.com/search?q=" + urllib.parse.quote(q)
    return open_url(url, incognito=incognito)

def _tavily_search(query: str, max_results: int = 3) -> dict:
    if not TAVILY_API_KEY:
        return {"ok": False, "error": "TAVILY_API_KEY yok"}
    try:
        import httpx
        r = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": True,
            },
            timeout=15.0,
        )
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("results", [])[:max_results]:
            body = (item.get("content") or "").strip()
            if len(body) > 600:
                body = body[:597] + "..."
            results.append({
                "title": item.get("title", ""),
                "href": item.get("url", ""),
                "body": body,
            })
        return {
            "ok": True,
            "provider": "tavily",
            "answer": (data.get("answer") or "").strip(),
            "results": results,
        }
    except Exception as e:
        return {"ok": False, "error": f"Tavily başarısız: {str(e)}"}


def _ddgs_search(query: str, max_results: int = 3) -> dict:
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                for r in results:
                    if len(r.get("body", "")) > 500:
                        r["body"] = r["body"][:497] + "..."
        if not results:
            return {"ok": True, "provider": "ddgs", "results": [], "note": "Sonuç bulunamadı."}
        return {"ok": True, "provider": "ddgs", "results": results}
    except Exception as e:
        return {"ok": False, "error": f"DDGS başarısız: {str(e)}"}


def hidden_search(query: str, max_results: int = 3) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "Arama sorgusu boş"}

    if TAVILY_API_KEY:
        result = _tavily_search(q, max_results)
        if result.get("ok") and result.get("results"):
            return result

    return _ddgs_search(q, max_results)
