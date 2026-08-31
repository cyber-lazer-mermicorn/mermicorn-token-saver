# ARCHITECTURE

## Control loop

```
Session / tool output
        │
        ▼
   ┌─────────┐
   │ Doctor  │  deterministic findings
   └────┬────┘
        │
        ▼
 ┌──────────────┐
 │ Strategy     │  layer + action
 │ Router       │
 └──────┬───────┘
        │
        ├── structural_nav   → symbol index (planned)
        ├── cli_compact      → processors/cli.py
        ├── terse_prose      → policy (skill surface)
        ├── keep_errors_only → processors
        └── subagent_isolate → harness guidance
        │
        ▼
   ┌──────────┐
   │ Receipts │  exact | estimated | observed
   └──────────┘
```

## Primary metric

**Cost per successful task** = total spend ÷ number of tasks that meet the success bar.

Token % reduction is a supporting signal only.

## Layers

| Layer | Dominant waste | Highest-leverage response |
|-------|----------------|---------------------------|
| code_read | Full-file reads | Structural / symbol navigation |
| command_output | Progress, pass spam | Specialized CLI compactors |
| prose_output | Preambles, summaries | Terse policy |
| code_gen | Over-verbose generation | Focused generation policy |
| session | Loops, repeated context | Budgets + isolation |

## Constraints

- Doctor and CLI processors: zero LLM calls
- Never drop error / traceback / diff signal
- Receipts must label mode (exact vs estimated)
