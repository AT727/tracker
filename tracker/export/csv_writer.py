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
    video_name: str,
    fps: float,
) -> None:
    p = Path(path)
    calibrated = pipeline.calibration.is_calibrated
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([f"# video: {video_name}"])
        writer.writerow([f"# fps: {fps:.3f}"])
        if calibrated:
            scale = pipeline.calibration.scale_cm_per_px
            writer.writerow([f"# calibration: scale={scale:.6f} cm/px"])
        else:
            writer.writerow(["# calibration: uncalibrated"])
        writer.writerow(["frame", "timestamp", "series", "x", "y"])
        for mark in collector.marks:
            series = collector.get_series(mark.series_id)
            label = series.label if series else mark.series_id
            world = pipeline.pixel_to_world(mark.px, mark.py)
            writer.writerow(
                [
                    mark.frame,
                    f"{mark.timestamp_s:.6f}",
                    label,
                    f"{world.x:.6f}",
                    f"{world.y:.6f}",
                ]
            )
