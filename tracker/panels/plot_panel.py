from __future__ import annotations

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from tracker.tracking.collector import TrackingCollector


class PlotPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure()
        self._canvas = FigureCanvas(self._figure)
        self._toolbar = NavigationToolbar(self._canvas, self)

        self._axes_x = self._figure.add_subplot(211)
        self._axes_y = self._figure.add_subplot(212)

        layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas)

        self._figure.tight_layout()

    def update_from_collector(self, collector: TrackingCollector, total_frames: int):
        QTimer.singleShot(0, lambda: self._do_update(collector))

    def _do_update(self, collector: TrackingCollector):
        frames = []
        x_worlds = []
        y_worlds = []
        for pt in collector:
            frames.append(pt.frame)
            x_worlds.append(pt.x_world)
            y_worlds.append(pt.y_world)

        self._axes_x.clear()
        self._axes_x.plot(frames, x_worlds, 'b.-')
        self._axes_x.set_ylabel("X World")
        self._axes_x.grid(True)

        self._axes_y.clear()
        self._axes_y.plot(frames, y_worlds, 'r.-')
        self._axes_y.set_ylabel("Y World")
        self._axes_y.set_xlabel("Frame")
        self._axes_y.grid(True)

        self._canvas.draw()
