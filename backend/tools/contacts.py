"""Kişi rehberi — isimden mail adresine lookup."""
import json
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONTACTS_PATH = os.path.join(_BASE, "contacts.json")
_PHONES_PATH = os.path.join(_BASE, "contacts_phones.json")
_cache: dict[str, str] | None = None
_phone_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_CONTACTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache = {k.strip().lower(): v.strip() for k, v in data.items() if isinstance(v, str)}
    except Exception:
        _cache = {}
    return _cache


def _load_phones() -> dict[str, str]:
    global _phone_cache
    if _phone_cache is not None:
        return _phone_cache
    try:
        with open(_PHONES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _phone_cache = {
            k.strip().lower(): str(v).strip().replace("+", "").replace(" ", "")
            for k, v in data.items() if isinstance(v, (str, int))
        }
    except Exception:
        _phone_cache = {}
    return _phone_cache


def resolve_email(name_or_email: str) -> str | None:
    s = (name_or_email or "").strip()
    if not s:
        return None
    if "@" in s:
        return s
    return _load().get(s.lower())


def resolve_phone(name_or_phone: str) -> str | None:
    s = (name_or_phone or "").strip()
    if not s:
        return None
    digits = s.replace("+", "").replace(" ", "").replace("-", "")
    if digits.isdigit() and len(digits) >= 7:
        return digits
    return _load_phones().get(s.lower())


def list_contacts() -> dict[str, str]:
    return dict(_load())
