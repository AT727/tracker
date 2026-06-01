from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class CalibrationData:
    stick_endpoint_a_px: Tuple[float, float]
    stick_endpoint_b_px: Tuple[float, float]
    known_length: float
    known_unit: str
    origin_px: Tuple[float, float]
    axis_rotation_deg: float
    pixel_distance: float
    scale: float
    video_frame0_hash: str = ""

    @classmethod
    def from_endpoints(
        cls,
        endpoint_a: Tuple[float, float],
        endpoint_b: Tuple[float, float],
        known_length: float,
        unit: str = "m",
    ) -> "CalibrationData":
        dx = endpoint_b[0] - endpoint_a[0]
        dy = endpoint_b[1] - endpoint_a[1]
        pixel_distance = (dx**2 + dy**2) ** 0.5
        if pixel_distance == 0:
            raise ValueError("Endpoints are identical; pixel_distance must be > 0")
        scale = known_length / pixel_distance
        return cls(
            stick_endpoint_a_px=endpoint_a,
            stick_endpoint_b_px=endpoint_b,
            known_length=known_length,
            known_unit=unit,
            origin_px=(0.0, 0.0),
            axis_rotation_deg=0.0,
            pixel_distance=pixel_distance,
            scale=scale,
        )

    @property
    def is_valid(self) -> bool:
        return self.pixel_distance > 0 and self.scale > 0

    def to_dict(self) -> dict:
        return {
            "stick_endpoint_a_px": list(self.stick_endpoint_a_px),
            "stick_endpoint_b_px": list(self.stick_endpoint_b_px),
            "known_length": self.known_length,
            "known_unit": self.known_unit,
            "origin_px": list(self.origin_px),
            "axis_rotation_deg": self.axis_rotation_deg,
            "pixel_distance": self.pixel_distance,
            "scale": self.scale,
            "video_frame0_hash": self.video_frame0_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationData":
        return cls(
            stick_endpoint_a_px=tuple(data["stick_endpoint_a_px"]),
            stick_endpoint_b_px=tuple(data["stick_endpoint_b_px"]),
            known_length=data["known_length"],
            known_unit=data["known_unit"],
            origin_px=tuple(data["origin_px"]),
            axis_rotation_deg=data["axis_rotation_deg"],
            pixel_distance=data["pixel_distance"],
            scale=data["scale"],
            video_frame0_hash=data.get("video_frame0_hash", ""),
        )
