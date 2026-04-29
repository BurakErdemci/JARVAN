"""Computer Use — otonom ekran kontrol ajanı (pyautogui + Gemini Vision).

Ekranı görüp, mouse/keyboard ile herhangi bir uygulamada otonom görev yürütür.
browser_task tarayıcıyla sınırlıyken, bu araç bilgisayardaki HER uygulamayı kontrol edebilir.

Akış: screenshot → Gemini Vision → JSON action → pyautogui → tekrarla
"""

import asyncio
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
import threading

import pyautogui

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GEMINI_API_KEY

from google import genai
from google.genai import types


# ─── Sabitler ─────────────────────────────────────────────────────────

MAX_STEPS = 15
TASK_TIMEOUT_S = 300          # 5 dakika
SCREENSHOT_SIZE = (1280, 720) # Vision modele gönderilecek thumbnail boyutu
ACTION_DELAY_S = 1.5          # Aksiyon sonrası UI tepkisi için bekleme

IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

# Vision model fallback zinciri (live_session.py ile aynı)
VISION_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite-preview",
)


# ─── Task lock (browser_agent.py pattern) ─────────────────────────────

_TASK_LOCK = threading.Lock()
_TASK_RUNNING = False


def _try_acquire() -> bool:
    global _TASK_RUNNING
    with _TASK_LOCK:
        if _TASK_RUNNING:
            return False
        _TASK_RUNNING = True
        return True


def _release():
    global _TASK_RUNNING
    with _TASK_LOCK:
        _TASK_RUNNING = False


# ─── pyautogui güvenlik ayarları ──────────────────────────────────────

pyautogui.FAILSAFE = True   # Mouse ekran köşesine gidince dur (güvenlik)
pyautogui.PAUSE = 0.1       # Her pyautogui komutu arası kısa bekleme


# ─── Koordinat dönüşümü ──────────────────────────────────────────────

def _get_monitor_bounds() -> dict:
    """Aktif monitörün piksel offsetlerini döner."""
    from screen.capture import get_monitor_bounds
    return get_monitor_bounds()


def _scale_coords(x: int, y: int, tw: int, th: int, bounds: dict) -> tuple[int, int]:
    """Model koordinatlarını (1280x720 içindeki) gerçek ekran koordinatlarına çevirir.
    
    tw, th: Thumbnail'in (modelin gördüğü resmin) gerçek boyutları.
    bounds: mss'ten gelen fiziksel ekran sınırları.
    """
    # 1. Oransal olarak thumbnail'den fiziksel (mss) boyutuna çık
    # x,y modelin gördüğü (thumb_w, thumb_h) koordinatları
    mx = x * bounds["width"] / tw
    my = y * bounds["height"] / th
    
    # 2. Offset ekle (multi-monitor)
    return int(mx + bounds["left"]), int(my + bounds["top"])


def _validate_point(x: int, y: int, tw: int, th: int) -> str | None:
    if not (0 <= int(x) < int(tw)):
        return f"x koordinatı thumbnail dışında: {x} (0..{tw - 1})"
    if not (0 <= int(y) < int(th)):
        return f"y koordinatı thumbnail dışında: {y} (0..{th - 1})"
    return None


def _validate_action(action: dict, thumb_size: tuple[int, int]) -> str | None:
    act = action.get("action", "").lower().strip()
    tw, th = thumb_size

    if act in {"click", "double_click", "right_click", "move"}:
        if "x" not in action or "y" not in action:
            return "x/y eksik"
        return _validate_point(action["x"], action["y"], tw, th)

    if act == "drag":
        if any(k not in action for k in ("from_x", "from_y", "to_x", "to_y")):
            return "drag koordinatları eksik"
        err = _validate_point(action["from_x"], action["from_y"], tw, th)
        if err:
            return f"drag başlangıç: {err}"
        return _validate_point(action["to_x"], action["to_y"], tw, th)

    if act == "scroll" and ("x" in action or "y" in action):
        x = int(action.get("x", 0))
        y = int(action.get("y", 0))
        return _validate_point(x, y, tw, th)

    return None


# ─── Clipboard paste (Türkçe karakter desteği) ───────────────────────

