"""Live data table."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView, QMenu, QTableWidget, QTableWidgetItem

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.tracking.collector import TrackingCollector


class DataTablePanel(QTableWidget):
    go_to_frame_requested = pyqtSignal(int)

    HEADERS = ["frame", "t (s)", "x (cm)", "y (cm)"]
    _SCROLL_THRESHOLD = 5
    _FRAME_ROLE = Qt.UserRole + 1
    _SEPARATOR_BG = QColor("#2f0f0f")
    _SEPARATOR_FG = QColor("#ff6b6b")
    _SEPARATOR_HEIGHT = 8

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def refresh(
        self,
        collector: TrackingCollector,
        pipeline: CoordinatePipeline,
        series_id: str | None = None,
        gap_after_frames: set[int] | None = None,
    ) -> None:
        marks = (
            collector.marks_for_series(series_id)
            if series_id
            else collector.marks
        )
        marks = sorted(marks, key=lambda m: m.frame)
        gap_after_frames = gap_after_frames or set()
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - self._SCROLL_THRESHOLD
        row_count = len(marks) + sum(1 for mark in marks if mark.frame in gap_after_frames)
        self.setRowCount(row_count)
        self.setHorizontalHeaderLabels(self.HEADERS)
        row = 0
        for mark in marks:
            world = pipeline.pixel_to_world(mark.px, mark.py)
            values = [
                str(mark.frame + 1),
                f"{mark.timestamp_s:.4f}",
                f"{world.x:.3f}",
                f"{world.y:.3f}",
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setData(self._FRAME_ROLE, mark.frame)
                self.setItem(row, col, item)
            row += 1
            if mark.frame in gap_after_frames:
                self._insert_gap_row(row)
                row += 1
        if marks and (at_bottom or len(marks) == 1):
            target_row = self._last_data_row()
            if target_row is not None:
                self.scrollToItem(self.item(target_row, 0))

    def _insert_gap_row(self, row: int) -> None:
        values = ["", "missing frame(s)", "", ""]
        for col, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setBackground(self._SEPARATOR_BG)
            item.setForeground(self._SEPARATOR_FG)
            self.setItem(row, col, item)
        self.setRowHeight(row, self._SEPARATOR_HEIGHT)

    def _last_data_row(self) -> int | None:
        for row in range(self.rowCount() - 1, -1, -1):
            item = self.item(row, 0)
            if item is None:
                continue
            if item.data(self._FRAME_ROLE) is not None:
                return row
        return None

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if item is None:
            return
        frame = item.data(self._FRAME_ROLE)
        if frame is None:
            return
        menu = QMenu(self)
        go_to_action = menu.addAction("Go to frame")
        action = menu.exec_(self.viewport().mapToGlobal(pos))
        if action == go_to_action:
            self.go_to_frame_requested.emit(int(frame))
