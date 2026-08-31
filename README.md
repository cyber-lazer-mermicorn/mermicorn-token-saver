# mermicorn-token-saver

**Highest-leverage AI-agent token control plane.**

Primary metric: **cost per successful task** — not raw token percentage.

Doctor diagnoses waste → Strategy Router selects the best layer action → Receipts account honestly → CLI processors cut command noise without losing errors or diffs.

Part of the [Mermicorn Grove](https://github.com/cyber-lazer-mermicorn) constellation.

## Why this exists

Agent token spend is dominated by:

1. **Code-read input** — full-file reads when a symbol slice would suffice (often 60–97% reducible)
2. **Command-output input** — progress bars, pass spam, download noise (60–99% on specialized tools)
3. **Prose output** — preambles and restated summaries (40–65%)
4. **Session shape** — unbounded tool loops and repeated large context

Most “token savers” attack one layer. This control plane diagnoses across layers and routes to the highest-leverage action, while measuring the metric that actually matters: cost per successful task.

## Quick start

```bash
# From repo root
python -m pip install -e ".[dev]"
mts diagnose -f path/to/large_cli_log.txt
mts compact -f path/to/pytest_output.txt --tool pytest --receipt
pytest -q
```

## Architecture

| Component | Role |
|-----------|------|
| **Doctor** | Deterministic waste rules (no LLM). Full-file, verbose CLI, chatty prose, oversized logs. |
| **Strategy Router** | Maps findings → layer + action (structural nav, CLI compact, terse prose, sub-agent isolate). |
| **Receipt Engine** | Exact / estimated / observed-only accounting + cost-per-successful-task helper. |
| **CLI Processors** | Content-aware compactors for git, pytest, npm, generic logs. Keep errors and diffs. |

## Design principles

- **First pass is last pass** — code ships runnable.
- **Deterministic core** — Doctor and CLI processors never call an LLM.
- **Honest receipts** — distinguish exact vs estimated savings.
- **Quality preserved** — never strip error/traceback/diff signal.
- **Proprietary** — all rights reserved; collaboration by discussion.

## Status

See [STATUS.md](STATUS.md). v0.1.0 is the working control-plane foundation: Doctor, Strategy, Receipts, CLI compactors, CLI, tests.

## License / rights

Proprietary — All Rights Reserved. See RIGHTS.md.
