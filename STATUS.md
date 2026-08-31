# STATUS — mermicorn-token-saver

**As of:** 2026-08-31  
**Version:** 0.2.0  
**State:** Upgraded control plane — symbol index, session loop detector, apply pipeline, MCP stdio, expanded CLI processors. Tests green.

## Audit (v0.1 → gaps)

| Gap | Severity | Status in 0.2 |
|-----|----------|---------------|
| No structural symbol index (dominant code-read lever) | Critical | **Shipped** — AST index + `mts symbol` / `find_symbol` |
| MCP stub only | High | **Shipped** — stdio JSON-RPC tools, zero extra deps |
| No session / unbounded-loop detector | High | **Shipped** — `SessionTracker` + `session-demo` |
| Advisory-only (no apply path) | High | **Shipped** — `apply.py` + `mts apply` |
| Thin CLI processor set | Medium | **Shipped** — cargo + docker added |
| Docs-only upgrade risk | — | Avoided — code first |

## What works

- Doctor (+ SYMBOL_AVAILABLE, session loops)
- Strategy Router (+ SYMBOL_SLICE)
- Receipts + cost-per-successful-task
- CLI compactors: git, pytest, npm, cargo, docker, generic
- Python AST symbol index + tree walk
- Apply pipeline (cli / symbol / auto)
- MCP stdio server: diagnose_text, compact_cli, index_symbols, find_symbol, session_*
- CLI: diagnose, compact, index, symbol, apply, session-demo, mcp, version

## Next (code-up)

1. Multi-language symbol index (TS/Go via tree-sitter optional extra)
2. Persistent session store across process restarts
3. Constellation-map node + command-board panel wiring
4. Measured integration receipts on real agent sessions

## Non-goals

- Claiming fixed % savings without receipts
- Replacing specialized tools — this routes and proves
