"""CLI entry — diagnose, compact, index, apply, session, mcp."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .apply import apply_cli_text, apply_file, apply_symbol_slice
from .doctor import diagnose_session, diagnose_text
from .index.symbols import index_path, index_source, index_tree
from .processors.cli import compact_cli, detect_tool
from .receipts import make_estimated
from .session import SessionTracker
from .strategy import recommend


def cmd_diagnose(args: argparse.Namespace) -> int:
    text = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    d = diagnose_text(text, path_hint=args.file or "<stdin>", line_count=lines)
    recs = recommend(d)
    out = {
        "version": __version__,
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
    print(json.dumps(out, indent=2))
    return 0


def cmd_compact(args: argparse.Namespace) -> int:
    text = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    tool = args.tool or detect_tool(args.command or text)
    res = apply_cli_text(text, tool=tool, command=args.command or "")
    if args.receipt and res.receipt:
        print(json.dumps(res.receipt.to_dict(), indent=2), file=sys.stderr)
    sys.stdout.write(res.output)
    if not res.output.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    if args.tree:
        idx = index_tree(args.tree)
    elif args.file:
        idx = index_path(args.file)
    else:
        idx = index_source(sys.stdin.read(), path="<stdin>")
    if args.json:
        print(
            json.dumps(
                {
                    "count": len(idx.symbols),
                    "symbols": [
                        {
                            "name": s.name,
                            "kind": s.kind,
                            "qualname": s.qualname,
                            "path": s.path,
                            "lineno": s.lineno,
                            "end_lineno": s.end_lineno,
                            "signature": s.signature,
                        }
                        for s in idx.symbols
                    ],
                },
                indent=2,
            )
        )
    else:
        print(idx.summary(max_items=args.limit))
        print(f"\n# {len(idx.symbols)} symbols", file=sys.stderr)
    return 0


def cmd_symbol(args: argparse.Namespace) -> int:
    text = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    path = args.file or "<stdin>"
    res = apply_symbol_slice(text, path=path, symbol_name=args.name)
    if args.receipt and res.receipt:
        print(json.dumps(res.receipt.to_dict(), indent=2), file=sys.stderr)
    sys.stdout.write(res.output)
    if not res.output.endswith("\n"):
        sys.stdout.write("\n")
    return 0 if res.action_taken == "symbol_slice" else 1


def cmd_apply(args: argparse.Namespace) -> int:
    res = apply_file(args.file, mode=args.mode, symbol=args.symbol, tool=args.tool)
    if args.receipt and res.receipt:
        print(json.dumps(res.receipt.to_dict(), indent=2), file=sys.stderr)
    sys.stdout.write(res.output)
    if not res.output.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_session_demo(args: argparse.Namespace) -> int:
    t = SessionTracker(repeat_threshold=args.threshold)
    for i in range(args.repeats):
        t.record_tool(args.tool, tokens_est=args.tokens)
    d = diagnose_session(t)
    print(json.dumps({"tracker": t.to_dict(), "diagnosis_waste": d.total_estimated_waste}, indent=2))
    return 0


def cmd_version(_: argparse.Namespace) -> int:
    print(__version__)
    return 0


def cmd_mcp(_: argparse.Namespace) -> int:
    from .mcp.server import main as mcp_main

    mcp_main()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="mts",
        description="Mermicorn Token Saver — Doctor · Strategy · Index · Apply · MCP",
    )
    p.add_argument("--version", action="store_true", help="Print version")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("diagnose", help="Run Doctor on a file or stdin")
    d.add_argument("-f", "--file", help="Input file (default: stdin)")
    d.set_defaults(func=cmd_diagnose)

    c = sub.add_parser("compact", help="Compact CLI/log output")
    c.add_argument("-f", "--file", help="Input file (default: stdin)")
    c.add_argument(
        "-t",
        "--tool",
        choices=["git", "pytest", "npm", "cargo", "docker", "generic"],
        help="Force tool profile",
    )
    c.add_argument("--command", help="Original command string for tool detection")
    c.add_argument("--receipt", action="store_true", help="Emit estimated receipt to stderr")
    c.set_defaults(func=cmd_compact)

    ix = sub.add_parser("index", help="Build symbol index (Python AST)")
    ix.add_argument("-f", "--file", help="Single Python file")
    ix.add_argument("--tree", help="Index a directory tree")
    ix.add_argument("--json", action="store_true", help="JSON output")
    ix.add_argument("--limit", type=int, default=80, help="Max summary rows")
    ix.set_defaults(func=cmd_index)

    sy = sub.add_parser("symbol", help="Extract one symbol slice from a file")
    sy.add_argument("-f", "--file", help="Python file")
    sy.add_argument("-n", "--name", required=True, help="Symbol name")
    sy.add_argument("--receipt", action="store_true")
    sy.set_defaults(func=cmd_symbol)

    ap = sub.add_parser("apply", help="Diagnose + apply best compact/slice action")
    ap.add_argument("file", help="Input file")
    ap.add_argument("--mode", choices=["auto", "cli", "symbol"], default="auto")
    ap.add_argument("--symbol", help="Symbol name for symbol mode")
    ap.add_argument("-t", "--tool", help="CLI tool profile")
    ap.add_argument("--receipt", action="store_true")
    ap.set_defaults(func=cmd_apply)

    se = sub.add_parser("session-demo", help="Demo unbounded-loop detector")
    se.add_argument("--tool", default="Read")
    se.add_argument("--repeats", type=int, default=6)
    se.add_argument("--tokens", type=int, default=500)
    se.add_argument("--threshold", type=int, default=4)
    se.set_defaults(func=cmd_session_demo)

    m = sub.add_parser("mcp", help="Run MCP stdio server")
    m.set_defaults(func=cmd_mcp)

    v = sub.add_parser("version", help="Print version")
    v.set_defaults(func=cmd_version)

    args = p.parse_args(argv)
    if getattr(args, "version", False) and not args.cmd:
        return cmd_version(args)
    if not args.cmd:
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
