"""Receipt Engine — honest accounting of token impact."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ReceiptMode(str, Enum):
    EXACT = "exact"
    ESTIMATED = "estimated"
    OBSERVED_ONLY = "observed_only"


@dataclass
class Receipt:
    mode: ReceiptMode
    tokens_before: int | None
    tokens_after: int | None
    tokens_saved: int | None
    pct_saved: float | None
    layer: str
    action: str
    task_id: str = ""
    success: bool | None = None
    notes: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_saved": self.tokens_saved,
            "pct_saved": self.pct_saved,
            "layer": self.layer,
            "action": self.action,
            "task_id": self.task_id,
            "success": self.success,
            "notes": self.notes,
            "meta": self.meta,
            "ts": self.ts,
        }


def make_estimated(
    *,
    tokens_before_est: int,
    tokens_after_est: int,
    layer: str,
    action: str,
    task_id: str = "",
    notes: str = "",
    success: bool | None = None,
    meta: dict[str, Any] | None = None,
) -> Receipt:
    saved = max(0, tokens_before_est - tokens_after_est)
    pct = (saved / tokens_before_est * 100.0) if tokens_before_est > 0 else 0.0
    return Receipt(
        mode=ReceiptMode.ESTIMATED,
        tokens_before=tokens_before_est,
        tokens_after=tokens_after_est,
        tokens_saved=saved,
        pct_saved=round(pct, 2),
        layer=layer,
        action=action,
        task_id=task_id,
        success=success,
        notes=notes or "Heuristic estimate (chars/4 or rule-based)",
        meta=meta or {},
    )


def make_exact(
    *,
    tokens_before: int,
    tokens_after: int,
    layer: str,
    action: str,
    task_id: str = "",
    notes: str = "",
    success: bool | None = None,
    meta: dict[str, Any] | None = None,
) -> Receipt:
    saved = max(0, tokens_before - tokens_after)
    pct = (saved / tokens_before * 100.0) if tokens_before > 0 else 0.0
    return Receipt(
        mode=ReceiptMode.EXACT,
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        tokens_saved=saved,
        pct_saved=round(pct, 2),
        layer=layer,
        action=action,
        task_id=task_id,
        success=success,
        notes=notes or "Measured token counts",
        meta=meta or {},
    )


def cost_per_successful_task(
    total_cost: float,
    successes: int,
    attempts: int,
) -> float | None:
    if successes <= 0:
        return None
    return total_cost / successes


def estimate_tokens(text: str) -> int:
    """Fast local estimate. Prefer provider counts when available."""
    return max(0, len(text) // 4)
