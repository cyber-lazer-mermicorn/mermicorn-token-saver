# ARCHITECTURE — v0.2

## Control loop

```
tool output / source file / session events
            │
            ▼
       ┌─────────┐
       │ Doctor  │
       └────┬────┘
            ▼
     ┌─────────────┐
     │  Strategy   │
     └──────┬──────┘
            │
   ┌────────┼────────────────────┐
   ▼        ▼                    ▼
 symbol   cli_compact      subagent_isolate
 slice    keep_errors      terse_prose
   │        │
   ▼        ▼
     ┌──────────┐
     │  Apply   │ → output + Receipt
     └──────────┘
```

## Symbol index (code-read lever)

Python `ast` only. Builds qualname → line range → signature.  
`find_symbol` / `mts symbol` returns a header + slice so agents never need the full file when a definition is enough.

## Session tracker

Sliding window of tool events. Flags consecutive repeats ≥ threshold and high-frequency tools in-window. Feeds Doctor as `UNBOUNDED_TOOL_LOOP`.

## MCP

JSON-RPC 2.0 subset over stdio. No SDK dependency. Tools return structured JSON inside MCP content text for maximum client compatibility.

## Metric

`cost_per_successful_task = total_cost / successes`  
Token % is supporting evidence only; receipts label exact vs estimated.
