"""CSV export per spec."""

from __future__ import annotations

import csv
from pathlib import Path

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.mutations import ColumnMutation, eval_formula
from tracker.tracking.collector import TrackingCollector


def export_csv(
    path: str | Path,
    collector: TrackingCollector,
    pipeline: CoordinatePipeline,
    mutations: list[ColumnMutation] | None = None,
) -> None:
    mutations = mutations or []
    p = Path(path)
    if not pipeline.calibration.is_calibrated:
        raise ValueError("Calibration is required before exporting CSV data in centimeters.")

    base_headers = ["frame", "t", "x (cm)", "y (cm)"]
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(base_headers + [m.name for m in mutations])
        for mark in collector.marks:
            world = pipeline.pixel_to_world(mark.px, mark.py)
            row = [
                mark.frame + 1,
                f"{mark.timestamp_s:.6f}",
                f"{world.x:.6f}",
                f"{world.y:.6f}",
            ]
            vars = {
                "x": world.x,
                "y": world.y,
                "t": mark.timestamp_s,
                "frame": float(mark.frame),
            }
            for mutation in mutations:
                try:
                    result = eval_formula(mutation.formula, vars)
                    row.append(f"{result:.6f}")
                except (ValueError, ZeroDivisionError):
                    row.append("ERR")
            writer.writerow(row)