def _clipboard_paste(text: str):
    """Metni clipboard'a kopyalayıp Ctrl+V ile yapıştır. (Windows PowerShell optimize)"""
    escaped = text.replace("'", "''")
    subprocess.run(
        ["powershell", "-command", f"Set-Clipboard -Value '{escaped}'"],
        capture_output=True, timeout=5,
    )
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)


# ─── Hotkey normalizasyonu ────────────────────────────────────────────

def _normalize_hotkey(keys: str) -> list[str]:
    """Platform-aware hotkey normalizasyonu."""
    return [k.strip().lower() for k in keys.split("+")]


# ─── Aksiyon yürütücü ────────────────────────────────────────────────

def do_action(
    action: dict,
    monitor_bounds: dict,
    thumb_size: tuple[int, int],
) -> dict:
    """Tek bir aksiyonu yürütür. Koordinatlar thumbnail space'den gerçek ekrana çevrilir."""
    act = action.get("action", "").lower().strip()
    reason = action.get("reason", "")
    tw, th = thumb_size

    try:
        validation_error = _validate_action(action, thumb_size)
        if validation_error:
            return {"ok": False, "error": f"Geçersiz koordinat: {validation_error}"}

        if act == "click":
            ax, ay = _scale_coords(action["x"], action["y"], tw, th, monitor_bounds)
            print(f"      [pyautogui] Clicking: ({ax}, {ay})", flush=True)
            pyautogui.click(ax, ay)
            return {"ok": True, "action": "click", "pos": f"{ax},{ay}", "reason": reason}

        elif act == "double_click":
            ax, ay = _scale_coords(action["x"], action["y"], tw, th, monitor_bounds)
            print(f"      [pyautogui] Double Clicking: ({ax}, {ay})", flush=True)
            pyautogui.doubleClick(ax, ay)
            return {"ok": True, "action": "double_click", "pos": f"{ax},{ay}", "reason": reason}

        elif act == "right_click":
            ax, ay = _scale_coords(action["x"], action["y"], tw, th, monitor_bounds)
            print(f"      [pyautogui] Right Clicking: ({ax}, {ay})", flush=True)
            pyautogui.rightClick(ax, ay)
            return {"ok": True, "action": "right_click", "pos": f"{ax},{ay}", "reason": reason}

        elif act == "type_text":
            text = action.get("text", "")
            if not text:
                return {"ok": False, "error": "text boş"}
            _clipboard_paste(text)
            return {"ok": True, "action": "type_text", "text": text[:50], "reason": reason}

        elif act == "hotkey":
            keys_str = action.get("keys", "")
            if not keys_str:
                return {"ok": False, "error": "keys boş"}
            parts = _normalize_hotkey(keys_str)
            pyautogui.hotkey(*parts)
            return {"ok": True, "action": "hotkey", "keys": "+".join(parts), "reason": reason}

        elif act == "scroll":
            x = action.get("x", 0)
            y = action.get("y", 0)
            if x or y:
                ax, ay = _scale_coords(x, y, tw, th, monitor_bounds)
                pyautogui.moveTo(ax, ay)
            direction = action.get("direction", "down")
            clicks = action.get("clicks", 3)
            scroll_amount = clicks if direction == "up" else -clicks
            pyautogui.scroll(scroll_amount)
            return {"ok": True, "action": "scroll", "direction": direction, "clicks": clicks, "reason": reason}

        elif act == "move":
            ax, ay = _scale_coords(action["x"], action["y"], tw, th, monitor_bounds)
            pyautogui.moveTo(ax, ay)
            return {"ok": True, "action": "move", "pos": f"{ax},{ay}", "reason": reason}

        elif act == "drag":
            fx, fy = _scale_coords(action["from_x"], action["from_y"], tw, th, monitor_bounds)
            tx, ty = _scale_coords(action["to_x"], action["to_y"], tw, th, monitor_bounds)
            pyautogui.moveTo(fx, fy)
            time.sleep(0.1)
            pyautogui.mouseDown()
            pyautogui.moveTo(tx, ty, duration=0.5)
            pyautogui.mouseUp()
            return {"ok": True, "action": "drag", "from": f"{fx},{fy}", "to": f"{tx},{ty}", "reason": reason}

        elif act == "wait":
            seconds = min(float(action.get("seconds", 1)), 5.0)
            time.sleep(seconds)
            return {"ok": True, "action": "wait", "seconds": seconds, "reason": reason}

        elif act == "done":
            return {"ok": True, "action": "done", "result": action.get("result", "Görev tamamlandı.")}

        else:
            return {"ok": False, "error": f"Bilinmeyen aksiyon: {act}"}

    except pyautogui.FailSafeException:
        return {"ok": False, "error": "FAILSAFE — mouse ekran köşesinde, güvenlik durdurusu."}
    except Exception as e:
        return {"ok": False, "error": f"Aksiyon hatası: {type(e).__name__}: {e}"}


