"""Explicit scale/pan viewport state → QTransform."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtGui import QTransform


@dataclass
class ViewportState:
    scale: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def to_transform(self) -> QTransform:
        t = QTransform()
        t.translate(self.pan_x, self.pan_y)
        t.scale(self.scale, self.scale)
        return t

    def scene_to_pixel(self, scene_x: float, scene_y: float) -> tuple[float, float]:
        """Scene coordinates are video pixel coordinates."""
        return scene_x, scene_y

    def pixel_to_scene(self, px: float, py: float) -> tuple[float, float]:
        return px, py

    def view_to_pixel(self, view_x: float, view_y: float) -> tuple[float, float]:
        px = (view_x - self.pan_x) / self.scale
        py = (view_y - self.pan_y) / self.scale
        return px, py

    def pixel_to_view(self, px: float, py: float) -> tuple[float, float]:
        vx = px * self.scale + self.pan_x
        vy = py * self.scale + self.pan_y
        return vx, vy

    def zoom_at(self, scene_x: float, scene_y: float, factor: float) -> None:
        """Zoom keeping the video pixel under (scene_x, scene_y) fixed."""
        px, py = scene_x, scene_y
        view_x, view_y = self.pixel_to_view(px, py)
        new_scale = max(0.05, min(50.0, self.scale * factor))
        self.scale = new_scale
        self.pan_x = view_x - px * new_scale
        self.pan_y = view_y - py * new_scale

    def fit_to_view(self, view_w: float, view_h: float, image_w: float, image_h: float) -> None:
        if image_w <= 0 or image_h <= 0:
            return
        scale_x = view_w / image_w
        scale_y = view_h / image_h
        self.scale = min(scale_x, scale_y)
        self.pan_x = (view_w - image_w * self.scale) / 2.0
        self.pan_y = (view_h - image_h * self.scale) / 2.0

    def pan_range(
        self,
        view_w: float,
        view_h: float,
        image_w: float,
        image_h: float,
    ) -> tuple[float, float, float, float]:
        """Return (min_pan_x, max_pan_x, min_pan_y, max_pan_y)."""
        content_w = image_w * self.scale
        content_h = image_h * self.scale
        if content_w <= view_w:
            center_x = (view_w - content_w) / 2.0
            min_pan_x = max_pan_x = center_x
        else:
            min_pan_x = view_w - content_w
            max_pan_x = 0.0
        if content_h <= view_h:
            center_y = (view_h - content_h) / 2.0
            min_pan_y = max_pan_y = center_y
        else:
            min_pan_y = view_h - content_h
            max_pan_y = 0.0
        return min_pan_x, max_pan_x, min_pan_y, max_pan_y

    def set_pan(
        self,
        pan_x: float,
        pan_y: float,
        view_w: float,
        view_h: float,
        image_w: float,
        image_h: float,
    ) -> None:
        min_px, max_px, min_py, max_py = self.pan_range(view_w, view_h, image_w, image_h)
        self.pan_x = max(min_px, min(max_px, pan_x))
        self.pan_y = max(min_py, min(max_py, pan_y))

    def pan_slider_values(
        self,
        view_w: float,
        view_h: float,
        image_w: float,
        image_h: float,
    ) -> tuple[int, int, bool, bool]:
        """Return (h_value, v_value, h_enabled, v_enabled) for 0-1000 sliders."""
        min_px, max_px, min_py, max_py = self.pan_range(view_w, view_h, image_w, image_h)
        h_enabled = max_px > min_px
        v_enabled = max_py > min_py
        h_val = 0
        v_val = 0
        if h_enabled:
            h_val = int(round((self.pan_x - min_px) / (max_px - min_px) * 1000))
        if v_enabled:
            v_val = int(round((self.pan_y - min_py) / (max_py - min_py) * 1000))
        return h_val, v_val, h_enabled, v_enabled

    def pan_from_sliders(
        self,
        h_norm: int,
        v_norm: int,
        view_w: float,
        view_h: float,
        image_w: float,
        image_h: float,
    ) -> None:
        min_px, max_px, min_py, max_py = self.pan_range(view_w, view_h, image_w, image_h)
        pan_x = min_px + (max_px - min_px) * (h_norm / 1000.0)
        pan_y = min_py + (max_py - min_py) * (v_norm / 1000.0)
        self.set_pan(pan_x, pan_y, view_w, view_h, image_w, image_h)
