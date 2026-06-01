from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QKeySequence, QPixmap, QFont, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QLabel, QAction, QFileDialog,
    QMessageBox, QMenu, QStatusBar, QFrame,
)

import cv2
import numpy as np

from tracker.calibration.controller import CalibrationController
from tracker.calibration.persistence import CalibrationStore
from tracker.calibration.data import CalibrationData
from tracker.coordinates.pipeline import pixel_to_world, viewport_to_pixel
from tracker.export.csv_writer import CsvExporter
from tracker.tracking.collector import TrackingCollector, TrackedPoint
from tracker.tracking.state import AppMode
from tracker.video.decoder import VideoDecoder
from tracker.canvas.view import VideoView, VideoScene
from tracker.canvas.overlay_items import (
    CrosshairItem, TrackedPointItem, CalibrationPointItem,
    OriginItem, FrameWatermark,
)
from tracker.panels.data_table import DataTablePanel
from tracker.panels.plot_panel import PlotPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker")
        self.resize(1280, 800)

        # Core state
        self._decoder: Optional[VideoDecoder] = None
        self._collector = TrackingCollector()
        self._cal_controller = CalibrationController()
        self._cal_store = CalibrationStore()
        self._video_path: Optional[str] = None
        self._current_frame: int = 0
        self._total_frames: int = 0
        self._fps: float = 0.0

        # Build UI
        self._setup_menu()
        self._setup_status_bar()
        self._setup_central()

        # Connect signals
        self._connect_signals()

        # Crosshair overlay
        self._crosshair = CrosshairItem()
        self._scene.addItem(self._crosshair)

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("&Open Video...", self._open_video, QKeySequence.Open)
        file_menu.addSeparator()
        file_menu.addAction("&Load Calibration...", self._load_calibration)
        file_menu.addAction("&Save Calibration", self._save_calibration)
        file_menu.addSeparator()
        file_menu.addAction("Export &Standard CSV...", self._export_standard_csv)
        file_menu.addAction("Export &Full CSV...", self._export_full_csv)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, QKeySequence.Quit)

        view_menu = menubar.addMenu("&View")
        view_menu.addAction("&Reset Zoom", self._reset_view)
        view_menu.addAction("Zoom &In", self._zoom_in)
        view_menu.addAction("Zoom &Out", self._zoom_out)

        cal_menu = menubar.addMenu("&Calibration")
        cal_menu.addAction("Start &Calibration", self._start_calibration)
        cal_menu.addAction("&Set Origin", self._start_set_origin)
        cal_menu.addAction("&Reset Calibration", self._reset_calibration)

    def _setup_status_bar(self):
        self._status_label = QLabel("No video loaded")
        self._frame_label = QLabel("Frame: -")
        self._mode_label = QLabel("Mode: IDLE")
        self.statusBar().addWidget(self._status_label, 1)
        self.statusBar().addPermanentWidget(self._frame_label)
        self.statusBar().addPermanentWidget(self._mode_label)

    def _setup_central(self):
        self._view = VideoView()
        self._scene = self._view._scene

        self._data_table = DataTablePanel()
        self._plot_panel = PlotPanel()
        tabs = QTabWidget()
        tabs.addTab(self._data_table, "Data")
        tabs.addTab(self._plot_panel, "Plot")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._view)
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

    def _connect_signals(self):
        self._view.clicked.connect(self._on_canvas_click)
        self._cal_controller.mode_changed.connect(self._on_mode_changed)
        self._cal_controller.endpoint_a_selected.connect(self._on_endpoint_a)
        self._cal_controller.endpoint_b_selected.connect(self._on_endpoint_b)
        self._cal_controller.calibration_complete.connect(self._on_calibration_complete)
        self._cal_controller.origin_set.connect(self._on_origin_set)
        self._cal_controller.status_message.connect(self._status_label.setText)
        self._data_table.frame_selected.connect(self._seek_to_frame)

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "", "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        if not path:
            return

        try:
            decoder = VideoDecoder(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open video:\n{e}")
            return

        self._decoder = decoder
        self._video_path = path
        self._total_frames = decoder.frame_count
        self._fps = decoder.fps
        self._current_frame = 0
        self._collector = TrackingCollector()

        self._show_frame(0)
        self._frame_label.setText(f"Frame: 0/{self._total_frames}")
        self._status_label.setText(f"Loaded: {Path(path).name}")

        self._cal_controller.try_auto_load(path)

    def _show_frame(self, frame_index: int):
        if self._decoder is None:
            return
        frame, timestamp = self._decoder.get_frame(frame_index)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimage = QPixmap.fromImage(
            QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        )
        self._view.set_frame(qimage)
        self._frame_label.setText(f"Frame: {frame_index}/{self._total_frames}")

    def _on_canvas_click(self, scene_pos: QPointF):
        px, py = int(scene_pos.x()), int(scene_pos.y())
        mode = self._cal_controller.mode

        if mode == AppMode.TRACKING:
            cal = self._cal_controller._calibration
            x_pixel = float(px)
            y_pixel = float(py)
            timestamp = 0.0
            if self._decoder is not None:
                _, timestamp = self._decoder.get_frame(self._current_frame)

            if cal is not None:
                x_world, y_world = pixel_to_world(
                    x_pixel, y_pixel, cal.origin_px,
                    cal.scale, cal.axis_rotation_deg,
                )
            else:
                x_world, y_world = 0.0, 0.0

            self._collector.record(
                frame=self._current_frame, timestamp=timestamp,
                x_world=x_world, y_world=y_world,
                x_pixel=x_pixel, y_pixel=y_pixel,
            )

            dot = TrackedPointItem()
            dot.setPos(scene_pos)
            self._scene.addItem(dot)

            self._data_table.update_from_collector(self._collector, self._total_frames)
            self._plot_panel.update_from_collector(self._collector, self._total_frames)

            if self._current_frame + 1 < self._total_frames:
                self._current_frame += 1
                self._show_frame(self._current_frame)

        elif mode in (AppMode.CALIBRATING_A, AppMode.CALIBRATING_B, AppMode.SETTING_ORIGIN):
            self._cal_controller.on_canvas_click(scene_pos)

    def _on_mode_changed(self, mode: AppMode):
        self._mode_label.setText(f"Mode: {mode.name}")

    def _on_endpoint_a(self, pos):
        item = CalibrationPointItem(role="A")
        item.setPos(pos)
        self._scene.addItem(item)

    def _on_endpoint_b(self, pos):
        item = CalibrationPointItem(role="B")
        item.setPos(pos)
        self._scene.addItem(item)

    def _on_calibration_complete(self, cal: CalibrationData):
        pass

    def _on_origin_set(self, pos):
        item = OriginItem()
        item.setPos(pos)
        self._scene.addItem(item)

    def _start_calibration(self):
        self._cal_controller.set_mode_transition(AppMode.CALIBRATING_A)
        self._status_label.setText("Calibration: click to set point A")

    def _start_set_origin(self):
        self._cal_controller.set_mode_transition(AppMode.SETTING_ORIGIN)
        self._status_label.setText("Click to set origin point")

    def _reset_calibration(self):
        self._cal_controller.set_mode_transition(AppMode.IDLE)
        self._status_label.setText("Calibration reset")

    def _load_calibration(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Calibration", "calibrations", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path) as f:
                import json
                data = json.load(f)
            cal = CalibrationData.from_dict(data)
            self._cal_controller.load_calibration(cal, self._video_path or "")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load calibration:\n{e}")

    def _save_calibration(self):
        if self._video_path is None:
            return
        self._cal_controller.save_current(self._video_path)

    def _export_standard_csv(self):
        if self._video_path is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Standard CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return
        exporter = CsvExporter(
            self._video_path, self._fps, self._total_frames,
            calibration=self._cal_controller._calibration,
            collector=self._collector,
        )
        exporter.write_standard(path)
        self._status_label.setText(f"Exported: {path}")

    def _export_full_csv(self):
        if self._video_path is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Full CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return
        exporter = CsvExporter(
            self._video_path, self._fps, self._total_frames,
            calibration=self._cal_controller._calibration,
            collector=self._collector,
        )
        exporter.write_full(path)
        self._status_label.setText(f"Exported: {path}")

    def _reset_view(self):
        self._view.reset_view()

    def _zoom_in(self):
        self._view.zoom_in()

    def _zoom_out(self):
        self._view.zoom_out()

    def _seek_to_frame(self, frame: int):
        if frame < 0 or frame >= self._total_frames:
            return
        self._current_frame = frame
        self._show_frame(frame)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space or event.key() == Qt.Key_Right:
            if self._current_frame + 1 < self._total_frames:
                self._current_frame += 1
                self._show_frame(self._current_frame)
        elif event.key() == Qt.Key_Left:
            if self._current_frame > 0:
                self._current_frame -= 1
                self._show_frame(self._current_frame)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self._decoder is not None:
            self._decoder.close()
        super().closeEvent(event)
