"""pyqtgraph plot panel."""

from __future__ import annotations

import pyqtgraph as pg
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.tracking.collector import TrackingCollector


class PlotPanel(QWidget):
    AXIS_OPTIONS = [
        ("x vs t", "x", "t"),
        ("y vs t", "y", "t"),
        ("y vs x", "y", "x"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self._axis_combo = QComboBox()
        for label, _, _ in self.AXIS_OPTIONS:
            self._axis_combo.addItem(label)
        self._axis_combo.currentIndexChanged.connect(self._on_axis_changed)
        controls.addWidget(self._axis_combo)
        layout.addLayout(controls)
        self._plot = pg.PlotWidget()
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.addLegend()
        layout.addWidget(self._plot)
        self._collector: TrackingCollector | None = None
        self._pipeline: CoordinatePipeline | None = None

    def refresh(
        self,
        collector: TrackingCollector,
        pipeline: CoordinatePipeline,
    ) -> None:
        self._collector = collector
        self._pipeline = pipeline
        self._redraw()

    def _on_axis_changed(self) -> None:
        if self._collector and self._pipeline:
            self._redraw()

    def _redraw(self) -> None:
        if self._collector is None or self._pipeline is None:
            return
        self._plot.clear()
        idx = self._axis_combo.currentIndex()
        _, x_key, y_key = self.AXIS_OPTIONS[idx]
        suffix = self._pipeline.unit_suffix
        x_label = self._axis_label(x_key, suffix)
        y_label = self._axis_label(y_key, suffix)
        self._plot.setLabel("bottom", x_label)
        self._plot.setLabel("left", y_label)

        for series in self._collector.series:
            marks = self._collector.marks_for_series(series.id)
            if not marks:
                continue
            xs: list[float] = []
            ys: list[float] = []
            for mark in marks:
                world = self._pipeline.pixel_to_world(mark.px, mark.py)
                values = {
                    "x": world.x,
                    "y": world.y,
                    "t": mark.timestamp_s,
                }
                xs.append(values[x_key])
                ys.append(values[y_key])
            pen = pg.mkPen(color=series.color, width=2)
            self._plot.plot(xs, ys, pen=pen, symbol="o", symbolSize=5, name=series.label)

    @staticmethod
    def _axis_label(key: str, suffix: str) -> str:
        if key == "t":
            return "Time (s)"
        return f"{key.upper()} ({suffix})"
