"""Load/save {video_stem}.json beside the MP4."""

from __future__ import annotations

import json
from pathlib import Path

from tracker.calibration.data import CalibrationData


def sidecar_path_for_video(video_path: str | Path) -> Path:
    video = Path(video_path)
    return video.with_suffix(".json")


class CalibrationStore:
    @staticmethod
    def load(path: str | Path) -> CalibrationData | None:
        p = Path(path)
        if not p.is_file():
            return None
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        cal = CalibrationData(
            stick_a_px=_tuple_or_none(data.get("stick_a_px")),
            stick_b_px=_tuple_or_none(data.get("stick_b_px")),
            known_length_cm=data.get("known_length_cm"),
            origin_px=_tuple_or_none(data.get("origin_px")),
            scale_cm_per_px=data.get("scale_cm_per_px"),
        )
        if cal.scale_cm_per_px is None and cal.stick_a_px and cal.stick_b_px:
            cal.compute_scale()
        return cal

    @staticmethod
    def save(path: str | Path, calibration: CalibrationData) -> None:
        p = Path(path)
        payload = {
            "stick_a_px": list(calibration.stick_a_px) if calibration.stick_a_px else None,
            "stick_b_px": list(calibration.stick_b_px) if calibration.stick_b_px else None,
            "known_length_cm": calibration.known_length_cm,
            "origin_px": list(calibration.origin_px) if calibration.origin_px else None,
            "scale_cm_per_px": calibration.scale_cm_per_px,
        }
        with p.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)


def _tuple_or_none(value) -> tuple[float, float] | None:
    if value is None:
        return None
    return float(value[0]), float(value[1])
