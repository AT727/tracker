from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from tracker.calibration.data import CalibrationData
from tracker.tracking.collector import TrackingCollector


class CsvExporter:
    HEADER_PREFIX = "# "

    def __init__(self, video_path: str, fps: float, frame_count: int,
                 calibration: Optional[CalibrationData] = None,
                 collector: Optional[TrackingCollector] = None):
        self._video_path = video_path
        self._fps = fps
        self._frame_count = frame_count
        self._calibration = calibration
        self._collector = collector or TrackingCollector()

    def _metadata_lines(self) -> List[str]:
        cal = self._calibration
        cal_info = f"scale={cal.scale} {cal.known_unit}/px, rotation={cal.axis_rotation_deg} deg" if cal else "None"
        return [
            f"{self.HEADER_PREFIX}Tracker Point Data Export",
            f"{self.HEADER_PREFIX}Exported: {datetime.now().isoformat()}",
            f"{self.HEADER_PREFIX}Video: {Path(self._video_path).name}",
            f"{self.HEADER_PREFIX}Frames: 0-{self._frame_count - 1}",
            f"{self.HEADER_PREFIX}FPS: {self._fps}",
            f"{self.HEADER_PREFIX}Calibration: {cal_info}",
        ]

    def write_standard(self, filepath: str):
        fields = ["frame", "timestamp", "x_pixel", "y_pixel", "x_world", "y_world", "track_id", "is_interpolated"]
        with open(filepath, "w", newline="") as f:
            for line in self._metadata_lines():
                f.write(line + "\n")
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for pt in self._collector:
                writer.writerow({
                    "frame": pt.frame,
                    "timestamp": pt.timestamp,
                    "x_pixel": pt.x_pixel,
                    "y_pixel": pt.y_pixel,
                    "x_world": pt.x_world,
                    "y_world": pt.y_world,
                    "track_id": pt.track_id,
                    "is_interpolated": pt.is_interpolated,
                })

    def write_full(self, filepath: str):
        fields = ["frame", "timestamp", "x_pixel", "y_pixel", "x_world", "y_world", "track_id", "is_interpolated"]
        lookup = {pt.frame: pt for pt in self._collector}
        with open(filepath, "w", newline="") as f:
            for line in self._metadata_lines():
                f.write(line + "\n")
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for frame_idx in range(self._frame_count):
                pt = lookup.get(frame_idx)
                writer.writerow({
                    "frame": frame_idx,
                    "timestamp": pt.timestamp if pt else "",
                    "x_pixel": pt.x_pixel if pt else "",
                    "y_pixel": pt.y_pixel if pt else "",
                    "x_world": pt.x_world if pt else "",
                    "y_world": pt.y_world if pt else "",
                    "track_id": pt.track_id if pt else "",
                    "is_interpolated": pt.is_interpolated if pt else "",
                })
