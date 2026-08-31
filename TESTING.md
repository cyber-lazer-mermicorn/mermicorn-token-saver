# Testing mermicorn-token-saver v0.2

## Install

```bash
git clone https://github.com/cyber-lazer-mermicorn/mermicorn-token-saver.git
cd mermicorn-token-saver
python -m pip install -e ".[dev]"
```

## Automated tests

```bash
pytest -q
# expect: 8 passed
```

## Manual smoke

```bash
mts version
# 0.2.0

mts index -f src/mermicorn_token_saver/doctor.py
mts symbol -f src/mermicorn_token_saver/doctor.py -n diagnose_text --receipt
mts session-demo --tool Bash --repeats 5 --threshold 3
mts diagnose -f src/mermicorn_token_saver/doctor.py
```

## MCP (optional)

```bash
# MCP client config:
# "command": "python", "args": ["-m", "mermicorn_token_saver.mcp.server"]
mts mcp
```
