"""Named point series with label and color."""

from __future__ import annotations

from dataclasses import dataclass
import itertools

_DEFAULT_COLORS = [
    "#e41a1c",
    "#377eb8",
    "#4daf4a",
    "#984ea3",
    "#ff7f00",
    "#a65628",
    "#f781bf",
    "#999999",
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
