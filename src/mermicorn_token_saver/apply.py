"""Apply pipeline — diagnose → recommend → act → receipt.

End-to-end path so the control plane is not advisory-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .doctor import Diagnosis, diagnose_text, rule_symbol_available
from .index.symbols import index_source
from .processors.cli import compact_cli, detect_tool
from .receipts import Receipt, estimate_tokens, make_estimated
from .strategy import Action, Recommendation, recommend


@dataclass
class ApplyResult:
    diagnosis: Diagnosis
    recommendations: list[Recommendation]
    output: str
    receipt: Receipt | None
    action_taken: str


def apply_cli_text(text: str, *, tool: str | None = None, command: str = "") -> ApplyResult:
    d = diagnose_text(text)
    recs = recommend(d)
    chosen_tool = tool or detect_tool(command or text)
    before = estimate_tokens(text)
    compacted = compact_cli(text, tool=chosen_tool)
    after = estimate_tokens(compacted)
    receipt = make_estimated(
        tokens_before_est=before,
        tokens_after_est=after,
        layer="command_output",
        action="cli_compact",
        notes=f"tool={chosen_tool}",
        meta={"tool": chosen_tool},
    )
    return ApplyResult(
        diagnosis=d,
        recommendations=recs,
        output=compacted,
        receipt=receipt,
        action_taken="cli_compact",
    )


def apply_symbol_slice(
    source: str,
    *,
    path: str = "<string>",
    symbol_name: str,
) -> ApplyResult:
    idx = index_source(source, path=path)
    matches = idx.find(symbol_name)
    d = diagnose_text(source, path_hint=path, line_count=source.count("\n") + 1)
    if matches:
        sym = matches[0]
        f = rule_symbol_available(path, source, sym.name, sym.line_span)
        if f:
            d.add(f)
    recs = recommend(d)
    before = estimate_tokens(source)
    if not matches:
        receipt = make_estimated(
            tokens_before_est=before,
            tokens_after_est=before,
            layer="code_read",
            action="symbol_slice",
            notes=f"symbol {symbol_name!r} not found; returned full source",
        )
        return ApplyResult(d, recs, source, receipt, "no_op")
    sym = matches[0]
    sliced = sym.slice_source(source)
    header = f"# symbol {sym.qualname} ({sym.kind}) {path}:{sym.lineno}-{sym.end_lineno}\n"
    out = header + sliced
    after = estimate_tokens(out)
    receipt = make_estimated(
        tokens_before_est=before,
        tokens_after_est=after,
        layer="code_read",
        action="symbol_slice",
        notes=f"sliced {sym.qualname} from {path}",
        meta={"symbol": sym.qualname, "lines": sym.line_span},
    )
    return ApplyResult(d, recs, out, receipt, "symbol_slice")


def apply_file(
    path: str | Path,
    *,
    mode: str = "auto",
    symbol: str | None = None,
    tool: str | None = None,
) -> ApplyResult:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    if mode == "symbol" or (mode == "auto" and symbol):
        if not symbol:
            raise ValueError("symbol name required for symbol mode")
        return apply_symbol_slice(text, path=str(p), symbol_name=symbol)
    if mode in ("cli", "auto"):
        if symbol and p.suffix == ".py":
            return apply_symbol_slice(text, path=str(p), symbol_name=symbol)
        return apply_cli_text(text, tool=tool)
    return apply_cli_text(text, tool=tool)
