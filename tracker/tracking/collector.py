"""Append-only mark collection with point series management."""

from __future__ import annotations

from typing import Iterable, Optional

from tracker.tracking.mark import Mark
from tracker.tracking.series import PointSeries


class TrackingCollector:
    def __init__(self) -> None:
        self._series: dict[str, PointSeries] = {}
        self._marks: list[Mark] = []
        self._active_series_id: Optional[str] = None
        self._ensure_default_series()

    def _ensure_default_series(self) -> None:
        if not self._series:
            default = PointSeries.create("Series 1")
            self._series[default.id] = default
            self._active_series_id = default.id

    @property
    def series(self) -> list[PointSeries]:
        return list(self._series.values())

    @property
    def active_series_id(self) -> Optional[str]:
        return self._active_series_id

    @property
    def marks(self) -> list[Mark]:
        return list(self._marks)

    def get_series(self, series_id: str) -> Optional[PointSeries]:
        return self._series.get(series_id)

    def add_series(self, label: str | None = None, color: str | None = None) -> PointSeries:
        s = PointSeries.create(label=label, color=color)
        self._series[s.id] = s
        self._active_series_id = s.id
        return s

    def set_active_series(self, series_id: str) -> None:
        if series_id not in self._series:
            raise KeyError(f"Unknown series: {series_id}")
        self._active_series_id = series_id

    def append_mark(
        self,
        frame: int,
        timestamp_s: float,
        px: float,
        py: float,
        series_id: str | None = None,
    ) -> Mark:
        sid = series_id or self._active_series_id
        if sid is None or sid not in self._series:
            raise ValueError("No active series")
        mark = Mark(frame=frame, timestamp_s=timestamp_s, px=px, py=py, series_id=sid)
        self._marks.append(mark)
        return mark

    def upsert_mark(
        self,
        frame: int,
        timestamp_s: float,
        px: float,
        py: float,
        series_id: str | None = None,
    ) -> tuple[Mark, bool]:
        """Insert or replace a mark for one (series, frame) pair."""
        sid = series_id or self._active_series_id
        if sid is None or sid not in self._series:
            raise ValueError("No active series")
        mark = Mark(frame=frame, timestamp_s=timestamp_s, px=px, py=py, series_id=sid)
        match_indices = [
            idx
            for idx, existing in enumerate(self._marks)
            if existing.series_id == sid and existing.frame == frame
        ]
        if not match_indices:
            self._marks.append(mark)
            return mark, False

        # Replace the newest existing mark and drop older duplicates so each
        # (series, frame) pair remains unique.
        replace_at = match_indices[-1]
        self._marks[replace_at] = mark
        for idx in reversed(match_indices[:-1]):
            del self._marks[idx]
        return mark, True

    def marks_for_series(self, series_id: str) -> list[Mark]:
        return [m for m in self._marks if m.series_id == series_id]

    def clear_marks(self) -> None:
        self._marks.clear()

    def iter_marks(self) -> Iterable[Mark]:
        return iter(self._marks)
