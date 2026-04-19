"""Deterministic calculator actions for known simple tasks."""

import ast
import asyncio
import platform
import re
import subprocess
import time

import pyautogui

from tools.app_control import open_app

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"


def extract_expression(task: str) -> str | None:
    text = (task or "").lower()
    text = text.replace("×", "*").replace("x", "*").replace("÷", "/").replace(",", ".")
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None
    left, op, right = match.groups()
    return f"{left}{op}{right}"


def safe_eval_expression(expr: str) -> str:
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.Constant,
    )
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError("desteklenmeyen ifade")
    value = eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}}, {})
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _run_osascript(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=5,
    )


def _press_calculator_keys_macos(expr: str):
    keycode_map = {
        "0": 82,
        "1": 83,
        "2": 84,
        "3": 85,
        "4": 86,
        "5": 87,
        "6": 88,
        "7": 89,
        "8": 91,
        "9": 92,
        "+": 69,
        "-": 78,
        "*": 67,
        "/": 75,
        ".": 65,
        "=": 76,
        "C": 8,
    }

    sequence = ["C", *list(expr), "="]
    for token in sequence:
        keycode = keycode_map.get(token)
        if keycode is None:
            raise RuntimeError(f"Calculator keycode mapping yok: {token}")
        script = f'''
tell application "Calculator" to activate
tell application "System Events"
    key code {keycode}
end tell
'''
        result = _run_osascript(script)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Calculator key code failed: {token}")
        time.sleep(0.12)


def _type_calculator_expression(expr: str):
    pyautogui.press("c")
    time.sleep(0.1)
    pyautogui.press("c")
    time.sleep(0.1)
    pyautogui.write(expr, interval=0.05)
    time.sleep(0.1)
    pyautogui.press("enter")


async def run_calculator_task(task: str) -> dict:
    expr = extract_expression(task)
    if not expr:
        return {"ok": False, "error": "hesap makinesi görevi içinde basit bir işlem bulunamadı"}

    open_result = await asyncio.to_thread(open_app, "calculator")
    if not open_result.get("ok"):
        return {"ok": False, "error": open_result.get("error", "Calculator açılamadı")}

    await asyncio.sleep(0.8)

    if IS_MAC:
        subprocess.run(
            ["osascript", "-e", 'tell application "Calculator" to activate'],
            capture_output=True,
            timeout=3,
        )
    elif IS_WIN:
        second_open = await asyncio.to_thread(open_app, "calculator")
        if not second_open.get("ok"):
            return {"ok": False, "error": second_open.get("error", "Calculator odaklanamadı")}

    await asyncio.sleep(0.4)

    try:
        if IS_MAC:
            await asyncio.to_thread(_press_calculator_keys_macos, expr)
        else:
            await asyncio.to_thread(_type_calculator_expression, expr)
    except Exception as exc:
        return {"ok": False, "error": f"hesap makinesi input başarısız: {exc}"}

    await asyncio.sleep(0.4)

    try:
        result = safe_eval_expression(expr)
    except Exception as exc:
        return {"ok": False, "error": f"ifade hesaplanamadı: {exc}"}

    return {"ok": True, "result": result, "expression": expr}
