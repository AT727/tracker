"""pyqtgraph plot panel."""

from __future__ import annotations

import pyqtgraph as pg
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.tracking.collector import TrackingCollector


class PlotPanel(QWidget):
    AXIS_OPTIONS = [
        ("x vs t", "t", "x"),
        ("y vs t", "t", "y"),
        ("y vs x", "x", "y"),
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
        self._plot = pg.PlotWidget(background='#1e1e1e')
        self._plot.showGrid(x=True, y=True, alpha=0.15)
        for axis in ['left', 'bottom']:
            ax = self._plot.getAxis(axis)
            ax.setPen('#5d5d5d')
            ax.setTextPen('#8e8e93')
        self._plot.addLegend()
        layout.addWidget(self._plot)
        self._collector: TrackingCollector | None = None
        self._pipeline: CoordinatePipeline | None = None
        self._plotted_data: list[dict] = []
        self._hover_text = pg.TextItem(
            "",
            anchor=(0, 1),
            color="#ffffff",
            fill=pg.mkBrush(30, 30, 30, 200),
        )
        self._plot.addItem(self._hover_text)
        self._hover_text.hide()
        self._proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved,
            rateLimit=30,
            slot=self._on_mouse_moved,
        )

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

        self._plotted_data = []
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
            brush = pg.mkBrush(color=series.color)
            self._plot.plot(
                xs,
                ys,
                pen=pen,
                symbol="o",
                symbolSize=6,
                symbolBrush=brush,
                symbolPen=pen,
                name=series.label,
            )
            self._plotted_data.append({"xs": xs, "ys": ys})
        self._plot.addItem(self._hover_text)
        self._hover_text.hide()

    def _on_mouse_moved(self, evt) -> None:
        if not self._plotted_data or self._pipeline is None:
            return
        pos = evt[0]
        vb = self._plot.plotItem.vb
        mouse_data = vb.mapSceneToView(pos)
        mx, my = mouse_data.x(), mouse_data.y()

        pw, ph = vb.viewPixelSize()
        threshold = 15.0 * max(pw, ph)

        best_dist = threshold * threshold
        best_x = None
        best_y = None

        for entry in self._plotted_data:
            for x, y in zip(entry["xs"], entry["ys"]):
                dx = x - mx
                dy = y - my
                dist = dx * dx + dy * dy
                if dist < best_dist:
                    best_dist = dist
                    best_x = x
                    best_y = y

        if best_x is not None:
            suffix = self._pipeline.unit_suffix
            self._hover_text.setText(
                f"({self._format_value(best_y, suffix)}, "
                f"{self._format_value(best_x, suffix)})"
            )
            self._hover_text.setPos(best_x, best_y)
            self._hover_text.show()
        else:
            self._hover_text.hide()

    @staticmethod
    def _format_value(val: float, suffix: str) -> str:
        if suffix == "px":
            return str(int(round(val)))
        return f"{val:.2f}"

    @staticmethod
    def _axis_label(key: str, suffix: str) -> str:
        if key == "t":
            return "Time (s)"
        return f"{key.upper()} ({suffix})"
