"""Calibration data model."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class CalibrationData:
    """Stick endpoints, origin, and scale in cm per pixel."""

    stick_a_px: Optional[tuple[float, float]] = None
    stick_b_px: Optional[tuple[float, float]] = None
    known_length_cm: Optional[float] = None
    origin_px: Optional[tuple[float, float]] = None
    scale_cm_per_px: Optional[float] = None

    @property
    def is_calibrated(self) -> bool:
        return (
            self.stick_a_px is not None
            and self.stick_b_px is not None
            and self.known_length_cm is not None
            and self.known_length_cm > 0
            and self.origin_px is not None
            and self.scale_cm_per_px is not None
            and self.scale_cm_per_px > 0
        )

    @property
    def has_scale(self) -> bool:
        return self.scale_cm_per_px is not None and self.scale_cm_per_px > 0

    def compute_scale(self) -> None:
        """Derive scale_cm_per_px from stick endpoints and known length."""
        if (
            self.stick_a_px is None
            or self.stick_b_px is None
            or self.known_length_cm is None
            or self.known_length_cm <= 0
        ):
            self.scale_cm_per_px = None
            return
        dx = self.stick_b_px[0] - self.stick_a_px[0]
        dy = self.stick_b_px[1] - self.stick_a_px[1]
        px_dist = math.hypot(dx, dy)
        if px_dist <= 0:
            self.scale_cm_per_px = None
            return
        self.scale_cm_per_px = self.known_length_cm / px_dist
