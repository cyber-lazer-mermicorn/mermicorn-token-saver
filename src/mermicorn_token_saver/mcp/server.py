"""Minimal MCP-compatible stdio tool server (JSON-RPC 2.0 subset).

Tools:
  diagnose_text, compact_cli, index_symbols, find_symbol, session_check

No third-party MCP SDK required. Works as:
  python -m mermicorn_token_saver.mcp.server
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .. import __version__
from ..apply import apply_cli_text, apply_symbol_slice
from ..doctor import diagnose_text
from ..index.symbols import index_source
from ..receipts import estimate_tokens
from ..session import SessionTracker
from ..strategy import recommend

_TRACKER = SessionTracker()


def _result(id_: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


TOOLS = [
    {
        "name": "diagnose_text",
        "description": "Run Mermicorn Doctor on text; returns findings and strategy recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "path_hint": {"type": "string"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "compact_cli",
        "description": "Compact CLI/log output with content-aware processors. Preserves errors and diffs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "tool": {"type": "string", "enum": ["git", "pytest", "npm", "cargo", "docker", "generic"]},
            },
            "required": ["text"],
        },
    },
    {
        "name": "index_symbols",
        "description": "Build a Python symbol index (signatures + line ranges) from source text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["source"],
        },
    },
    {
        "name": "find_symbol",
        "description": "Return a single symbol slice instead of a full file. Dominant code-read saver.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "symbol": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["source", "symbol"],
        },
    },
    {
        "name": "session_record_tool",
        "description": "Record a tool invocation into the session tracker for loop detection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tokens_est": {"type": "integer"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "session_check",
        "description": "Check the session tracker for unbounded tool loops.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "diagnose_text":
        text = arguments.get("text", "")
        path = arguments.get("path_hint", "")
        lines = text.count("\n") + (1 if text else 0)
        d = diagnose_text(text, path_hint=path, line_count=lines)
        recs = recommend(d)
        return {
            "findings": [
                {
                    "kind": f.kind.value,
                    "severity": f.severity,
                    "evidence": f.evidence,
                    "estimated_tokens": f.estimated_tokens,
                    "remediation_hint": f.remediation_hint,
                }
                for f in d.findings
            ],
            "total_estimated_waste": d.total_estimated_waste,
            "recommendations": [
                {
                    "layer": r.layer.value,
                    "action": r.action.value,
                    "priority": r.priority,
                    "rationale": r.rationale,
                }
                for r in recs
            ],
        }
    if name == "compact_cli":
        res = apply_cli_text(arguments.get("text", ""), tool=arguments.get("tool"))
        return {
            "output": res.output,
            "receipt": res.receipt.to_dict() if res.receipt else None,
            "action_taken": res.action_taken,
        }
    if name == "index_symbols":
        src = arguments.get("source", "")
        path = arguments.get("path", "<string>")
        idx = index_source(src, path=path)
        return {
            "count": len(idx.symbols),
            "summary": idx.summary(),
            "symbols": [
                {
                    "name": s.name,
                    "kind": s.kind,
                    "qualname": s.qualname,
                    "lineno": s.lineno,
                    "end_lineno": s.end_lineno,
                    "signature": s.signature,
                    "path": s.path,
                }
                for s in idx.symbols
            ],
            "estimated_full_file_tokens": estimate_tokens(src),
        }
    if name == "find_symbol":
        res = apply_symbol_slice(
            arguments.get("source", ""),
            path=arguments.get("path", "<string>"),
            symbol_name=arguments.get("symbol", ""),
        )
        return {
            "output": res.output,
            "receipt": res.receipt.to_dict() if res.receipt else None,
            "action_taken": res.action_taken,
        }
    if name == "session_record_tool":
        _TRACKER.record_tool(
            arguments.get("name", "unknown"),
            tokens_est=int(arguments.get("tokens_est") or 0),
        )
        return {"ok": True, "event_count": len(_TRACKER.events)}
    if name == "session_check":
        return _TRACKER.to_dict()
    raise ValueError(f"unknown tool: {name}")


def handle(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        return _result(
            id_,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mermicorn-token-saver", "version": __version__},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _result(id_, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            result = _call_tool(name, args)
            return _result(
                id_,
                {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "isError": False,
                },
            )
        except Exception as exc:
            return _result(
                id_,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )
    if method == "ping":
        return _result(id_, {})
    if id_ is not None:
        return _error(id_, -32601, f"Method not found: {method}")
    return None


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
