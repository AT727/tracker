from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QGraphicsItem


class CrosshairItem(QGraphicsItem):
    Type = QGraphicsItem.UserType + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setZValue(100)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self._pen = QPen(QColor(255, 255, 255, 200), 1)

    def boundingRect(self):
        return QRectF(-10, -10, 20, 20)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.drawLine(-10, 0, 10, 0)
        painter.drawLine(0, -10, 0, 10)

    def type(self):
        return self.Type


class TrackedPointItem(QGraphicsItem):
    Type = QGraphicsItem.UserType + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self._brush = QBrush(QColor("#FF0000"))
        self._pen = QPen(Qt.NoPen)

    def boundingRect(self):
        return QRectF(-4, -4, 8, 8)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        painter.drawEllipse(QRectF(-4, -4, 8, 8))

    def type(self):
        return self.Type


class CalibrationPointItem(QGraphicsItem):
    Type = QGraphicsItem.UserType + 3

    def __init__(self, role="A", on_drag=None, parent=None):
        super().__init__(parent)
        self.role = role
        self._on_drag = on_drag
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        color = QColor("#0066FF") if role == "A" else QColor("#00CC44")
        self._brush = QBrush(color)
        self._pen = QPen(color.darker(130), 2)

    def boundingRect(self):
        return QRectF(-6, -6, 12, 12)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        painter.drawEllipse(QRectF(-6, -6, 12, 12))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self._on_drag:
            self._on_drag(value)
        return super().itemChange(change, value)

    def type(self):
        return self.Type


class OriginItem(QGraphicsItem):
    Type = QGraphicsItem.UserType + 4

    def __init__(self, on_drag=None, parent=None):
        super().__init__(parent)
        self._on_drag = on_drag
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self._pen = QPen(QColor("#FF8800"), 2)
        self._brush = QBrush(QColor("#FF8800"))

    def boundingRect(self):
        return QRectF(-8, -8, 16, 16)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(-8, -8, 16, 16))
        painter.drawLine(-6, 0, 6, 0)
        painter.drawLine(0, -6, 0, 6)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self._on_drag:
            self._on_drag(value)
        return super().itemChange(change, value)

    def type(self):
        return self.Type


class FrameWatermark(QGraphicsItem):
    Type = QGraphicsItem.UserType + 5

    def __init__(self, frame_number=0, parent=None):
        super().__init__(parent)
        self.frame_number = frame_number
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self._font = QFont("monospace", 12)
        self._pen = QPen(QColor(255, 255, 255, 180))

    def set_frame(self, frame_number):
        self.frame_number = frame_number
        self.prepareGeometryChange()

    def boundingRect(self):
        return QRectF(-100, -20, 200, 40)

    def paint(self, painter, option, widget=None):
        painter.setFont(self._font)
        painter.setPen(self._pen)
        painter.drawText(
            self.boundingRect(),
            Qt.AlignRight | Qt.AlignBottom,
            f"Frame: {self.frame_number}",
        )

    def type(self):
        return self.Type
