from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QAbstractItemView, QHeaderView
from PyQt5.QtCore import Qt

from tracker.tracking.collector import TrackingCollector


class DataTablePanel(QWidget):
    frame_selected = pyqtSignal(int)

    COLUMNS = ["Frame", "Timestamp (s)", "X (px)", "Y (px)", "X World", "Y World"]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.clicked.connect(self._on_row_clicked)
        layout.addWidget(self._table)
        self._current_frame: Optional[int] = None

    def update_from_collector(self, collector: TrackingCollector, total_frames: int):
        QTimer.singleShot(0, lambda: self._do_update(collector))

    def _do_update(self, collector: TrackingCollector):
        items = list(collector)
        self._table.setRowCount(len(items))
        for row, pt in enumerate(items):
            self._table.setItem(row, 0, self._make_item(str(pt.frame)))
            self._table.setItem(row, 1, self._make_item(f"{pt.timestamp:.4f}"))
            self._table.setItem(row, 2, self._make_item(f"{pt.x_pixel:.1f}"))
            self._table.setItem(row, 3, self._make_item(f"{pt.y_pixel:.1f}"))
            self._table.setItem(row, 4, self._make_item(f"{pt.x_world:.4f}"))
            self._table.setItem(row, 5, self._make_item(f"{pt.y_world:.4f}"))

    def _make_item(self, text: str):
        from PyQt5.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def highlight_frame(self, frame: int):
        for row in range(self._table.rowCount()):
            if self._table.item(row, 0).text() == str(frame):
                self._table.selectRow(row)
                self._current_frame = frame
                return

    def _on_row_clicked(self, index):
        item = self._table.item(index.row(), 0)
        if item:
            self.frame_selected.emit(int(item.text()))
