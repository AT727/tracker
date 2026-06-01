import pytest
from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtWidgets import QGraphicsScene
from tracker.canvas.overlay_items import (
    CrosshairItem,
    TrackedPointItem,
    CalibrationPointItem,
    OriginItem,
    FrameWatermark,
)


def test_crosshair_item_type():
    item = CrosshairItem()
    assert item.type() == CrosshairItem.Type


def test_crosshair_item_z_value():
    item = CrosshairItem()
    assert item.zValue() == 100


def test_crosshair_item_ignores_transforms():
    item = CrosshairItem()
    assert item.flags() & item.ItemIgnoresTransformations


def test_tracked_point_has_position():
    item = TrackedPointItem()
    item.setPos(100.0, 200.0)
    assert item.pos() == QPointF(100.0, 200.0)


def test_tracked_point_type():
    item = TrackedPointItem()
    assert item.type() == TrackedPointItem.Type


def test_calibration_point_role_determines_color():
    a = CalibrationPointItem(role="A")
    b = CalibrationPointItem(role="B")
    assert a.role == "A"
    assert b.role == "B"


def test_calibration_point_type():
    item = CalibrationPointItem(role="A")
    assert item.type() == CalibrationPointItem.Type


def test_origin_item_type():
    item = OriginItem()
    assert item.type() == OriginItem.Type


def test_origin_item_ignores_transforms():
    item = OriginItem()
    assert item.flags() & item.ItemIgnoresTransformations


def test_origin_item_is_movable():
    item = OriginItem()
    assert item.flags() & item.ItemIsMovable


def test_watermark_renders_frame_text(qtbot):
    scene = QGraphicsScene()
    wm = FrameWatermark(frame_number=42)
    scene.addItem(wm)
    assert wm.frame_number == 42


def test_watermark_type():
    item = FrameWatermark()
    assert item.type() == FrameWatermark.Type


def test_watermark_set_frame(qtbot):
    scene = QGraphicsScene()
    wm = FrameWatermark(frame_number=0)
    scene.addItem(wm)
    wm.set_frame(99)
    assert wm.frame_number == 99


def test_calibration_point_is_draggable(qtbot):
    item = CalibrationPointItem(role="A")
    assert item.flags() & item.ItemIsMovable


def test_calibration_point_bounding_rect():
    item = CalibrationPointItem(role="A")
    rect = item.boundingRect()
    assert isinstance(rect, QRectF)
    assert rect.width() > 0
    assert rect.height() > 0


def test_tracked_point_bounding_rect():
    item = TrackedPointItem()
    rect = item.boundingRect()
    assert isinstance(rect, QRectF)
    assert rect.width() > 0
    assert rect.height() > 0


def test_crosshair_bounding_rect():
    item = CrosshairItem()
    rect = item.boundingRect()
    assert isinstance(rect, QRectF)
    assert rect.width() > 0
    assert rect.height() > 0


def test_origin_bounding_rect():
    item = OriginItem()
    rect = item.boundingRect()
    assert isinstance(rect, QRectF)
    assert rect.width() > 0
    assert rect.height() > 0


def test_watermark_bounding_rect():
    item = FrameWatermark()
    rect = item.boundingRect()
    assert isinstance(rect, QRectF)
    assert rect.width() > 0
    assert rect.height() > 0


def test_calibration_drag_callback_triggered(qtbot):
    positions = []
    item = CalibrationPointItem(role="A", on_drag=lambda p: positions.append(p))
    scene = QGraphicsScene()
    scene.addItem(item)
    item.setPos(10.0, 20.0)
    assert len(positions) == 1
    assert positions[0] == QPointF(10.0, 20.0)


def test_origin_drag_callback_triggered(qtbot):
    positions = []
    item = OriginItem(on_drag=lambda p: positions.append(p))
    scene = QGraphicsScene()
    scene.addItem(item)
    item.setPos(50.0, 60.0)
    assert len(positions) == 1
    assert positions[0] == QPointF(50.0, 60.0)
