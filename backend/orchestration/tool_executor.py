"""ToolExecutor — wraps _handle_tool_calls logic extracted from LiveSession."""
import asyncio
import time
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.genai import types

from tools.computer_use import run_computer_task
from tools.calculator import run_calculator_task
from tools.developer import save_report, create_project_file, create_folder
from workers.gemini_cli_worker import start_gemini_task, get_job_result
from tools.obsidian import obsidian_manage
from ai.insight_agent import get_insight_agent

from orchestration.tool_registry import TOOL_IMPL


@dataclass
class ExecutorContext:
    on_log: Callable
    inflight_tools: set
    tool_cooldown: dict
    get_last_research: Callable  # returns last_research_result
    get_transcript: Callable     # returns full_session_transcript list
    clear_transcript: Callable   # clears full_session_transcript
    set_asleep: Callable         # Callable[[bool], None]
    describe_screen: Callable    # async


class ToolExecutor:
    def __init__(self, ctx: ExecutorContext):
        self.ctx = ctx

    async def handle(self, function_calls, session) -> list:
        ctx = self.ctx
        responses = []
        for fc in function_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}

            if name == "computer_use":
                task = args.get("task", "")
                if "computer_use" in ctx.inflight_tools:
                    result = {"ok": False, "error": "Computer use görevi zaten çalışıyor, lütfen bekle."}
                    ctx.on_log("system", "[tool] computer_use zaten in-flight, atlandı", None)
                    responses.append(types.FunctionResponse(id=fc.id, name=name, response=result))
                    continue
                now = time.monotonic()
                cooldown_until = ctx.tool_cooldown.get("computer_use", 0)
                if now < cooldown_until:
                    result = {"ok": False, "error": "Az önce aynı görev tamamlandı, sonucu sesli özetle."}
                    ctx.on_log("system", f"[tool] computer_use cooldown ({cooldown_until - now:.0f}s kaldı), atlandı", None)
                    responses.append(types.FunctionResponse(id=fc.id, name=name, response=result))
                    continue
                ctx.inflight_tools.add("computer_use")
                ctx.on_log("system", f"[tool] computer_use({task[:80]}...)", None)
                try:
                    raw = await asyncio.wait_for(run_computer_task(task), timeout=300)
                    ctx.inflight_tools.discard("computer_use")
                    ctx.tool_cooldown["computer_use"] = time.monotonic() + 60
                    if raw and raw.get("ok"):
                        result = {"ok": True, "result": str(raw.get("result", ""))}
                    else:
                        err_msg = raw.get("error", "görev başarısız") if raw else "Boş yanıt"
                        result = {"ok": False, "error": str(err_msg)}
                except asyncio.TimeoutError:
                    ctx.inflight_tools.discard("computer_use")
                    result = {"ok": False, "error": "Computer use 5 dakikada bitmedi, zaman aşımı."}
                except Exception as e:
                    ctx.inflight_tools.discard("computer_use")
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "calculator_compute":
                task = args.get("task", "")
                ctx.on_log("system", f"[tool] calculator_compute({task[:80]}...)", None)
                try:
                    raw = await run_calculator_task(task)
                    if raw.get("ok"):
                        result = {"ok": True, "result": f"Calculator'da {raw.get('expression')} işlendi, sonuç: {raw.get('result')}"}
                    else:
                        result = {"ok": False, "error": raw.get("error", "hesap makinesi görevi başarısız")}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "play_spotify_track":
                from tools.spotify import play_spotify_track
                ctx.on_log("system", f"[tool] play_spotify_track({args})", None)
                try:
                    result = await play_spotify_track(
                        track=args.get("track"),
                        artist=args.get("artist"),
                        is_playlist=args.get("is_playlist", False),
                        shuffle=args.get("shuffle", False)
                    )
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "spotify_control":
                from tools.spotify import control_spotify
                action = args.get("action")
                ctx.on_log("system", f"[tool] spotify_control(action={action})", None)
                try:
                    result = await control_spotify(action)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "save_report":
                filename = args.get("filename", "Rapor.md")
                content = args.get("content", "")

                # Eğer content boşsa veya Gemini gönderdiyse, hafızadaki sonucu kullan
                if (not content or len(content) < 10) and ctx.get_last_research():
                    content = ctx.get_last_research()

                ctx.on_log("system", f"[tool] save_report({filename}) [Hafızadan: {bool(not content)}]", None)
                try:
                    result = save_report(filename, content)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "create_project_file":
                path = args.get("file_path", "")
                content = args.get("content", "")
                ctx.on_log("system", f"[tool] create_project_file({path})", None)
                try:
                    result = create_project_file(path, content)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "create_folder":
                folder_path = args.get("folder_path", "")
                ctx.on_log("system", f"[tool] create_folder({folder_path})", None)
                try:
                    result = create_folder(folder_path)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "start_gemini_task":
                prompt = args.get("prompt", "")
                heavy = bool(args.get("heavy", False))
                model_tag = "pro" if heavy else "flash"
                ctx.on_log("system", f"[tool] start_gemini_task(model={model_tag}, prompt={prompt[:60]}...)", None)
                try:
                    job_id = await start_gemini_task(prompt, heavy=heavy)
                    result = {"ok": True, "job_id": job_id, "message": f"Görev başlatıldı ({model_tag}). Sonuç için get_gemini_result('{job_id}') kullan."}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "get_gemini_result":
                job_id = args.get("job_id", "")
                ctx.on_log("system", f"[tool] get_gemini_result({job_id})", None)
                try:
                    result = get_job_result(job_id)
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] status={result.get('status')}", None)
            elif name == "see_screen":
                ctx.on_log("system", "[tool] see_screen()", None)
                try:
                    description = await ctx.describe_screen()
                    if description:
                        result = {"ok": True, "screen": description}
                    else:
                        result = {"ok": False, "error": "ekran analizi başarısız"}
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            elif name == "sleep_mode":
                ctx.on_log("system", "[tool] sleep_mode()", None)
                ctx.set_asleep(True)

                # Otonom Öğrenme Döngüsü Başlat (Arka Planda)
                transcript = ctx.get_transcript()
                if transcript:
                    transcript_str = "\n".join(transcript)
                    asyncio.create_task(get_insight_agent().process_session(transcript_str))
                    # Bir sonraki session için temizle
                    ctx.clear_transcript()

                result = {"ok": True, "message": "Jarvan uyku moduna geçti. Sadece 'Uyan Jarvan' ile uyanacak."}
                ctx.on_log("system", "[Jarvan Uyuyor...]", None)
            elif name == "obsidian_manage":
                ctx.on_log("system", f"[tool] obsidian_manage({args})", None)
                try:
                    result = await asyncio.to_thread(
                        obsidian_manage,
                        action=args.get("action"),
                        title=args.get("title"),
                        content=args.get("content"),
                        folder=args.get("folder"),
                        query=args.get("query")
                    )
                except Exception as e:
                    result = {"ok": False, "error": str(e)}
                ctx.on_log("system", f"[tool sonuç] {result}", None)
            else:
                impl = TOOL_IMPL.get(name)
                if impl is None:
                    result = {"ok": False, "error": f"bilinmeyen tool: {name}"}
                else:
                    ctx.on_log("system", f"[tool] {name}({args})", None)
                    try:
                        raw_result = await asyncio.to_thread(impl, args)
                        result = raw_result.copy() if isinstance(raw_result, dict) else raw_result
                        if isinstance(result, dict) and "url" in result:
                            del result["url"]
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}
                    ctx.on_log("system", f"[tool sonuç] {result}", None)

            responses.append(types.FunctionResponse(
                id=fc.id,
                name=name,
                response=result,
            ))

        await session.send_tool_response(function_responses=responses)
