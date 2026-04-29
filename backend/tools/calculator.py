"""Deterministic calculator actions for known simple tasks (Windows Optimize)."""

import ast
import asyncio
import re
import time
import pyautogui
import pygetwindow as gw
from tools.app_control import open_app

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

def _focus_calculator() -> bool:
    try:
        wins = [w for w in gw.getAllWindows() if "calculator" in w.title.lower() or "hesap makinesi" in w.title.lower()]
        if wins:
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            return True
        return False
    except Exception:
        return False

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

    focused = await asyncio.to_thread(_focus_calculator)
    if not focused:
        # Fallback to second open app call
        second_open = await asyncio.to_thread(open_app, "calculator")
        if not second_open.get("ok"):
            return {"ok": False, "error": second_open.get("error", "Calculator odaklanamadı")}

    await asyncio.sleep(0.4)

    try:
        await asyncio.to_thread(_type_calculator_expression, expr)
    except Exception as exc:
        return {"ok": False, "error": f"hesap makinesi input başarısız: {exc}"}

    await asyncio.sleep(0.4)

    try:
        result = safe_eval_expression(expr)
    except Exception as exc:
        return {"ok": False, "error": f"ifade hesaplanamadı: {exc}"}

    return {"ok": True, "result": result, "expression": expr}
