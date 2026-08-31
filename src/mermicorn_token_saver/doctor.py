"""Doctor — deterministic waste diagnosis for AI-agent sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from .session import LoopFinding, SessionTracker


class WasteKind(str, Enum):
    FULL_FILE_READ = "full_file_read"
    VERBOSE_CLI = "verbose_cli"
    REPEATED_CONTEXT = "repeated_context"
    CHATTY_PROSE = "chatty_prose"
    OVERSIZED_LOG = "oversized_log"
    CACHE_DRIFT = "cache_drift"
    UNBOUNDED_TOOL_LOOP = "unbounded_tool_loop"
    SYMBOL_AVAILABLE = "symbol_available"


@dataclass(frozen=True)
class Finding:
    kind: WasteKind
    severity: int
    evidence: str
    estimated_tokens: int
    remediation_hint: str


@dataclass
class Diagnosis:
    findings: list[Finding] = field(default_factory=list)
    total_estimated_waste: int = 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)
        self.total_estimated_waste += max(0, finding.estimated_tokens)


_CLI_NOISE_MARKERS = (
    "Downloading",
    "Progress:",
    "=======",
    "----",
    "npm WARN",
    "passed in",
    "Collecting ",
    "Building wheel",
    "Compiling ",
    "Finished `",
)

_CHATTY_MARKERS = (
    "I'd be happy to help",
    "Let me check that for you",
    "Here's a summary of what I did",
    "Sure, I can assist",
    "I'll walk you through",
    "Of course!",
    "Great question",
)


def rule_verbose_cli(text: str, threshold: int = 800) -> Finding | None:
    if len(text) < threshold:
        return None
    hits = sum(1 for m in _CLI_NOISE_MARKERS if m in text)
    if hits < 2 and len(text) < 4000:
        return None
    est = max(200, len(text) // 4)
    return Finding(
        kind=WasteKind.VERBOSE_CLI,
        severity=min(5, 2 + hits),
        evidence=f"CLI output length={len(text)} chars, noise_markers={hits}",
        estimated_tokens=est,
        remediation_hint="Route through CLI processor (git/pytest/npm/cargo compactors)",
    )


def rule_chatty_prose(text: str) -> Finding | None:
    hits = [m for m in _CHATTY_MARKERS if m.lower() in text.lower()]
    if not hits:
        return None
    est = max(80, len(text) // 6)
    return Finding(
        kind=WasteKind.CHATTY_PROSE,
        severity=2 + min(2, len(hits)),
        evidence=f"chatty_markers={hits[:3]}",
        estimated_tokens=est,
        remediation_hint="Apply terse / caveman policy for prose output",
    )


def rule_oversized_log(text: str, threshold: int = 6000) -> Finding | None:
    if len(text) < threshold:
        return None
    has_error = any(x in text for x in ("Traceback", "ERROR", "FAILED", "Exception", "error:"))
    severity = 3 if has_error else 4
    est = len(text) // 4
    return Finding(
        kind=WasteKind.OVERSIZED_LOG,
        severity=severity,
        evidence=f"log_chars={len(text)}, has_error_signal={has_error}",
        estimated_tokens=est,
        remediation_hint="Keep error/traceback slices; drop progress and passed suites",
    )


def rule_full_file_heuristic(path_hint: str, content: str, line_count: int) -> Finding | None:
    if line_count < 200:
        return None
    est = max(300, len(content) // 4)
    return Finding(
        kind=WasteKind.FULL_FILE_READ,
        severity=4 if line_count > 500 else 3,
        evidence=f"path={path_hint!r} lines={line_count}",
        estimated_tokens=est,
        remediation_hint="Prefer symbol/index navigation over full-file cat",
    )


def rule_symbol_available(
    path_hint: str,
    content: str,
    symbol_name: str,
    symbol_lines: int,
) -> Finding | None:
    full_lines = content.count("\n") + 1
    if symbol_lines <= 0 or full_lines < 120:
        return None
    if symbol_lines >= full_lines * 0.5:
        return None
    waste = max(0, (len(content) // 4) - max(40, symbol_lines * 8))
    return Finding(
        kind=WasteKind.SYMBOL_AVAILABLE,
        severity=5 if full_lines > 400 else 4,
        evidence=f"path={path_hint!r} full_lines={full_lines} symbol={symbol_name!r} symbol_lines={symbol_lines}",
        estimated_tokens=waste,
        remediation_hint=f"Use symbol slice for {symbol_name!r} instead of full file",
    )


def rule_from_loop(loop: LoopFinding) -> Finding:
    return Finding(
        kind=WasteKind.UNBOUNDED_TOOL_LOOP,
        severity=5 if loop.consecutive >= 6 else 4,
        evidence=loop.message,
        estimated_tokens=loop.estimated_wasted_tokens,
        remediation_hint="Hard budget + sub-agent isolation; stop repeating the same tool",
    )


def diagnose_text(text: str, *, path_hint: str = "", line_count: int = 0) -> Diagnosis:
    d = Diagnosis()
    for rule in (
        lambda t: rule_verbose_cli(t),
        lambda t: rule_chatty_prose(t),
        lambda t: rule_oversized_log(t),
    ):
        f = rule(text)
        if f:
            d.add(f)
    if path_hint and line_count:
        f = rule_full_file_heuristic(path_hint, text, line_count)
        if f:
            d.add(f)
    return d


def diagnose_session(tracker: SessionTracker) -> Diagnosis:
    d = Diagnosis()
    for loop in tracker.detect_loops():
        d.add(rule_from_loop(loop))
    return d


def diagnose_batch(blobs: Sequence[tuple[str, str, int]]) -> Diagnosis:
    merged = Diagnosis()
    for path, text, lines in blobs:
        sub = diagnose_text(text, path_hint=path, line_count=lines)
        for f in sub.findings:
            merged.add(f)
    return merged
