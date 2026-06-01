from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsPixmapItem


class VideoScene(QGraphicsScene):
    pass


class VideoView(QGraphicsView):
    clicked = pyqtSignal(QPointF)

    MIN_ZOOM = 0.1
    MAX_ZOOM = 50.0
    ZOOM_FACTOR = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "NORMAL"
        self._panning = False
        self._last_pan_pos = QPoint()

        self._scene = VideoScene(self)
        self.setScene(self._scene)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

    def set_frame(self, pixmap):
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))

    def reset_view(self):
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def _apply_zoom(self, factor, viewport_pos):
        pt = viewport_pos.toPoint() if isinstance(viewport_pos, QPointF) else viewport_pos
        old_scene = self.mapToScene(pt)
        self.scale(factor, factor)
        new_scene = self.mapToScene(pt)
        delta = new_scene - old_scene
        self.translate(delta.x(), delta.y())

    def wheelEvent(self, event):
        steps = event.angleDelta().y() / 120
        factor = self.ZOOM_FACTOR ** steps
        current = self.transform().m11()
        new_zoom = current * factor
        if new_zoom < self.MIN_ZOOM:
            factor = self.MIN_ZOOM / current
        elif new_zoom > self.MAX_ZOOM:
            factor = self.MAX_ZOOM / current
        self._apply_zoom(factor, event.pos())

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
            self._panning = True
            self._last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.LeftButton and self._mode == "TRACKING":
            scene_pos = self.mapToScene(event.pos())
            self.clicked.emit(scene_pos)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            new_scene = self.mapToScene(event.pos())
            old_scene = self.mapToScene(self._last_pan_pos)
            delta = new_scene - old_scene
            self.translate(-delta.x(), -delta.y())
            self._last_pan_pos = event.pos()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def zoom_in(self):
        center = QPointF(self.viewport().rect().center())
        current = self.transform().m11()
        factor = min(self.ZOOM_FACTOR, self.MAX_ZOOM / current)
        self._apply_zoom(factor, center)

    def zoom_out(self):
        center = QPointF(self.viewport().rect().center())
        current = self.transform().m11()
        factor = max(1.0 / self.ZOOM_FACTOR, self.MIN_ZOOM / current)
        self._apply_zoom(factor, center)
