from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass
class TrackedPoint:
    frame: int
    timestamp: float
    x_world: float
    y_world: float
    x_pixel: float
    y_pixel: float
    track_id: str = "0"
    is_interpolated: bool = False


class TrackingCollector:
    def __init__(self):
        self._points: List[TrackedPoint] = []

    def record(self, frame: int, timestamp: float, x_world: float, y_world: float,
               x_pixel: float, y_pixel: float, track_id: str = "0") -> TrackedPoint:
        pt = TrackedPoint(
            frame=frame, timestamp=timestamp, x_world=x_world, y_world=y_world,
            x_pixel=x_pixel, y_pixel=y_pixel, track_id=track_id,
        )
        self._points.append(pt)
        return pt

    def recompute_world_coords(self, pixel_to_world: Callable[[float, float], Tuple[float, float]]):
        for pt in self._points:
            pt.x_world, pt.y_world = pixel_to_world(pt.x_pixel, pt.y_pixel)

    def get_by_frame(self, frame: int) -> Optional[TrackedPoint]:
        for pt in self._points:
            if pt.frame == frame:
                return pt
        return None

    def all_frames_range(self, total_frames: int) -> List[Optional[TrackedPoint]]:
        lookup = {pt.frame: pt for pt in self._points}
        return [lookup.get(i) for i in range(total_frames)]

    def __len__(self) -> int:
        return len(self._points)

    def __getitem__(self, index: int) -> TrackedPoint:
        return self._points[index]

    def __iter__(self):
        return iter(self._points)
