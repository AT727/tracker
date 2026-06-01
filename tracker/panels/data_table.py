"""Live data table."""

from __future__ import annotations

from PyQt5.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.tracking.collector import TrackingCollector
from tracker.tracking.mark import Mark


class DataTablePanel(QTableWidget):
    HEADERS = ["frame", "t (s)", "x (cm)", "y (cm)"]
    _SCROLL_THRESHOLD = 5

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)

    def append_mark(
        self,
        _collector: TrackingCollector,
        pipeline: CoordinatePipeline,
        mark: Mark,
    ) -> None:
        """Incrementally append one row (fast path for high CPS)."""
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - self._SCROLL_THRESHOLD

        row = self.rowCount()
        self.insertRow(row)

        world = pipeline.pixel_to_world(mark.px, mark.py)
        values = [
            str(mark.frame + 1),
            f"{mark.timestamp_s:.4f}",
            f"{world.x:.3f}",
            f"{world.y:.3f}",
        ]
        for col, text in enumerate(values):
            self.setItem(row, col, QTableWidgetItem(text))

        if row == 0 or at_bottom:
            self.scrollToItem(self.item(row, 0))

    def refresh(
        self,
        collector: TrackingCollector,
        pipeline: CoordinatePipeline,
    ) -> None:
        marks = collector.marks
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - self._SCROLL_THRESHOLD
        self.setRowCount(len(marks))
        self.setHorizontalHeaderLabels(self.HEADERS)
        for row, mark in enumerate(marks):
            world = pipeline.pixel_to_world(mark.px, mark.py)
            values = [
                str(mark.frame + 1),
                f"{mark.timestamp_s:.4f}",
                f"{world.x:.3f}",
                f"{world.y:.3f}",
            ]
            for col, text in enumerate(values):
                self.setItem(row, col, QTableWidgetItem(text))
        if marks and (at_bottom or len(marks) == 1):
            self.scrollToItem(self.item(len(marks) - 1, 0))
