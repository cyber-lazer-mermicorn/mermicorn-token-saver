"""CLI entry — diagnose, recommend, compact, receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .doctor import diagnose_text
from .processors.cli import compact_cli, detect_tool
from .receipts import make_estimated
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
    before = len(text) // 4
    compacted = compact_cli(text, tool=tool)
    after = len(compacted) // 4
    receipt = make_estimated(
        tokens_before_est=before,
        tokens_after_est=after,
        layer="command_output",
        action="cli_compact",
        notes=f"tool={tool}",
    )
    if args.receipt:
        print(json.dumps(receipt.to_dict(), indent=2), file=sys.stderr)
    sys.stdout.write(compacted)
    if not compacted.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_version(_: argparse.Namespace) -> int:
    print(__version__)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="mts",
        description="Mermicorn Token Saver — Doctor · Strategy · Receipts · CLI compactors",
    )
    p.add_argument("--version", action="store_true", help="Print version")
    sub = p.add_subparsers(dest="cmd")

    d = sub.add_parser("diagnose", help="Run Doctor on a file or stdin")
    d.add_argument("-f", "--file", help="Input file (default: stdin)")
    d.set_defaults(func=cmd_diagnose)

    c = sub.add_parser("compact", help="Compact CLI/log output")
    c.add_argument("-f", "--file", help="Input file (default: stdin)")
    c.add_argument("-t", "--tool", choices=["git", "pytest", "npm", "generic"], help="Force tool profile")
    c.add_argument("--command", help="Original command string for tool detection")
    c.add_argument("--receipt", action="store_true", help="Emit estimated receipt to stderr")
    c.set_defaults(func=cmd_compact)

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