# ─── Agent system prompt ─────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = (
    "Sen bir bilgisayar kontrol ajanısın. Ekran görüntüsünü analiz edip, "
    "verilen görevi tamamlamak için tek bir aksiyon üretiyorsun.\n\n"

    "MEVCUT AKSİYONLAR:\n"
    '- {{"action": "click", "x": <int>, "y": <int>, "reason": "..."}}\n'
    '- {{"action": "double_click", "x": <int>, "y": <int>, "reason": "..."}}\n'
    '- {{"action": "right_click", "x": <int>, "y": <int>, "reason": "..."}}\n'
    '- {{"action": "type_text", "text": "<str>", "reason": "..."}}\n'
    '- {{"action": "hotkey", "keys": "<str>", "reason": "..."}}  (örn: "ctrl+c", "alt+tab", "enter")\n'
    '- {{"action": "scroll", "x": <int>, "y": <int>, "direction": "up"|"down", "clicks": <int>, "reason": "..."}}\n'
    '- {{"action": "move", "x": <int>, "y": <int>, "reason": "..."}}\n'
    '- {{"action": "drag", "from_x": <int>, "from_y": <int>, "to_x": <int>, "to_y": <int>, "reason": "..."}}\n'
    '- {{"action": "wait", "seconds": <float>, "reason": "..."}}  (max 5sn)\n'
    '- {{"action": "done", "result": "<str>"}}  — Görev tamamlandı veya yapılamıyor\n\n'

    "--- ÇALIŞMA PRENSİBİ (DÜŞÜNCE ZİNCİRİ) ---\n"
    "Her yanıtında 'reason' alanını şu yapıda kullanmalısın:\n"
    "1. GÖZLEM: Şu an ekranda tam olarak ne görüyorsun? (Pencere nerede? Hangi sayı görünüyor? X ve Y ekseninde nerede?)\n"
    "2. ANALİZ: Önceki aksiyonun sonucunu ekranda GÖRÜYOR MUSUN? (Örn: 7'ye tıkladıysan, ekranda 7 yazdı mı?)\n"
    "3. KARAR: Bir sonraki adımın koordinatlarını (x, y) sanki elinde bir cetvel varmış gibi sıfırdan hesapla. Asla tahmin etme!\n\n"

    "KURALLAR:\n"
    "1. SADECE 1 aksiyon döndür. SADECE JSON döndür, dışına metin ekleme.\n"
    "2. GÖRSEL İSPAT ŞART: Görev bittiğinde (Örn: 7+7=14), ekranda '14' rakamını görmeden 'done' deme. Eğer göremiyorsan adımı tekrarla veya hatanı bul.\n"
    "3. PENCERE KARIŞIKLIĞI: Ekranda birden fazla pencere (Jarvan ve Uygulama) varken, tıklayacağın butonun HEDEF UYGULAMA (örn: Hesap Makinesi) sınırı içinde olduğundan emin ol.\n"
    "4. ODAKLANMA: Herhangi bir sayı girmeden önce mutlaka uygulamanın başlık çubuğuna veya içine tıkla.\n"
    "5. JARVAN PENCERESİ: Kendi panelin senin için 'ölümcül bölgedir', oradaki hiçbir şeye (Durdur, Live vb.) dokunma.\n"
    "6. Platform: {platform}\n"
    "7. ÇOK ÖNEMLİ: Koordinatların her zaman verilen EKRAN BOYUTU içinde kalmalı. "
    "Örneğin yükseklik 720 ise y=720 veya üzeri YASAK; genişlik 1280 ise x=1280 veya üzeri YASAK.\n"
)


