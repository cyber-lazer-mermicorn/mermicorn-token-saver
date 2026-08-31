# STATUS — mermicorn-token-saver

**As of:** 2026-08-31  
**Version:** 0.1.0  
**State:** Foundation live — Doctor, Strategy Router, Receipts, CLI processors, CLI, tests green.

## What works

- Deterministic Doctor rules (verbose CLI, chatty prose, oversized log, full-file heuristic)
- Strategy Router → layer + action recommendations
- Receipt engine (exact / estimated) + cost-per-successful-task helper
- CLI compactors: git, pytest, npm, generic (preserve errors/diffs)
- `mts diagnose` / `mts compact` / `mts version`
- pytest suite on core paths

## Next (code-up priority)

1. Structural symbol index / navigation surface (dominant measured lever on code-read layer)
2. MCP server entry for Claude Code / Cursor
3. Session event stream + unbounded-loop detector
4. Integration receipts against real agent sessions
5. Wire into constellation-map + command-board panel

## Non-goals for v0.1

- Claiming fixed % savings without measured receipts
- Replacing specialized tools (RTK, Headroom, Token Savior, etc.) — this is the control plane that routes among them
