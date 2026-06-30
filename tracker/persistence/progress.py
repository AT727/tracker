"""Save/load tracking progress via {video_stem}.tracker.json sidecar."""

from __future__ import annotations

import json
from pathlib import Path

from tracker.tracking.collector import TrackingCollector
from tracker.tracking.mark import Mark
from tracker.tracking.series import PointSeries


class ProgressStore:
    @staticmethod
    def save(path: str | Path, collector: TrackingCollector) -> None:
        p = Path(path)
        payload = {
            "version": 1,
            "active_series_id": collector.active_series_id,
            "series": [
                {
                    "id": s.id,
                    "label": s.label,
                    "color": s.color,
                }
                for s in collector.series
            ],
            "marks": [
                {
                    "frame": m.frame,
                    "timestamp_s": m.timestamp_s,
                    "px": m.px,
                    "py": m.py,
                    "series_id": m.series_id,
                }
                for m in collector.marks
            ],
        }
        with p.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @staticmethod
    def load(path: str | Path) -> dict | None:
        p = Path(path)
        if not p.is_file():
            return None
        try:
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        version = data.get("version", 1)
        if version != 1:
            return None

        series_list = data.get("series", [])
        marks_list = data.get("marks", [])
        active_series_id = data.get("active_series_id")

        return {
            "series": series_list,
            "marks": marks_list,
            "active_series_id": active_series_id,
        }
