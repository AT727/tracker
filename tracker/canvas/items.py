"""Graphics scene items for overlays."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPen, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsSimpleTextItem,
    QGraphicsItemGroup,
)

MARK_RED = "#ff453a"
CLICK_GREEN = "#30d158"


class FramePixmapItem(QGraphicsPixmapItem):
    def __init__(self) -> None:
        super().__init__()
        self.setTransformationMode(Qt.SmoothTransformation)


class StickOverlay(QGraphicsItemGroup):
    HANDLE_RADIUS = 6

    def __init__(self) -> None:
        super().__init__()
        r = self.HANDLE_RADIUS
        pen = QPen(QColor("#30d158"), 2)
        fill = QBrush(QColor("#30d158"))
        self._line = QGraphicsLineItem()
        self._line.setPen(pen)
        self._a = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        self._b = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
        for handle in (self._a, self._b):
            handle.setPen(QPen(QColor("#1c7d32"), 1))
            handle.setBrush(fill)
        self.addToGroup(self._line)
        self.addToGroup(self._a)
        self.addToGroup(self._b)

    def set_endpoints(self, ax: float, ay: float, bx: float, by: float) -> None:
        partial = ax == bx and ay == by
        self._line.setLine(ax, ay, bx, by)
        self._line.setVisible(not partial)
        self._a.setPos(ax, ay)
        self._b.setPos(bx, by)
        self._b.setVisible(not partial)


class OriginGridOverlay(QGraphicsItemGroup):
    GRID_SPACING = 50

    def __init__(self) -> None:
        super().__init__()
        self._lines: list[QGraphicsLineItem] = []
        self._origin_dot = QGraphicsEllipseItem(-5, -5, 10, 10)
        self._origin_dot.setBrush(QBrush(QColor("#ff453a")))
        self._origin_dot.setPen(QPen(Qt.NoPen))
        self.addToGroup(self._origin_dot)

    def set_origin(self, ox: float, oy: float, width: float, height: float) -> None:
        for line in self._lines:
            self.removeFromGroup(line)
        self._lines.clear()
        pen = QPen(QColor(255, 255, 255, 50), 1, Qt.DotLine)
        spacing = self.GRID_SPACING
        x = ox
        while x <= width:
            line = QGraphicsLineItem(x, 0, x, height)
            line.setPen(pen)
            self.addToGroup(line)
            self._lines.append(line)
            x += spacing
        x = ox - spacing
        while x >= 0:
            line = QGraphicsLineItem(x, 0, x, height)
            line.setPen(pen)
            self.addToGroup(line)
            self._lines.append(line)
            x -= spacing
        y = oy
        while y <= height:
            line = QGraphicsLineItem(0, y, width, y)
            line.setPen(pen)
            self.addToGroup(line)
            self._lines.append(line)
            y += spacing
        y = oy - spacing
        while y >= 0:
            line = QGraphicsLineItem(0, y, width, y)
            line.setPen(pen)
            self.addToGroup(line)
            self._lines.append(line)
            y -= spacing
        self._origin_dot.setPos(ox, oy)


class MarkDotItem(QGraphicsEllipseItem):
    def __init__(self, px: float, py: float, color: str = MARK_RED, radius: float = 5, filled: bool = True) -> None:
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.setPos(px, py)
        if filled:
            self.setBrush(QBrush(QColor(color)))
            self.setPen(QPen(Qt.black, 1))
        else:
            self.setBrush(QBrush(Qt.NoBrush))
            self.setPen(QPen(QColor(color), 2))


class MarkSquareItem(QGraphicsRectItem):
    HALF_SIZE = 6

    def __init__(self, px: float, py: float, color: str = MARK_RED) -> None:
        half = self.HALF_SIZE
        super().__init__(-half, -half, half * 2, half * 2)
        self.setPos(px, py)
        self.setBrush(QBrush(Qt.NoBrush))
        self.setPen(QPen(QColor(color), 2))


class FrameLabelItem(QGraphicsSimpleTextItem):
    def __init__(self) -> None:
        super().__init__()
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.setFont(font)
        self.setBrush(QBrush(QColor("#ffffff")))

    def set_frame_text(self, index: int, total: int, timestamp_s: float) -> None:
        self.setText(f"Frame {index + 1} / {total}  |  t = {timestamp_s:.4f} s")
