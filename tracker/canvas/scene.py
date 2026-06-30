"""Tracker graphics scene."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem

from tracker.canvas.items import (
    CLICK_GREEN,
    FrameLabelItem,
    FramePixmapItem,
    MarkDotItem,
    MarkSquareItem,
    OriginGridOverlay,
    StickOverlay,
)


class TrackerScene(QGraphicsScene):
    def __init__(self) -> None:
        super().__init__()
        self._frame_item = FramePixmapItem()
        self._stick = StickOverlay()
        self._grid = OriginGridOverlay()
        self._frame_label = FrameLabelItem()
        self._mark_items: list[QGraphicsItem] = []
        self._mark_styles: list[str] = []
        self._click_feedback: MarkDotItem | None = None
        self.addItem(self._frame_item)
        self.addItem(self._stick)
        self.addItem(self._grid)
        self.addItem(self._frame_label)
        self._stick.setVisible(False)
        self._grid.setVisible(False)
        self._image_w = 0
        self._image_h = 0

    def set_frame_pixmap(self, pixmap: QPixmap) -> None:
        self._frame_item.setPixmap(pixmap)
        self._frame_item.update()
        self._image_w = pixmap.width()
        self._image_h = pixmap.height()
        self.setSceneRect(0, 0, self._image_w, self._image_h)
        self._frame_label.setPos(8, 8)
        self.update()

    def set_stick_visible(self, visible: bool) -> None:
        self._stick.setVisible(visible)

    def set_grid_visible(self, visible: bool) -> None:
        self._grid.setVisible(visible)

    def update_stick(self, ax: float, ay: float, bx: float, by: float) -> None:
        self._stick.set_endpoints(ax, ay, bx, by)

    def update_origin_grid(self, ox: float, oy: float) -> None:
        self._grid.set_origin(ox, oy, float(self._image_w), float(self._image_h))

    def set_frame_label(self, index: int, total: int, timestamp_s: float) -> None:
        self._frame_label.set_frame_text(index, total, timestamp_s)

    def set_marks(self, marks: list[tuple[float, float, str]]) -> None:
        """Render mark items at pixel positions. Recreates items on style mismatch."""
        for i, (px, py, style) in enumerate(marks):
            if i < len(self._mark_items):
                if self._mark_styles[i] != style:
                    old = self._mark_items[i]
                    self.removeItem(old)
                    item = MarkDotItem(px, py) if style == "dot" else MarkSquareItem(px, py)
                    self.addItem(item)
                    self._mark_items[i] = item
                    self._mark_styles[i] = style
                else:
                    self._mark_items[i].setPos(px, py)
            else:
                item = MarkDotItem(px, py) if style == "dot" else MarkSquareItem(px, py)
                self.addItem(item)
                self._mark_items.append(item)
                self._mark_styles.append(style)
        while len(self._mark_items) > len(marks):
            self._mark_styles.pop()
            item = self._mark_items.pop()
            self.removeItem(item)

    def show_click_feedback(self, px: float, py: float, color: str = CLICK_GREEN, filled: bool = False) -> None:
        if self._click_feedback is not None:
            self.removeItem(self._click_feedback)
        self._click_feedback = MarkDotItem(px, py, color=color, filled=filled)
        self.addItem(self._click_feedback)

    def clear_click_feedback(self) -> None:
        if self._click_feedback is not None:
            self.removeItem(self._click_feedback)
            self._click_feedback = None
