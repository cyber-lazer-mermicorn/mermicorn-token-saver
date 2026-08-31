"""v0.2 tests — symbol index, session loops, apply, expanded processors."""

from __future__ import annotations

from mermicorn_token_saver.apply import apply_cli_text, apply_symbol_slice
from mermicorn_token_saver.doctor import diagnose_session, diagnose_text, WasteKind
from mermicorn_token_saver.index.symbols import index_source
from mermicorn_token_saver.processors.cli import compact_cli, detect_tool
from mermicorn_token_saver.receipts import make_estimated, cost_per_successful_task
from mermicorn_token_saver.session import SessionTracker
from mermicorn_token_saver.strategy import recommend, Action
from mermicorn_token_saver.mcp.server import handle


SAMPLE = '''
"""mod"""

def alpha(x, y):
    return x + y

class Beta:
    def method(self, z):
        return z

async def gamma():
    pass
'''


def test_symbol_index_finds_defs():
    idx = index_source(SAMPLE, path="sample.py")
    names = {s.name for s in idx.symbols}
    assert "alpha" in names
    assert "Beta" in names
    assert "method" in names
    assert "gamma" in names
    found = idx.find("alpha")
    assert found
    assert found[0].signature.startswith("alpha(")
    assert "x" in found[0].signature


def test_symbol_slice_saves_tokens():
    res = apply_symbol_slice(SAMPLE, path="sample.py", symbol_name="alpha")
    assert res.action_taken == "symbol_slice"
    assert "def alpha" in res.output
    assert res.receipt is not None
    assert res.receipt.tokens_after is not None
    assert res.receipt.tokens_before is not None
    assert res.receipt.tokens_after < res.receipt.tokens_before


def test_session_loop_detection():
    t = SessionTracker(repeat_threshold=3)
    for _ in range(5):
        t.record_tool("Bash", tokens_est=400)
    loops = t.detect_loops()
    assert loops
    assert loops[0].tool_name == "Bash"
    d = diagnose_session(t)
    assert any(f.kind == WasteKind.UNBOUNDED_TOOL_LOOP for f in d.findings)


def test_verbose_cli_and_strategy():
    blob = "Downloading\n" * 40 + "Progress:\n" * 40 + "npm WARN x\n" * 15
    d = diagnose_text(blob)
    assert d.findings
    recs = recommend(d)
    assert recs
    assert recs[0].action in (Action.CLI_COMPACT, Action.KEEP_ERRORS_ONLY)


def test_cargo_detect_and_compact():
    assert detect_tool("cargo test") == "cargo"
    raw = "Compiling foo v0.1.0\n" * 30 + "error: cannot find value\n" + "Finished test\n"
    out = compact_cli(raw, tool="cargo")
    assert "error" in out.lower()


def test_apply_cli_receipt():
    text = ".....s....\nFAILED t::x - AssertionError\nE AssertionError\n===== 1 failed =====\n" * 5
    res = apply_cli_text(text, tool="pytest")
    assert "FAILED" in res.output
    assert res.receipt is not None


def test_mcp_tools_list_and_diagnose():
    resp = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp is not None
    assert "tools" in resp["result"]
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "find_symbol" in names
    assert "compact_cli" in names

    resp2 = handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "index_symbols", "arguments": {"source": SAMPLE, "path": "s.py"}},
        }
    )
    assert resp2 is not None
    assert resp2["result"]["isError"] is False


def test_receipt_cpst():
    r = make_estimated(tokens_before_est=1000, tokens_after_est=250, layer="x", action="y")
    assert r.pct_saved == 75.0
    assert cost_per_successful_task(8.0, 4, 5) == 2.0
