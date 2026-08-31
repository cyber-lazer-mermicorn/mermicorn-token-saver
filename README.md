# mermicorn-token-saver

**Highest-leverage AI-agent token control plane** (v0.2).

Primary metric: **cost per successful task**.

```
Doctor → Strategy Router → Apply (CLI compact | symbol slice) → Receipt
                ↘ Session loop detector
                ↘ MCP stdio tools
```

## Install

```bash
pip install -e ".[dev]"
mts version   # 0.2.0
pytest -q
```

## Commands

```bash
mts diagnose -f big_log.txt
mts compact -f pytest.out --tool pytest --receipt
mts index -f src/app.py
mts index --tree src --json
mts symbol -f src/app.py -n MyClass --receipt
mts apply src/app.py --mode symbol --symbol MyClass --receipt
mts session-demo --tool Bash --repeats 6
mts mcp          # stdio MCP server
```

## MCP tools

`diagnose_text` · `compact_cli` · `index_symbols` · `find_symbol` · `session_record_tool` · `session_check`

Wire as:

```json
{
  "mcpServers": {
    "mermicorn-token-saver": {
      "command": "python",
      "args": ["-m", "mermicorn_token_saver.mcp.server"]
    }
  }
}
```

## Design

| Component | Role |
|-----------|------|
| Doctor | Deterministic waste rules (no LLM) |
| Strategy | Layer + action recommendations |
| Symbol index | AST map → slice instead of full file |
| Session tracker | Unbounded tool-loop detection |
| Apply | End-to-end act + receipt |
| CLI processors | git / pytest / npm / cargo / docker |
| MCP | Stdio tools, zero hard deps |

Proprietary — All Rights Reserved. See RIGHTS.md.