def _build_step_prompt(
    task: str,
    step: int,
    max_steps: int,
    width: int,
    height: int,
    history: list[str],
) -> str:
    """Her adım için vision model'e gönderilecek metin prompt."""
    parts = [
        f"GÖREV: {task}",
        f"ADIM: {step}/{max_steps}",
        f"EKRAN BOYUTU: {width}x{height} piksel",
    ]
    if history:
        # Son 5 adımı göster — model önceki aksiyonları bilsin, döngüye girmesin
        parts.append("\nÖNCEKİ ADIMLAR:\n" + "\n".join(history[-5:]))
    parts.append(
        "\nÖnemli: Yanıtındaki 'reason' alanında 'GÖZLEM, ANALİZ, KARAR' sırasını mutlaka kullan.\n"
        "Ekran görüntüsünü analiz et ve görev için sıradaki TEK aksiyonu JSON olarak döndür."
    )
    return "\n".join(parts)


def _parse_action(text: str) -> dict | None:
    """Model çıktısından JSON aksiyonu parse et.
    Model bazen ```json ... ``` ile sarar, bazen düz JSON döner."""
    text = text.strip()

    # ```json ... ``` bloğu bloğu varsa içini çıkar
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    else:
        # Düz JSON bul — en dıştaki { } arasını al
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            text = text[brace_start : brace_end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ─── Model Pool ──────────────────────────────────────────────────────

# (model_id, rpm_limit) — Vision-capable modeller.
MODEL_POOL = [
    ("gemini-3.1-flash-lite-preview", 15),  # Hızlı ve 500 RPD (En dengeli)
    ("gemini-2.0-flash", 15),               # Güçlü fallback
    ("gemini-2.5-flash-lite", 15),
]
SAFETY_MARGIN = 1  # limit - 1'de anahtarla

# Global rotasyon durumu (Farklı görevler arasında RPM koruması için)
_state = {
    "current_pool_idx": 0,
    "calls_on_current_model": 0,
    "last_rotation_time": time.time()
}

def _get_model_state():
    """RPM süresi dolduysa sayaçları sıfırlar."""
    now = time.time()
    # 60 saniye geçtiyse RPM penceresi sıfırlanmıştır
    if now - _state["last_rotation_time"] > 60:
        _state["calls_on_current_model"] = 0
        _state["current_pool_idx"] = 0
        _state["last_rotation_time"] = now
    return _state


def _next_model_index(idx: int) -> int:
    return (idx + 1) % len(MODEL_POOL)


def _should_rotate_for_error(message: str) -> bool:
    error_keywords = (
        "quota",
        "429",
        "exhausted",
        "rate",
        "503",
        "unavailable",
        "overload",
        "resource_exhausted",
        "not supported",
        "image",
        "vision",
    )
    return any(token in message for token in error_keywords)


async def _generate_action(
    client: genai.Client,
    jpeg: bytes,
    step_prompt: str,
    vision_config: types.GenerateContentConfig,
    state: dict,
) -> tuple[dict | None, Exception | None]:
    """Model havuzundan tek aksiyon almaya çalışır; sonsuz rotasyon yapmaz."""
    last_err: Exception | None = None

    for _ in range(len(MODEL_POOL)):
        model_name, rpm_limit = MODEL_POOL[state["current_pool_idx"]]

        if state["calls_on_current_model"] >= max(rpm_limit - SAFETY_MARGIN, 1):
            state["current_pool_idx"] = _next_model_index(state["current_pool_idx"])
            state["calls_on_current_model"] = 0
            continue

        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
                    step_prompt,
                ],
                config=vision_config,
            )
            raw_text = (response.text or "").strip()
            action_json = _parse_action(raw_text) if raw_text else None
            if action_json:
                state["calls_on_current_model"] += 1
                return action_json, None

            last_err = RuntimeError(f"{model_name} boş/geçersiz aksiyon döndürdü")
            print(f"[computer_use] {model_name} geçersiz aksiyon döndürdü, rotasyon yapılıyor", flush=True)
            state["current_pool_idx"] = _next_model_index(state["current_pool_idx"])
            state["calls_on_current_model"] = 0
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if _should_rotate_for_error(msg):
                print(f"[computer_use] Model {model_name} hata verdi: {msg}. Rotasyon yapılıyor...", flush=True)
                state["current_pool_idx"] = _next_model_index(state["current_pool_idx"])
                state["calls_on_current_model"] = 0
                continue
            return None, e

    return None, last_err


