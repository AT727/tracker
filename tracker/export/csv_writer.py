"""CSV export per spec."""

from __future__ import annotations

import csv
from pathlib import Path

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.tracking.collector import TrackingCollector


def export_csv(
    path: str | Path,
    collector: TrackingCollector,
    pipeline: CoordinatePipeline,
) -> None:
    p = Path(path)
    if not pipeline.calibration.is_calibrated:
        raise ValueError("Calibration is required before exporting CSV data in centimeters.")

    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "t (s)", "x (cm)", "y (cm)"])
        for mark in collector.marks:
            world = pipeline.pixel_to_world(mark.px, mark.py)
            writer.writerow(
                [
                    mark.frame + 1,
                    f"{mark.timestamp_s:.6f}",
                    f"{world.x:.6f}",
                    f"{world.y:.6f}",
                ]
            )
