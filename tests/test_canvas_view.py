import pytest
from PyQt5.QtCore import Qt, QPointF, QEvent
from PyQt5.QtGui import QPixmap, QMouseEvent
from PyQt5.QtWidgets import QGraphicsScene
from tracker.canvas.view import VideoView, VideoScene


def test_video_scene_creation(qtbot):
    scene = VideoScene()
    assert isinstance(scene, QGraphicsScene)


def test_video_view_creation(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    assert view._pixmap_item is not None


def test_set_frame_updates_pixmap(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    pixmap = QPixmap(640, 480)
    pixmap.fill(Qt.white)
    view.set_frame(pixmap)
    assert not view._pixmap_item.pixmap().isNull()


def test_reset_view_works(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    pixmap = QPixmap(640, 480)
    pixmap.fill(Qt.white)
    view.set_frame(pixmap)
    view.reset_view()


def test_zoom_in_out_roundtrip(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    view.zoom_in()
    view.zoom_out()
    assert view.transform().m11() == pytest.approx(1.0)
    assert view.transform().m22() == pytest.approx(1.0)


def test_zoom_in_zoom_out_preserves_aspect(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    view.zoom_in()
    assert view.transform().m11() == view.transform().m22()


def test_clicked_signal_emitted_in_tracking_mode(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    pixmap = QPixmap(100, 100)
    pixmap.fill(Qt.white)
    view.set_frame(pixmap)
    view.reset_view()

    with qtbot.waitSignal(view.clicked, timeout=500):
        center = view.viewport().rect().center()
        local = QPointF(center)
        event = QMouseEvent(
            QEvent.MouseButtonPress,
            local,
            center,
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        view._mode = "TRACKING"
        view.mousePressEvent(event)


def test_click_in_non_tracking_mode_does_not_emit(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    pixmap = QPixmap(100, 100)
    pixmap.fill(Qt.white)
    view.set_frame(pixmap)
    view.reset_view()

    signals = []
    view.clicked.connect(lambda p: signals.append(p))

    center = view.viewport().rect().center()
    local = QPointF(center)
    event = QMouseEvent(
        QEvent.MouseButtonPress,
        local,
        center,
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    view._mode = "NORMAL"
    view.mousePressEvent(event)

    assert len(signals) == 0


def test_clicked_signal_carries_scene_coordinates(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    pixmap = QPixmap(100, 100)
    pixmap.fill(Qt.white)
    view.set_frame(pixmap)
    view.reset_view()

    received = []
    view.clicked.connect(lambda p: received.append(p))

    with qtbot.waitSignal(view.clicked, timeout=500):
        center = view.viewport().rect().center()
        local = QPointF(center)
        view._mode = "TRACKING"
        event = QMouseEvent(
            QEvent.MouseButtonPress,
            local,
            center,
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        view.mousePressEvent(event)

    assert len(received) == 1
    pt = received[0]
    assert isinstance(pt, QPointF)


def test_pan_preserves_scale(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    original_m11 = view.transform().m11()
    original_m22 = view.transform().m22()

    vp = view.viewport()
    start = vp.rect().center()
    local_start = QPointF(start)
    end = QPointF(start.x() + 50, start.y() + 50)

    press = QMouseEvent(
        QEvent.MouseButtonPress,
        local_start,
        start,
        Qt.MiddleButton,
        Qt.MiddleButton,
        Qt.NoModifier,
    )
    view.mousePressEvent(press)

    move = QMouseEvent(
        QEvent.MouseMove,
        end,
        vp.mapToGlobal(end.toPoint()),
        Qt.NoButton,
        Qt.MiddleButton,
        Qt.NoModifier,
    )
    view.mouseMoveEvent(move)

    release = QMouseEvent(
        QEvent.MouseButtonRelease,
        end,
        vp.mapToGlobal(end.toPoint()),
        Qt.MiddleButton,
        Qt.MiddleButton,
        Qt.NoModifier,
    )
    view.mouseReleaseEvent(release)

    assert view.transform().m11() == pytest.approx(original_m11)
    assert view.transform().m22() == pytest.approx(original_m22)


def test_zoom_clamped_min(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    for _ in range(100):
        view.zoom_out()
    assert view.transform().m11() >= view.MIN_ZOOM - 1e-9


def test_zoom_clamped_max(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    for _ in range(100):
        view.zoom_in()
    assert view.transform().m11() <= view.MAX_ZOOM + 1e-9


def test_scene_rect_matches_frame_size(qtbot):
    view = VideoView()
    qtbot.addWidget(view)
    view.show()
    pixmap = QPixmap(320, 240)
    pixmap.fill(Qt.blue)
    view.set_frame(pixmap)
    assert view._scene.sceneRect().width() == pytest.approx(320.0)
    assert view._scene.sceneRect().height() == pytest.approx(240.0)
