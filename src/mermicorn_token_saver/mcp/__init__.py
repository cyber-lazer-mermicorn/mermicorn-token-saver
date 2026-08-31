"""MCP stdio server — zero hard dependency; pure JSON-RPC tools over stdin/stdout."""

from .server import main as mcp_main

__all__ = ["mcp_main"]
