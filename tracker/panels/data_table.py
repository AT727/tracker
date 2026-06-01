"""Live data table."""

from __future__ import annotations

from PyQt5.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.tracking.collector import TrackingCollector


class DataTablePanel(QTableWidget):
    HEADERS = ["Frame", "Time (s)", "Series", "X", "Y"]
    _SCROLL_THRESHOLD = 5

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)

    def refresh(
        self,
        collector: TrackingCollector,
        pipeline: CoordinatePipeline,
    ) -> None:
        marks = collector.marks
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - self._SCROLL_THRESHOLD
        self.setRowCount(len(marks))
        suffix = pipeline.unit_suffix
        self.setHorizontalHeaderLabels(
            ["Frame", "Time (s)", "Series", f"X ({suffix})", f"Y ({suffix})"]
        )
        for row, mark in enumerate(marks):
            series = collector.get_series(mark.series_id)
            label = series.label if series else mark.series_id
            world = pipeline.pixel_to_world(mark.px, mark.py)
            values = [
                str(mark.frame + 1),
                f"{mark.timestamp_s:.4f}",
                label,
                f"{world.x:.3f}",
                f"{world.y:.3f}",
            ]
            for col, text in enumerate(values):
                self.setItem(row, col, QTableWidgetItem(text))
        if marks and (at_bottom or len(marks) == 1):
            self.scrollToItem(self.item(len(marks) - 1, 0))
