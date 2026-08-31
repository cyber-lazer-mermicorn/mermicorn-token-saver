"""AST-based symbol index for Python (stdlib only).

Agents read full files when a 20–80 line symbol slice would suffice.
This index lets callers resolve name → definition without dumping the file.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str  # function | async_function | class | method | assign
    path: str
    lineno: int
    end_lineno: int
    qualname: str
    signature: str = ""

    @property
    def line_span(self) -> int:
        return max(1, self.end_lineno - self.lineno + 1)

    def slice_source(self, source: str) -> str:
        lines = source.splitlines()
        start = max(0, self.lineno - 1)
        end = min(len(lines), self.end_lineno)
        return "\n".join(lines[start:end])


@dataclass
class SymbolIndex:
    symbols: list[Symbol] = field(default_factory=list)
    by_name: dict[str, list[Symbol]] = field(default_factory=dict)
    by_path: dict[str, list[Symbol]] = field(default_factory=dict)

    def add(self, sym: Symbol) -> None:
        self.symbols.append(sym)
        self.by_name.setdefault(sym.name, []).append(sym)
        self.by_path.setdefault(sym.path, []).append(sym)

    def find(self, name: str) -> list[Symbol]:
        exact = self.by_name.get(name, [])
        if exact:
            return list(exact)
        low = name.lower()
        return [s for s in self.symbols if s.name.lower() == low or s.qualname.endswith("." + name)]

    def search(self, pattern: str) -> list[Symbol]:
        p = pattern.lower()
        return [s for s in self.symbols if p in s.name.lower() or p in s.qualname.lower()]

    def summary(self, max_items: int = 80) -> str:
        """Compact map suitable for agent context (signatures only)."""
        rows: list[str] = []
        for s in self.symbols[:max_items]:
            sig = s.signature or s.name
            rows.append(f"{s.kind:16} {s.qualname:40} L{s.lineno}-{s.end_lineno}  {sig}")
        if len(self.symbols) > max_items:
            rows.append(f"… {len(self.symbols) - max_items} more symbols")
        return "\n".join(rows)

    def estimated_full_file_tokens(self, path: str, source: str) -> int:
        return max(1, len(source) // 4)

    def estimated_symbol_tokens(self, sym: Symbol, source: str) -> int:
        return max(1, len(sym.slice_source(source)) // 4)


class _Collector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.symbols: list[Symbol] = []
        self._stack: list[str] = []

    def _qual(self, name: str) -> str:
        return ".".join(self._stack + [name]) if self._stack else name

    def _sig_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        args = []
        for a in node.args.args:
            args.append(a.arg)
        if node.args.vararg:
            args.append("*" + node.args.vararg.arg)
        for a in node.args.kwonlyargs:
            args.append(a.arg)
        if node.args.kwarg:
            args.append("**" + node.args.kwarg.arg)
        return f"{node.name}({', '.join(args)})"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        kind = "method" if self._stack else "function"
        self.symbols.append(
            Symbol(
                name=node.name,
                kind=kind,
                path=self.path,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno) or node.lineno,
                qualname=self._qual(node.name),
                signature=self._sig_func(node),
            )
        )
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        kind = "method" if self._stack else "async_function"
        self.symbols.append(
            Symbol(
                name=node.name,
                kind=kind,
                path=self.path,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno) or node.lineno,
                qualname=self._qual(node.name),
                signature=self._sig_func(node),
            )
        )
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))
            except Exception:
                bases.append("?")
        sig = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
        self.symbols.append(
            Symbol(
                name=node.name,
                kind="class",
                path=self.path,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno) or node.lineno,
                qualname=self._qual(node.name),
                signature=sig,
            )
        )
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()


def index_source(source: str, path: str = "<string>") -> SymbolIndex:
    idx = SymbolIndex()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return idx
    col = _Collector(path)
    col.visit(tree)
    for s in col.symbols:
        idx.add(s)
    return idx


def index_path(path: str | Path) -> SymbolIndex:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return index_source(text, path=str(p))


def index_tree(root: str | Path, patterns: Iterable[str] = ("**/*.py",)) -> SymbolIndex:
    root_p = Path(root)
    merged = SymbolIndex()
    for pat in patterns:
        for f in root_p.glob(pat):
            if not f.is_file():
                continue
            if any(part.startswith(".") for part in f.parts):
                continue
            if "venv" in f.parts or "node_modules" in f.parts or "__pycache__" in f.parts:
                continue
            try:
                sub = index_path(f)
            except OSError:
                continue
            for s in sub.symbols:
                merged.add(s)
    return merged
