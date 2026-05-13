# JARVAN Backend Runtime Boundaries

This file documents the current stable runtime split. The goal is to keep the
voice assistant reliable while experimental worker and MCP paths evolve.

## Stable Runtime

The active path is:

```text
FastAPI main.py
  -> Pipeline
  -> ai.live_session.LiveSession
  -> memory_manager + memory_core + insight_agent
  -> existing tools/*
```

Responsibilities:

- `main.py`: process lifecycle, WebSocket events, frontend state.
- `LiveSession`: Gemini Live audio session, wake word state, prompt assembly,
  audio I/O, screen description and stable tool handling.
- `memory_manager.py`: structured `memory.json` context.
- `memory_core.py`: ChromaDB behavioral memory.
- `insight_agent.py`: background learning when Jarvan goes to sleep.
- `tools/*`: currently working local abilities.

## Experimental Runtime

These modules are intentionally not part of the default Live tool surface:

- `ai/pro_operator.py`
- `ai/mcp_manager.py`
- `mcp/unified_operator.py`
- `mcp_config.json`

They are the future worker/MCP layer. Keep them behind feature flags until the
stable Live + memory loop is boring and predictable.

## Design Rule

Gemini Live is Jarvan's voice and real-time persona. It should not own long
running code, deep research or MCP orchestration. Those tasks should eventually
go through a backend worker layer that receives a compact context packet from
memory, runs asynchronously, then returns a result for Live to summarize.
