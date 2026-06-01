import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from tracker.coordinates.pipeline import scene_to_viewport, viewport_to_pixel, pixel_to_world, world_to_pixel


def test_pixel_to_world_origin():
    wx, wy = pixel_to_world(320.0, 240.0, (320.0, 240.0), 1.0, 0.0)
    assert wx == pytest.approx(0.0)
    assert wy == pytest.approx(0.0)


def test_pixel_to_world_no_rotation():
    wx, wy = pixel_to_world(420.0, 240.0, (320.0, 240.0), 0.01, 0.0)
    assert wx == pytest.approx(1.0)
    assert wy == pytest.approx(0.0)


def test_pixel_to_world_with_rotation():
    wx, wy = pixel_to_world(100.0, 0.0, (0.0, 0.0), 1.0, 180.0)
    assert wx == pytest.approx(-100.0)
    assert wy == pytest.approx(0.0, abs=1e-10)


def test_pixel_to_world_zero_scale_raises():
    with pytest.raises(ValueError, match="scale cannot be zero"):
        pixel_to_world(100.0, 200.0, (0.0, 0.0), 0.0, 45.0)


def test_world_to_pixel_roundtrip():
    wx, wy = pixel_to_world(420.0, 240.0, (320.0, 240.0), 0.01, 30.0)
    px, py = world_to_pixel(wx, wy, (320.0, 240.0), 0.01, 30.0)
    assert px == pytest.approx(420.0, abs=1e-10)
    assert py == pytest.approx(240.0, abs=1e-10)


def test_world_to_pixel_zero_scale_raises():
    with pytest.raises(ValueError, match="scale cannot be zero"):
        world_to_pixel(10.0, 20.0, (0.0, 0.0), 0.0, 0.0)


def test_scene_to_viewport_with_transform(qtbot):
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    view.resize(640, 480)
    view.show()
    qtbot.addWidget(view)
    view.scale(2.0, 2.0)
    view.horizontalScrollBar().setValue(0)
    view.verticalScrollBar().setValue(0)
    raw = view.mapFromScene(QPointF(100.0, 100.0))
    vp = scene_to_viewport(QPointF(100.0, 100.0), view)
    assert vp == raw


def test_viewport_to_pixel_clamps_negative(qtbot):
    px, py = viewport_to_pixel(QPointF(-10.0, -20.0))
    assert px == 0
    assert py == 0


def test_viewport_to_pixel_positive():
    px, py = viewport_to_pixel(QPointF(100.5, 200.7))
    assert px == 100
    assert py == 200
