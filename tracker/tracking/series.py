"""Named point series with label and color."""

from __future__ import annotations

from dataclasses import dataclass
import itertools

_DEFAULT_COLORS = [
    "#0a84ff",  # Blue
    "#30d158",  # Green
    "#ff453a",  # Red
    "#ff9f0a",  # Orange
    "#bf5af2",  # Purple
    "#ffd60a",  # Yellow
    "#5ac8fa",  # Light Blue
    "#ff2d55",  # Pink
]

_id_counter = itertools.count(1)


@dataclass
class PointSeries:
    id: str
    label: str
    color: str

    @classmethod
    def create(cls, label: str | None = None, color: str | None = None) -> PointSeries:
        idx = next(_id_counter)
        return cls(
            id=f"series-{idx}",
            label=label or f"Series {idx}",
            color=color or _DEFAULT_COLORS[(idx - 1) % len(_DEFAULT_COLORS)],
        )
