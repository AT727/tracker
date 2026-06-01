"""Canvas view with zoom/pan and click handling."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QPointF, pyqtSignal
from PyQt5.QtGui import QMouseEvent, QPainter, QWheelEvent
from PyQt5.QtWidgets import QGraphicsView

from tracker.canvas.scene import TrackerScene
from tracker.canvas.viewport_state import ViewportState


class CanvasView(QGraphicsView):
    pixel_clicked = pyqtSignal(float, float)
    pixel_pressed = pyqtSignal(float, float)
    pixel_moved = pyqtSignal(float, float)
    pixel_released = pyqtSignal(float, float)
    viewport_changed = pyqtSignal()
    key_pressed = pyqtSignal(int, bool)
    key_released = pyqtSignal(int, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = TrackerScene()
        self.setScene(self._scene)
        self._viewport = ViewportState()
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(Qt.black)
        self.setFocusPolicy(Qt.StrongFocus)
        self._image_w = 0
        self._image_h = 0
        self._left_down = False

    @property
    def tracker_scene(self) -> TrackerScene:
        return self._scene

    @property
    def viewport_state(self) -> ViewportState:
        return self._viewport

    def set_image_size(self, w: int, h: int) -> None:
        self._image_w = w
        self._image_h = h
        self.fit_in_view()

    def fit_in_view(self) -> None:
        self._viewport.fit_to_view(
            float(self.viewport().width()),
            float(self.viewport().height()),
            float(self._image_w),
            float(self._image_h),
        )
        self._apply_transform()
        self.viewport_changed.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._image_w > 0 and self._image_h > 0:
            self.fit_in_view()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        scene_pos = self._event_to_scene(event.pos())
        self._viewport.zoom_at(scene_pos.x(), scene_pos.y(), factor)
        self._apply_transform()
        self.viewport_changed.emit()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            px, py = self._event_to_pixel(event)
            if px is not None:
                self._left_down = True
                self.pixel_pressed.emit(px, py)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._left_down and event.buttons() & Qt.LeftButton:
            px, py = self._event_to_pixel(event)
            if px is not None:
                self.pixel_moved.emit(px, py)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._left_down:
            self._left_down = False
            px, py = self._event_to_pixel(event)
            if px is not None:
                self.pixel_released.emit(px, py)
                self.pixel_clicked.emit(px, py)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def set_pan_from_sliders(self, h_norm: int, v_norm: int) -> None:
        vw = float(self.viewport().width())
        vh = float(self.viewport().height())
        self._viewport.pan_from_sliders(
            h_norm, v_norm, vw, vh, float(self._image_w), float(self._image_h)
        )
        self._apply_transform()
        self.viewport_changed.emit()

    def _event_to_pixel(self, event: QMouseEvent) -> tuple[float, float] | None:
        scene_pos = self._event_to_scene(event.pos())
        px, py = self._viewport.scene_to_pixel(scene_pos.x(), scene_pos.y())
        if 0 <= px <= self._image_w and 0 <= py <= self._image_h:
            return px, py
        return None

    def _event_to_scene(self, pos) -> QPointF:
        vp_pos = self.viewport().mapFrom(self, pos)
        return self.mapToScene(vp_pos)

    def _apply_transform(self) -> None:
        self.setTransform(self._viewport.to_transform())

    def scene_to_pixel(self, scene_x: float, scene_y: float) -> tuple[float, float]:
        return self._viewport.scene_to_pixel(scene_x, scene_y)

    def keyPressEvent(self, event) -> None:
        self.key_pressed.emit(event.key(), event.isAutoRepeat())
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        self.key_released.emit(event.key(), event.isAutoRepeat())
        super().keyReleaseEvent(event)
