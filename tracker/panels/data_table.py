"""Live data table."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView, QMenu, QTableWidget, QTableWidgetItem

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.mutations import ColumnMutation, eval_formula
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
        super().__init__(0, 4, parent)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._last_series_id: str | None = None
        self._last_mutations: list[ColumnMutation] = []
        self._last_mark_count: int = 0
        self._last_mark_frame: int = -1
        self._last_row_count: int = 0

    def refresh(
        self,
        collector: TrackingCollector,
        pipeline: CoordinatePipeline,
        series_id: str | None = None,
        gap_after_frames: set[int] | None = None,
        mutations: list[ColumnMutation] | None = None,
    ) -> None:
        mutations = mutations or []
        marks = (
            collector.marks_for_series_sorted(series_id)
            if series_id
            else sorted(collector.marks, key=lambda m: m.frame)
        )
        gap_after_frames = gap_after_frames or set()
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - self._SCROLL_THRESHOLD
        row_count = len(marks) + sum(1 for mark in marks if mark.frame in gap_after_frames)
        col_count = len(self.HEADERS) + len(mutations)

        marks_appended = (
            self._last_mark_count > 0
            and len(marks) > self._last_mark_count
            and marks[-1].frame > self._last_mark_frame
        )
        can_increment = (
            series_id == self._last_series_id
            and mutations == self._last_mutations
            and marks_appended
        )

        if can_increment:
            self.setRowCount(row_count)
            new_marks = marks[self._last_mark_count:]
            row = self._last_row_count
            for mark in new_marks:
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
                self._set_mutation_cells(row, mark, world, mutations)
                row += 1
                if mark.frame in gap_after_frames:
                    self._insert_gap_row(row, len(mutations))
                    row += 1
            if marks and at_bottom:
                target_row = self._last_data_row()
                if target_row is not None:
                    self.scrollToItem(self.item(target_row, 0))
            self._last_mark_count = len(marks)
            self._last_mark_frame = marks[-1].frame if marks else -1
            self._last_row_count = row
            return

        self.setColumnCount(col_count)
        self.setRowCount(row_count)
        headers = list(self.HEADERS) + [m.name for m in mutations]
        self.setHorizontalHeaderLabels(headers)
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
            self._set_mutation_cells(row, mark, world, mutations)
            row += 1
            if mark.frame in gap_after_frames:
                self._insert_gap_row(row, len(mutations))
                row += 1
        if marks and (at_bottom or len(marks) == 1):
            target_row = self._last_data_row()
            if target_row is not None:
                self.scrollToItem(self.item(target_row, 0))
        self._last_series_id = series_id
        self._last_mutations = list(mutations)
        self._last_mark_count = len(marks)
        self._last_mark_frame = marks[-1].frame if marks else -1
        self._last_row_count = row_count

    def _set_mutation_cells(
        self,
        row: int,
        mark,
        world,
        mutations: list[ColumnMutation],
    ) -> None:
        vars = {
            "x": world.x,
            "y": world.y,
            "t": mark.timestamp_s,
            "frame": float(mark.frame),
        }
        for col_offset, mutation in enumerate(mutations):
            col = len(self.HEADERS) + col_offset
            try:
                result = eval_formula(mutation.formula, vars)
                text = f"{result:.3f}"
            except (ValueError, ZeroDivisionError):
                text = "ERR"
            item = QTableWidgetItem(text)
            item.setData(self._FRAME_ROLE, mark.frame)
            self.setItem(row, col, item)

    def _insert_gap_row(self, row: int, mutation_count: int = 0) -> None:
        values = ["", "missing frame(s)", "", ""] + [""] * mutation_count
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
