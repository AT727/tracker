"""Pixel to world coordinate transform (cm, Y-up, no rotation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tracker.calibration.data import CalibrationData


@dataclass(frozen=True)
class WorldPoint:
    x: float
    y: float
    calibrated: bool


class CoordinatePipeline:
    """Transform raw pixel marks to display/export coordinates."""

    def __init__(self, calibration: Optional[CalibrationData] = None) -> None:
        self._calibration = calibration or CalibrationData()

    @property
    def calibration(self) -> CalibrationData:
        return self._calibration

    def set_calibration(self, calibration: CalibrationData) -> None:
        self._calibration = calibration

    @property
    def unit_suffix(self) -> str:
        return "cm" if self._calibration.is_calibrated else "(px)"

    def pixel_to_world(self, px: float, py: float) -> WorldPoint:
        if not self._calibration.is_calibrated:
            return WorldPoint(x=px, y=py, calibrated=False)

        ox, oy = self._calibration.origin_px  # type: ignore[misc]
        scale = self._calibration.scale_cm_per_px  # type: ignore[assignment]
        x_cm = (px - ox) * scale
        y_cm = -(py - oy) * scale
        return WorldPoint(x=x_cm, y=y_cm, calibrated=True)
