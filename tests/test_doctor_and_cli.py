"""First-pass tests — must pass on a clean checkout."""

from __future__ import annotations

from mermicorn_token_saver.doctor import diagnose_text, WasteKind
from mermicorn_token_saver.processors.cli import compact_cli, detect_tool
from mermicorn_token_saver.strategy import recommend, Action
from mermicorn_token_saver.receipts import make_estimated, cost_per_successful_task


def test_verbose_cli_detected():
    blob = "Downloading\n" * 50 + "Progress:\n" * 50 + "npm WARN something\n" * 20
    d = diagnose_text(blob)
    kinds = {f.kind for f in d.findings}
    assert WasteKind.VERBOSE_CLI in kinds or WasteKind.OVERSIZED_LOG in kinds


def test_chatty_prose_detected():
    text = "I'd be happy to help with that. Let me check that for you and provide a summary."
    d = diagnose_text(text)
    assert any(f.kind == WasteKind.CHATTY_PROSE for f in d.findings)


def test_pytest_keeps_failures():
    raw = (
        ".....s....\n"
        "FAILED tests/test_x.py::test_y - AssertionError: boom\n"
        "E       AssertionError: boom\n"
        "===== 1 failed, 10 passed in 2.1s =====\n"
    )
    out = compact_cli(raw, tool="pytest")
    assert "FAILED" in out
    assert "AssertionError" in out


def test_git_compact_preserves_diff_headers():
    raw = (
        "diff --git a/x.py b/x.py\n"
        "index 111..222 100644\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,3 +1,4 @@\n"
        "+new line\n"
        " unchanged\n"
    )
    out = compact_cli(raw, tool="git")
    assert "diff --git" in out
    assert "+new line" in out


def test_detect_tool():
    assert detect_tool("pytest -q") == "pytest"
    assert detect_tool("git status") == "git"
    assert detect_tool("npm install") == "npm"


def test_strategy_routes_full_file():
    from mermicorn_token_saver.doctor import Finding, Diagnosis, WasteKind

    d = Diagnosis()
    d.add(
        Finding(
            kind=WasteKind.FULL_FILE_READ,
            severity=4,
            evidence="lines=800",
            estimated_tokens=2000,
            remediation_hint="symbol nav",
        )
    )
    recs = recommend(d)
    assert recs
    assert recs[0].action == Action.STRUCTURAL_NAV


def test_receipt_and_cpst():
    r = make_estimated(
        tokens_before_est=1000,
        tokens_after_est=300,
        layer="command_output",
        action="cli_compact",
    )
    assert r.tokens_saved == 700
    assert r.pct_saved == 70.0
    assert cost_per_successful_task(10.0, successes=5, attempts=7) == 2.0
    assert cost_per_successful_task(10.0, successes=0, attempts=3) is None
