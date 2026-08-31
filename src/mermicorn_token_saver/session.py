"""Session event stream + unbounded-loop detector.

Tracks tool-call patterns without an LLM. Flags runaway repeats that multiply cost.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque


@dataclass(frozen=True)
class SessionEvent:
    kind: str  # tool | message | compact | error
    name: str
    tokens_est: int = 0
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    meta: dict = field(default_factory=dict)


@dataclass
class LoopFinding:
    tool_name: str
    consecutive: int
    total: int
    estimated_wasted_tokens: int
    message: str


@dataclass
class SessionTracker:
    """Sliding-window tracker for agent tool loops."""

    window: int = 40
    repeat_threshold: int = 4
    events: Deque[SessionEvent] = field(default_factory=deque)
    total_tokens_est: int = 0

    def __post_init__(self) -> None:
        self.events = deque(maxlen=self.window)

    def record(self, event: SessionEvent) -> None:
        self.events.append(event)
        self.total_tokens_est += max(0, event.tokens_est)

    def record_tool(self, name: str, tokens_est: int = 0, **meta: object) -> None:
        self.record(SessionEvent(kind="tool", name=name, tokens_est=tokens_est, meta=dict(meta)))

    def detect_loops(self) -> list[LoopFinding]:
        findings: list[LoopFinding] = []
        tool_events = [e for e in self.events if e.kind == "tool"]
        if not tool_events:
            return findings

        i = 0
        while i < len(tool_events):
            name = tool_events[i].name
            j = i + 1
            while j < len(tool_events) and tool_events[j].name == name:
                j += 1
            streak = j - i
            if streak >= self.repeat_threshold:
                waste = sum(e.tokens_est for e in tool_events[i:j])
                findings.append(
                    LoopFinding(
                        tool_name=name,
                        consecutive=streak,
                        total=sum(1 for e in tool_events if e.name == name),
                        estimated_wasted_tokens=waste,
                        message=(
                            f"Tool {name!r} repeated {streak} consecutive times "
                            f"(threshold={self.repeat_threshold}); likely unbounded loop"
                        ),
                    )
                )
            i = j

        counts = Counter(e.name for e in tool_events)
        for name, n in counts.items():
            if n >= self.repeat_threshold * 2:
                if any(f.tool_name == name and f.consecutive >= self.repeat_threshold for f in findings):
                    continue
                waste = sum(e.tokens_est for e in tool_events if e.name == name)
                findings.append(
                    LoopFinding(
                        tool_name=name,
                        consecutive=0,
                        total=n,
                        estimated_wasted_tokens=waste,
                        message=f"Tool {name!r} invoked {n} times in window of {len(tool_events)}",
                    )
                )
        return findings

    def to_dict(self) -> dict:
        return {
            "window": self.window,
            "event_count": len(self.events),
            "total_tokens_est": self.total_tokens_est,
            "loops": [
                {
                    "tool": f.tool_name,
                    "consecutive": f.consecutive,
                    "total": f.total,
                    "estimated_wasted_tokens": f.estimated_wasted_tokens,
                    "message": f.message,
                }
                for f in self.detect_loops()
            ],
        }
