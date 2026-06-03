"""Single tracking mark at a frame."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mark:
    frame: int
    timestamp_s: float
    px: float
    py: float
    series_id: str