# ─── Ana agent loop ──────────────────────────────────────────────────

async def run_computer_task(task: str) -> dict:
    """Otonom computer use agent.

    1. Ekranı yakala → Gemini Vision'a gönder
    2. Model JSON action döner
    3. pyautogui ile yürüt
    4. 'done' gelene kadar veya MAX_STEPS'e ulaşana kadar tekrarla
    5. Sonucu dict olarak dön
    """
    if not task or not task.strip():
        return {"ok": False, "error": "görev boş"}
    if not GEMINI_API_KEY:
        return {"ok": False, "error": "GEMINI_API_KEY yok"}

    if not _try_acquire():
        return {"ok": False, "error": "Başka bir computer use görevi zaten çalışıyor."}

    try:
        from screen.capture import capture_screenshot_pil, get_monitor_bounds

        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )

        monitor_bounds = get_monitor_bounds()
        print(
            "[computer_use] monitor_bounds="
            f"{monitor_bounds.get('left')},{monitor_bounds.get('top')} "
            f"{monitor_bounds.get('width')}x{monitor_bounds.get('height')} "
            f"source={monitor_bounds.get('source', 'unknown')} "
            f"scale=({monitor_bounds.get('scale_x')},{monitor_bounds.get('scale_y')})",
            flush=True,
        )
        platform_name = "macOS" if IS_MAC else ("Windows" if IS_WIN else "Linux")
        system_prompt = AGENT_SYSTEM_PROMPT.format(platform=platform_name)

        history: list[str] = []
        final_result = ""

        # Global durumu al
        state = _get_model_state()

        for step in range(1, MAX_STEPS + 1):
            # ── 1. Ekranı yakala ──
            img = await asyncio.to_thread(capture_screenshot_pil)
            img.thumbnail(SCREENSHOT_SIZE)
            thumb_w, thumb_h = img.size

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=80)
            jpeg = buf.getvalue()

            # ── 2. Vision model'den aksiyon al (Rotasyonlu) ──
            step_prompt = _build_step_prompt(
                task, step, MAX_STEPS, thumb_w, thumb_h, history,
            )
            vision_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
            )

            action_json, last_err = await _generate_action(
                client=client,
                jpeg=jpeg,
                step_prompt=step_prompt,
                vision_config=vision_config,
                state=state,
            )

            if not action_json:
                print(
                    f"[computer_use] Adım {step}: Vision model aksiyon döndüremedi: {last_err}",
                    flush=True,
                )
                final_result = f"Vision model aksiyon üretemedi (adım {step})"
                break

            # ── 3. Aksiyonu yürüt ──
            act_type = action_json.get("action", "")
            reason = action_json.get("reason", "")
            print(
                f"[computer_use] Adım {step}/{MAX_STEPS}: {act_type} — {reason}",
                flush=True,
            )

            if act_type == "done":
                final_result = action_json.get("result", "Görev tamamlandı.")
                history.append(f"{step}. done: {final_result}")
                break

            result = await asyncio.to_thread(
                do_action, action_json, monitor_bounds, (thumb_w, thumb_h),
            )
            status = "✓" if result.get("ok") else "✗ " + result.get("error", "")
            history.append(f"{step}. {act_type}: {reason} → {status}")

            if not result.get("ok"):
                print(
                    f"[computer_use] Aksiyon hatası: {result.get('error')}",
                    flush=True,
                )
                # Hata olsa da devam et — model bir sonraki adımda düzeltebilir

            # ── 4. UI tepkisi bekle ──
            await asyncio.sleep(ACTION_DELAY_S)

        if not final_result:
            final_result = (
                f"Görev {MAX_STEPS} adımda tamamlanamadı. "
                f"Son adımlar: {'; '.join(history[-3:])}"
            )

        return {"ok": True, "result": final_result[:600]}

    except asyncio.TimeoutError:
        return {"ok": False, "error": f"Görev {TASK_TIMEOUT_S}sn içinde bitmedi"}
    except Exception as e:
        import traceback
        print(f"[computer_use] HATA:\n{traceback.format_exc()}", flush=True)
        return {"ok": False, "error": f"Computer use hatası: {type(e).__name__}: {e}"}
    finally:
        _release()
