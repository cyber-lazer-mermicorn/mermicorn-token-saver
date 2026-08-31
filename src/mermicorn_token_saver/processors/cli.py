"""Specialized CLI compactors for high-frequency agent tool output."""

from __future__ import annotations

import re
from typing import Callable


def _keep_lines(text: str, predicate: Callable[[str], bool]) -> str:
    lines = text.splitlines()
    kept = [ln for ln in lines if predicate(ln)]
    if not kept and lines:
        kept = lines[-min(8, len(lines)) :]
    return "\n".join(kept)


def compact_git(text: str) -> str:
    if len(text) < 1200:
        return text

    def pred(ln: str) -> bool:
        s = ln.strip()
        if not s:
            return False
        if s.startswith(("diff --git", "index ", "--- ", "+++ ", "@@")):
            return True
        if s.startswith(("+", "-")) and not s.startswith(("+++", "---")):
            return True
        if re.match(r"^(M|A|D|R|C|\?\?)\s", s):
            return True
        if s.startswith(("commit ", "Author:", "Date:", "Merge:")):
            return True
        if "error" in s.lower() or "fatal" in s.lower():
            return True
        return False

    out = _keep_lines(text, pred)
    return out if out.strip() else text[:2000]


def compact_pytest(text: str) -> str:
    if len(text) < 1500:
        return text
    failure_block = False
    kept: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if re.search(r"\b(FAILED|ERROR|FAILURES|ERRORS)\b", s):
            failure_block = True
            kept.append(ln)
            continue
        if failure_block:
            if s.startswith("=") and "short test summary" in s.lower():
                failure_block = False
            kept.append(ln)
            continue
        if re.search(r"\b(passed|failed|error|warnings?)\b", s, re.I) and (
            "in " in s or s.startswith("=")
        ):
            kept.append(ln)
            continue
        if "Traceback" in ln or ln.startswith("E ") or "AssertionError" in ln:
            kept.append(ln)
    if not kept:
        return text[-2500:]
    return "\n".join(kept)


def compact_npm(text: str) -> str:
    if len(text) < 1000:
        return text

    def pred(ln: str) -> bool:
        s = ln.strip()
        if not s:
            return False
        low = s.lower()
        if any(x in low for x in ("error", "err!", "failed", "warn")):
            return True
        if s.startswith(("added ", "removed ", "changed ", "audited ")):
            return True
        if "vulnerabilit" in low:
            return True
        return False

    out = _keep_lines(text, pred)
    return out if out.strip() else text[:1500]


def compact_generic_log(text: str) -> str:
    if len(text) < 2000:
        return text

    def pred(ln: str) -> bool:
        low = ln.lower()
        if any(k in low for k in ("error", "exception", "traceback", "fatal", "failed", "critical")):
            return True
        if ln.strip().startswith("E ") or "AssertionError" in ln:
            return True
        return False

    out = _keep_lines(text, pred)
    if len(out) < 80:
        lines = text.splitlines()
        head = lines[:40]
        tail = lines[-40:] if len(lines) > 80 else []
        return "\n".join(head + (["…"] if tail else []) + tail)
    return out


PROCESSORS: dict[str, Callable[[str], str]] = {
    "git": compact_git,
    "pytest": compact_pytest,
    "npm": compact_npm,
    "generic": compact_generic_log,
}


def detect_tool(command_or_text: str) -> str:
    c = command_or_text.lower()
    if "pytest" in c or "py.test" in c:
        return "pytest"
    if c.strip().startswith("git ") or "diff --git" in c:
        return "git"
    if "npm " in c or "yarn " in c or "pnpm " in c:
        return "npm"
    return "generic"


def compact_cli(text: str, tool: str | None = None) -> str:
    key = tool or detect_tool(text)
    fn = PROCESSORS.get(key, compact_generic_log)
    return fn(text)
