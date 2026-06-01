from __future__ import annotations
import math
from typing import Tuple
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsView


def scene_to_viewport(scene_pos: QPointF, view: QGraphicsView) -> QPointF:
    return view.mapFromScene(scene_pos)


def viewport_to_pixel(vp_pos: QPointF) -> Tuple[int, int]:
    x = max(0, int(vp_pos.x()))
    y = max(0, int(vp_pos.y()))
    return x, y


def pixel_to_world(px: float, py: float, origin_px: Tuple[float, float],
                   scale: float, rotation_deg: float) -> Tuple[float, float]:
    if scale == 0.0:
        raise ValueError("scale cannot be zero")
    dx = px - origin_px[0]
    dy = py - origin_px[1]
    rad = math.radians(rotation_deg)
    c = math.cos(rad)
    s = math.sin(rad)
    x_world = (dx * c - dy * s) * scale
    y_world = (dx * s + dy * c) * scale
    return x_world, y_world


def world_to_pixel(x_world: float, y_world: float, origin_px: Tuple[float, float],
                   scale: float, rotation_deg: float) -> Tuple[float, float]:
    if scale == 0.0:
        raise ValueError("scale cannot be zero")
    rad = math.radians(-rotation_deg)
    c = math.cos(rad)
    s = math.sin(rad)
    inv_scale = 1.0 / scale
    dx = (x_world * c - y_world * s) * inv_scale
    dy = (x_world * s + y_world * c) * inv_scale
    px = dx + origin_px[0]
    py = dy + origin_px[1]
    return px, py
