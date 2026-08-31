"""Strategy Router — map Doctor findings to the highest-leverage action."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .doctor import Diagnosis, Finding, WasteKind


class Layer(str, Enum):
    CODE_READ = "code_read"
    COMMAND_OUTPUT = "command_output"
    PROSE_OUTPUT = "prose_output"
    CODE_GEN = "code_gen"
    SESSION = "session"


class Action(str, Enum):
    STRUCTURAL_NAV = "structural_nav"
    CLI_COMPACT = "cli_compact"
    TERSE_PROSE = "terse_prose"
    KEEP_ERRORS_ONLY = "keep_errors_only"
    SUBAGENT_ISOLATE = "subagent_isolate"
    SYMBOL_SLICE = "symbol_slice"
    NO_OP = "no_op"


@dataclass(frozen=True)
class Recommendation:
    layer: Layer
    action: Action
    priority: int
    finding: Finding
    rationale: str


_KIND_TO_ACTION: dict[WasteKind, tuple[Layer, Action, int, str]] = {
    WasteKind.SYMBOL_AVAILABLE: (
        Layer.CODE_READ,
        Action.SYMBOL_SLICE,
        98,
        "Named symbol exists; slice beats full-file by a large margin on measured suites",
    ),
    WasteKind.FULL_FILE_READ: (
        Layer.CODE_READ,
        Action.STRUCTURAL_NAV,
        90,
        "Full-file reads dominate input cost; symbol navigation cuts 60–97% in measured suites",
    ),
    WasteKind.VERBOSE_CLI: (
        Layer.COMMAND_OUTPUT,
        Action.CLI_COMPACT,
        85,
        "CLI progress/pass noise is pure waste; specialized processors keep errors/diffs only",
    ),
    WasteKind.OVERSIZED_LOG: (
        Layer.COMMAND_OUTPUT,
        Action.KEEP_ERRORS_ONLY,
        80,
        "Large logs: retain traceback/error slices, drop progress bars and passed suites",
    ),
    WasteKind.CHATTY_PROSE: (
        Layer.PROSE_OUTPUT,
        Action.TERSE_PROSE,
        70,
        "Agent preamble and restated summaries add tokens with zero task signal",
    ),
    WasteKind.REPEATED_CONTEXT: (
        Layer.SESSION,
        Action.SUBAGENT_ISOLATE,
        75,
        "Repeated large context is better isolated in a sub-agent that returns a short summary",
    ),
    WasteKind.CACHE_DRIFT: (
        Layer.SESSION,
        Action.NO_OP,
        40,
        "Cache drift is an observability signal; fix by stable prompt prefixes and model affinity",
    ),
    WasteKind.UNBOUNDED_TOOL_LOOP: (
        Layer.SESSION,
        Action.SUBAGENT_ISOLATE,
        95,
        "Unbounded tool loops multiply cost; hard budgets + isolation prevent runaway bills",
    ),
}


def recommend(diagnosis: Diagnosis) -> list[Recommendation]:
    out: list[Recommendation] = []
    for f in diagnosis.findings:
        mapping = _KIND_TO_ACTION.get(f.kind)
        if not mapping:
            continue
        layer, action, base_pri, rationale = mapping
        pri = base_pri + f.severity
        out.append(
            Recommendation(
                layer=layer,
                action=action,
                priority=pri,
                finding=f,
                rationale=rationale,
            )
        )
    out.sort(key=lambda r: r.priority, reverse=True)
    return out


def primary_action(diagnosis: Diagnosis) -> Recommendation | None:
    recs = recommend(diagnosis)
    return recs[0] if recs else None
