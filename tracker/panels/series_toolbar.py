"""Series selection toolbar."""

from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QWidget

from tracker.tracking.collector import TrackingCollector


class SeriesToolbar(QWidget):
    series_changed = pyqtSignal(str)
    add_series_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._emit_series)
        self._add_btn = QPushButton("Add Series")
        self._add_btn.clicked.connect(self.add_series_requested.emit)
        layout.addWidget(self._combo)
        layout.addWidget(self._add_btn)

    def refresh(self, collector: TrackingCollector) -> None:
        current = collector.active_series_id
        self._combo.blockSignals(True)
        self._combo.clear()
        for series in collector.series:
            self._combo.addItem(series.label, series.id)
        if current:
            idx = self._combo.findData(current)
            if idx >= 0:
                self._combo.setCurrentIndex(idx)
        self._combo.blockSignals(False)

    def _emit_series(self) -> None:
        series_id = self._combo.currentData()
        if series_id:
            self.series_changed.emit(series_id)
