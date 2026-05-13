# Experimental Area

Use this area for worker/MCP experiments that should not affect the default
voice runtime yet.

Current experimental concepts:

- ProOperator / Gemini Pro worker
- MCP hub manager
- Unified operator MCP server
- Gemini CLI worker

Before moving any experiment into the stable path, it should have:

- a feature flag in `config.py`
- a narrow backend entry point
- no direct prompt pressure on Gemini Live
- a failure mode that returns an error instead of restarting the Live session
