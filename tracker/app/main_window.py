"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QElapsedTimer, Qt, QTimer, QEvent
from PyQt5.QtGui import QCursor, QKeySequence, QPixmap, QImage
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollBar,
    QShortcut,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from tracker.calibration.controller import CalibrationController, CalibrationMode
from tracker.app.autoclicker import (
    AutoClickerConfigDialog,
    AutoClickerController,
    format_mapping_summary,
)
from tracker.calibration.data import CalibrationData
from tracker.calibration.persistence import (
    CalibrationStore,
    preset_path,
    sidecar_path_for_video,
)
from tracker.canvas.view import CanvasView
from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.export.csv_writer import export_csv
from tracker.panels.data_table import DataTablePanel
from tracker.panels.plot_panel import PlotPanel
from tracker.panels.series_toolbar import SeriesToolbar
from tracker.tracking.collector import TrackingCollector
from tracker.tracking.mark import Mark
from tracker.video.decoder_worker import VideoDecoderWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tracker")
        self.resize(1280, 800)

        self.collector = TrackingCollector()
        self.pipeline = CoordinatePipeline()
        self._video_path: Path | None = None
        self._fps = 30.0
        self._frame_count = 0
        self._current_frame = 0
        self._current_timestamp = 0.0
        self._width = 0
        self._height = 0
        self._calibration_snapshot: CalibrationData | None = None
        self._syncing_pan_sliders = False
        self._marks_by_frame: dict[int, list[Mark]] = {}
        self._plot_refresh_timer = QElapsedTimer()
        self._plot_refresh_timer.start()
        self._min_plot_refresh_interval_ms = 200
        self._autoclicker = AutoClickerController(self)
        self._autoclicker_enabled_action: QAction | None = None

        self._decoder = VideoDecoderWorker()
        self._decoder.opened.connect(self._on_video_opened)
        self._decoder.frame_ready.connect(self._on_frame_ready)
        self._decoder.frame_failed.connect(self._on_frame_failed)
        self._decoder.open_failed.connect(self._on_open_failed)
        self._decoder.start()

        self._calibration = CalibrationController(
            on_changed=self._on_calibration_changed,
            on_mode_changed=self._on_calibration_mode_changed,
        )

        self._canvas = CanvasView()
        self._canvas.pixel_pressed.connect(self._on_pixel_pressed)
        self._canvas.pixel_moved.connect(self._on_pixel_moved)
        self._canvas.pixel_released.connect(self._on_pixel_released)
        self._canvas.viewport_changed.connect(self._sync_pan_sliders)
        self._canvas.key_pressed.connect(self._on_canvas_key_pressed)
        self._canvas.key_released.connect(self._on_canvas_key_released)
        self._autoclicker.click_requested.connect(self._on_autoclick_requested)
        self._autoclicker.enabled_changed.connect(lambda _: self._update_status())
        self._autoclicker.mapping_changed.connect(lambda _: self._update_status())

        self._build_ui()
        self._build_menus()
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._cancel_calibration)
        self._schedule_refresh()
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        canvas_area = QWidget()
        canvas_grid = QGridLayout(canvas_area)
        canvas_grid.setContentsMargins(0, 0, 0, 0)
        canvas_grid.setSpacing(2)
        canvas_grid.addWidget(self._canvas, 0, 0)
        self._pan_v_slider = QScrollBar(Qt.Vertical)
        self._pan_v_slider.setRange(0, 1000)
        self._pan_v_slider.setEnabled(False)
        self._pan_v_slider.valueChanged.connect(self._on_pan_v_changed)
        canvas_grid.addWidget(self._pan_v_slider, 0, 1)
        self._pan_h_slider = QScrollBar(Qt.Horizontal)
        self._pan_h_slider.setRange(0, 1000)
        self._pan_h_slider.setEnabled(False)
        self._pan_h_slider.valueChanged.connect(self._on_pan_h_changed)
        canvas_grid.addWidget(self._pan_h_slider, 1, 0)
        canvas_grid.setRowStretch(0, 1)
        canvas_grid.setColumnStretch(0, 1)
        left_layout.addWidget(canvas_area, stretch=1)

        nav = QHBoxLayout()
        self._prev_btn = QPushButton("Prev")
        self._prev_btn.clicked.connect(self._go_prev)
        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._go_next)
        self._scrubber = QSlider(Qt.Horizontal)
        self._scrubber.setMinimum(0)
        self._scrubber.valueChanged.connect(self._on_scrub)
        self._frame_spin = QSpinBox()
        self._frame_spin.setMinimum(1)
        self._frame_spin.valueChanged.connect(self._on_spin_jump)
        nav.addWidget(self._prev_btn)
        nav.addWidget(self._next_btn)
        nav.addWidget(self._scrubber, stretch=1)
        nav.addWidget(QLabel("Frame:"))
        nav.addWidget(self._frame_spin)
        left_layout.addLayout(nav)

        overlay_row = QHBoxLayout()
        self._show_stick = QCheckBox("Show stick")
        self._show_stick.toggled.connect(self._update_overlays)
        self._show_grid = QCheckBox("Show grid")
        self._show_grid.toggled.connect(self._update_overlays)
        self._calibrate_btn = QPushButton("Calibrate")
        self._calibrate_btn.clicked.connect(self._start_calibration)
        self._origin_btn = QPushButton("Set Origin")
        self._origin_btn.clicked.connect(self._start_origin_calibration)
        self._cancel_cal_btn = QPushButton("Cancel")
        self._cancel_cal_btn.clicked.connect(self._cancel_calibration)
        self._cancel_cal_btn.setEnabled(False)
        overlay_row.addWidget(self._show_stick)
        overlay_row.addWidget(self._show_grid)
        overlay_row.addWidget(self._calibrate_btn)
        overlay_row.addWidget(self._origin_btn)
        overlay_row.addWidget(self._cancel_cal_btn)
        overlay_row.addStretch()
        left_layout.addLayout(overlay_row)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        self._series_toolbar = SeriesToolbar()
        self._series_toolbar.series_changed.connect(self._on_series_changed)
        self._series_toolbar.add_series_requested.connect(self._on_add_series)
        self._data_table = DataTablePanel()
        self._data_table.go_to_frame_requested.connect(self._on_go_to_frame_requested)
        self._table_skip_warning = QLabel("")
        self._table_skip_warning.setObjectName("tableSkipWarning")
        self._table_skip_warning.hide()
        self._plot_panel = PlotPanel()
        self._show_table = QCheckBox("Show table")
        self._show_table.setChecked(True)
        self._show_table.toggled.connect(self._toggle_table)
        self._show_plot = QCheckBox("Show plot")
        self._show_plot.setChecked(True)
        self._show_plot.toggled.connect(self._toggle_plot)
        right_layout.addWidget(self._series_toolbar)
        right_layout.addWidget(self._table_skip_warning)
        right_layout.addWidget(self._show_table)
        right_layout.addWidget(self._data_table, stretch=1)
        right_layout.addWidget(self._show_plot)
        right_layout.addWidget(self._plot_panel, stretch=1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._update_status()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        open_action = QAction("Open Video...", self)
        open_action.triggered.connect(self._open_video_dialog)
        file_menu.addAction(open_action)
        export_action = QAction("Export CSV...", self)
        export_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        cal_menu = self.menuBar().addMenu("&Calibration")
        save_preset_action = QAction("Save Current as Preset", self)
        save_preset_action.triggered.connect(self._save_preset)
        cal_menu.addAction(save_preset_action)
        clear_preset_action = QAction("Clear Preset", self)
        clear_preset_action.triggered.connect(self._clear_preset)
        cal_menu.addAction(clear_preset_action)
        apply_preset_action = QAction("Apply Preset to This Video", self)
        apply_preset_action.triggered.connect(self._apply_preset)
        cal_menu.addAction(apply_preset_action)
        cal_menu.addSeparator()
        calibrate_action = QAction("Calibrate Stick...", self)
        calibrate_action.triggered.connect(self._start_calibration)
        cal_menu.addAction(calibrate_action)
        origin_action = QAction("Set Origin...", self)
        origin_action.triggered.connect(self._start_origin_calibration)
        cal_menu.addAction(origin_action)

        autoclicker_menu = self.menuBar().addMenu("&Autoclicker")
        self._autoclicker_enabled_action = QAction("Enabled", self)
        self._autoclicker_enabled_action.setCheckable(True)
        self._autoclicker_enabled_action.toggled.connect(self._set_autoclicker_enabled)
        autoclicker_menu.addAction(self._autoclicker_enabled_action)
        config_action = QAction("Configure...", self)
        config_action.triggered.connect(self._open_autoclicker_config)
        autoclicker_menu.addAction(config_action)

        tb = QToolBar("Navigation")
        self.addToolBar(tb)
        tb.addAction("Open", self._open_video_dialog)
        tb.addAction("Export CSV", self._export_csv)

    def _set_autoclicker_enabled(self, enabled: bool) -> None:
        self._autoclicker.set_enabled(enabled)
        self._update_status()

    def _open_autoclicker_config(self) -> None:
        dialog = AutoClickerConfigDialog(self._autoclicker.mapping, self)
        if dialog.exec_() != dialog.Accepted:
            return
        mapping = dialog.mapping()
        if mapping is None:
            QMessageBox.warning(self, "Autoclicker", "Each key can only be assigned once.")
            return
        self._autoclicker.set_mapping(mapping)
        self._update_status()

    def closeEvent(self, event) -> None:
        self._autoclicker.release_all_keys()
        self._decoder.stop_worker()
        super().closeEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self._autoclicker.release_all_keys()
        super().changeEvent(event)

    def _open_video_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)",
        )
        if path:
            self._load_video(path)

    def _load_video(self, path: str) -> None:
        self._video_path = Path(path)
        self._current_frame = 0
        self._decoder.open(path)
        sidecar = sidecar_path_for_video(path)
        cal = CalibrationStore.load(sidecar)
        if cal:
            self._calibration.set_data(cal)
            self.pipeline.set_calibration(cal)
        else:
            preset = CalibrationStore.load_preset()
            if preset:
                self._calibration.set_data(preset)
                self.pipeline.set_calibration(preset)
            else:
                self._calibration.set_data(CalibrationData())
                self.pipeline.set_calibration(CalibrationData())
        # New video should start with a clean slate.
        self.collector.clear_marks()
        self._marks_by_frame.clear()
        self._refresh_panels()
        self._update_overlays()

    def _on_video_opened(self, fps: float, frame_count: int, width: int, height: int) -> None:
        self._fps = fps
        self._frame_count = max(frame_count, 1)
        self._width = width
        self._height = height
        self._canvas.set_image_size(width, height)
        self._sync_pan_sliders()
        self._scrubber.setMaximum(max(frame_count - 1, 0))
        self._frame_spin.setMaximum(max(frame_count, 1))
        self._frame_spin.blockSignals(True)
        self._frame_spin.setValue(self._current_frame + 1)
        self._frame_spin.blockSignals(False)
        self._scrubber.blockSignals(True)
        self._scrubber.setValue(self._current_frame)
        self._scrubber.blockSignals(False)
        self._go_to_frame(self._current_frame, prefetch=True)

    def _on_frame_ready(self, index: int, qimage: QImage, timestamp_s: float) -> None:
        if index != self._current_frame:
            return
        pixmap = QPixmap.fromImage(qimage)
        self._canvas.tracker_scene.set_frame_pixmap(pixmap)
        self._current_timestamp = timestamp_s
        self._canvas.tracker_scene.set_frame_label(index, self._frame_count, timestamp_s)
        self._canvas.viewport().repaint()
        self._update_overlays()
        self._update_status()

    def _on_frame_failed(self, index: int) -> None:
        if index == self._current_frame:
            self._status.showMessage(f"Failed to decode frame {index}")

    def _on_open_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Video Error", message)

    def _on_pixel_pressed(self, px: float, py: float) -> None:
        if self._calibration.mode != CalibrationMode.NONE:
            if self._calibration.begin_point():
                self._calibration.update_draft(px, py)
                self._update_overlays()

    def _on_pixel_moved(self, px: float, py: float) -> None:
        if self._calibration.mode != CalibrationMode.NONE:
            if self._calibration.update_draft(px, py):
                self._update_overlays()

    def _on_pixel_released(self, px: float, py: float) -> None:
        if self._calibration.mode != CalibrationMode.NONE:
            if self._calibration.commit_point(px, py, self):
                self._update_overlays()
                if self._calibration.mode == CalibrationMode.NONE and self._video_path:
                    self._calibration_snapshot = None
                    CalibrationStore.save(
                        sidecar_path_for_video(self._video_path),
                        self._calibration.data,
                    )
            return

        self._record_click_at(px, py)

    def _record_click_at(self, px: float, py: float) -> None:
        if self._frame_count <= 0:
            return

        mark, _ = self.collector.upsert_mark(
            frame=self._current_frame,
            timestamp_s=self._current_timestamp,
            px=px,
            py=py,
        )
        self._sync_marks_for_frame(mark.frame)
        self._advance_frame()
        self._canvas.tracker_scene.show_click_feedback(px, py)
        if self._show_table.isChecked():
            # Defer table work so rapid clicks stay responsive.
            QTimer.singleShot(0, self._refresh_table)
        self._maybe_refresh_plot()

    def _on_autoclick_requested(self) -> None:
        pixel = self._current_canvas_pixel()
        if pixel is None:
            return
        self._record_click_at(pixel[0], pixel[1])

    def _current_canvas_pixel(self) -> tuple[float, float] | None:
        view_pos = self._canvas.viewport().mapFromGlobal(QCursor.pos())
        if not self._canvas.viewport().rect().contains(view_pos):
            return None
        scene_pos = self._canvas.mapToScene(view_pos)
        px, py = self._canvas.scene_to_pixel(scene_pos.x(), scene_pos.y())
        if 0 <= px <= self._width and 0 <= py <= self._height:
            return px, py
        return None

    def _on_canvas_key_pressed(self, key: int, is_auto_repeat: bool) -> None:
        self._autoclicker.handle_key_press(key, is_auto_repeat)

    def _on_canvas_key_released(self, key: int, is_auto_repeat: bool) -> None:
        self._autoclicker.handle_key_release(key, is_auto_repeat)

    def _on_pan_h_changed(self, value: int) -> None:
        if self._syncing_pan_sliders:
            return
        self._canvas.set_pan_from_sliders(value, self._pan_v_slider.value())

    def _on_pan_v_changed(self, value: int) -> None:
        if self._syncing_pan_sliders:
            return
        self._canvas.set_pan_from_sliders(self._pan_h_slider.value(), value)

    def _sync_pan_sliders(self) -> None:
        vp = self._canvas.viewport_state
        vw = float(self._canvas.viewport().width())
        vh = float(self._canvas.viewport().height())
        h_val, v_val, h_en, v_en = vp.pan_slider_values(
            vw, vh, float(self._width), float(self._height)
        )
        self._syncing_pan_sliders = True
        self._pan_h_slider.setEnabled(h_en)
        self._pan_v_slider.setEnabled(v_en)
        self._pan_h_slider.setValue(h_val)
        self._pan_v_slider.setValue(v_val)
        self._syncing_pan_sliders = False

    def _advance_frame(self) -> None:
        if self._current_frame < self._frame_count - 1:
            self._go_to_frame(self._current_frame + 1, prefetch=True)

    def _go_prev(self) -> None:
        if self._current_frame > 0:
            self._go_to_frame(self._current_frame - 1)

    def _go_next(self) -> None:
        if self._current_frame < self._frame_count - 1:
            self._go_to_frame(self._current_frame + 1, prefetch=True)

    def _on_scrub(self, value: int) -> None:
        if value != self._current_frame:
            self._go_to_frame(value, coalesce=True, prefetch=True)

    def _on_spin_jump(self, value: int) -> None:
        self._go_to_frame(value - 1, coalesce=True, prefetch=True)

    def _go_to_frame(
        self,
        index: int,
        prefetch: bool = False,
        coalesce: bool = False,
    ) -> None:
        index = max(0, min(index, max(self._frame_count - 1, 0)))
        self._current_frame = index
        self._scrubber.blockSignals(True)
        self._scrubber.setValue(index)
        self._scrubber.blockSignals(False)
        self._frame_spin.blockSignals(True)
        self._frame_spin.setValue(index + 1)
        self._frame_spin.blockSignals(False)
        if coalesce:
            self._decoder.scrub_to_frame(index)
        else:
            self._decoder.request_frame(index)
        if prefetch:
            self._decoder.prefetch(index + 1, 5)
        self._canvas.tracker_scene.clear_click_feedback()
        self._refresh_marks_on_canvas()
        self._update_status()

    def _on_calibration_changed(self, data: CalibrationData) -> None:
        self.pipeline.set_calibration(data)
        self._update_overlays()
        self._schedule_refresh()

    def _on_calibration_mode_changed(self, mode: CalibrationMode) -> None:
        in_calibration = mode != CalibrationMode.NONE
        self._cancel_cal_btn.setEnabled(in_calibration)
        if mode == CalibrationMode.SET_ORIGIN:
            self._show_grid.setChecked(True)
        self._update_status()

    def _start_calibration(self) -> None:
        self._calibration_snapshot = self._copy_calibration(self._calibration.data)
        self._calibration.start_stick_calibration()
        self._show_stick.setChecked(True)
        self._show_grid.setChecked(True)
        self._update_overlays()

    def _start_origin_calibration(self) -> None:
        self._calibration_snapshot = self._copy_calibration(self._calibration.data)
        self._calibration.start_origin_calibration()
        self._show_grid.setChecked(True)
        self._update_overlays()

    def _cancel_calibration(self) -> None:
        if self._calibration.mode == CalibrationMode.NONE:
            return
        if self._calibration_snapshot is not None:
            self._calibration.set_data(self._calibration_snapshot)
        self._calibration.cancel()
        self._calibration_snapshot = None
        self._update_overlays()
        self._update_status()

    @staticmethod
    def _copy_calibration(data: CalibrationData) -> CalibrationData:
        return CalibrationData(
            stick_a_px=data.stick_a_px,
            stick_b_px=data.stick_b_px,
            known_length_cm=data.known_length_cm,
            origin_px=data.origin_px,
            scale_cm_per_px=data.scale_cm_per_px,
        )

    def _update_overlays(self) -> None:
        scene = self._canvas.tracker_scene
        cal = self._calibration.data
        mode = self._calibration.mode
        draft = self._calibration.draft
        scene.set_stick_visible(self._show_stick.isChecked())
        scene.set_grid_visible(self._show_grid.isChecked())

        stick_a = cal.stick_a_px
        stick_b = cal.stick_b_px
        if mode == CalibrationMode.STICK_A and draft:
            stick_a = draft
        elif mode == CalibrationMode.STICK_B and draft:
            stick_b = draft

        if stick_a and stick_b:
            scene.update_stick(
                stick_a[0], stick_a[1], stick_b[0], stick_b[1]
            )
        elif stick_a:
            ax, ay = stick_a
            scene.update_stick(ax, ay, ax, ay)

        grid_ox: float | None = None
        grid_oy: float | None = None
        if mode == CalibrationMode.SET_ORIGIN and draft:
            grid_ox, grid_oy = draft
        elif cal.origin_px:
            grid_ox, grid_oy = cal.origin_px
        elif mode == CalibrationMode.SET_ORIGIN and cal.stick_a_px and cal.stick_b_px:
            ax, ay = cal.stick_a_px
            bx, by = cal.stick_b_px
            grid_ox = (ax + bx) / 2.0
            grid_oy = (ay + by) / 2.0
        if grid_ox is not None and grid_oy is not None:
            scene.update_origin_grid(grid_ox, grid_oy)

    def _refresh_marks_on_canvas(self) -> None:
        marks_data = [
            (mark.px, mark.py, "square")
            for mark in self._marks_by_frame.get(self._current_frame, [])
        ]
        self._canvas.tracker_scene.set_marks(marks_data)

    def _sync_marks_for_frame(self, frame: int) -> None:
        marks = [mark for mark in self.collector.marks if mark.frame == frame]
        if marks:
            self._marks_by_frame[frame] = marks
        else:
            self._marks_by_frame.pop(frame, None)

    def _schedule_refresh(self) -> None:
        QTimer.singleShot(0, self._refresh_panels)

    def _refresh_panels(self) -> None:
        self._series_toolbar.refresh(self.collector)
        self._refresh_table()
        self._plot_panel.refresh(self.collector, self.pipeline)

    def _refresh_table(self) -> None:
        active_series_id = self.collector.active_series_id
        skip_frames = self._find_skipped_frames(active_series_id)
        gap_after_frames = {start for start, _ in skip_frames}
        self._data_table.refresh(
            self.collector,
            self.pipeline,
            series_id=active_series_id,
            gap_after_frames=gap_after_frames,
        )
        self._update_skip_warning(skip_frames)

    def _find_skipped_frames(self, series_id: str | None) -> list[tuple[int, int]]:
        if not series_id:
            return []
        frame_indices = sorted({mark.frame for mark in self.collector.marks_for_series(series_id)})
        skipped_ranges: list[tuple[int, int]] = []
        for current, following in zip(frame_indices, frame_indices[1:]):
            if following - current > 1:
                skipped_ranges.append((current, following))
        return skipped_ranges

    def _update_skip_warning(self, skipped_ranges: list[tuple[int, int]]) -> None:
        missing_count = sum(end - start - 1 for start, end in skipped_ranges)
        if missing_count <= 0:
            self._table_skip_warning.hide()
            self._table_skip_warning.clear()
            return
        self._table_skip_warning.setText(f"[!] {missing_count} skipped frame(s) detected")
        self._table_skip_warning.show()

    def _maybe_refresh_plot(self) -> None:
        if not self._show_plot.isChecked():
            return
        if self._plot_refresh_timer.elapsed() < self._min_plot_refresh_interval_ms:
            return
        self._plot_refresh_timer.restart()
        # Plot redraw is relatively expensive; throttle it to keep click handling responsive.
        QTimer.singleShot(0, lambda: self._plot_panel.refresh(self.collector, self.pipeline))

    def _on_series_changed(self, series_id: str) -> None:
        self.collector.set_active_series(series_id)
        self._refresh_marks_on_canvas()
        self._refresh_table()

    def _on_add_series(self) -> None:
        self.collector.add_series()
        self._series_toolbar.refresh(self.collector)
        if self.collector.active_series_id:
            self.collector.set_active_series(self.collector.active_series_id)
        self._refresh_table()

    def _on_go_to_frame_requested(self, frame_index: int) -> None:
        self._go_to_frame(frame_index, prefetch=True, coalesce=True)

    def _toggle_table(self, visible: bool) -> None:
        self._data_table.setVisible(visible)

    def _toggle_plot(self, visible: bool) -> None:
        self._plot_panel.setVisible(visible)

    def _update_status(self) -> None:
        unit = self.pipeline.unit_suffix
        autoclick_state = "ON" if self._autoclicker.enabled else "OFF"
        mapping_summary = format_mapping_summary(self._autoclicker.mapping)
        frame_info = (
            f"Frame {self._current_frame + 1}/{self._frame_count}  "
            f"t={self._current_timestamp:.4f}s  fps={self._fps:.1f}  units={unit}  "
            f"autoclicker={autoclick_state} [{mapping_summary}]"
        )
        cal_hints = {
            CalibrationMode.STICK_A: "Calibration: drag stick endpoint A, release to confirm",
            CalibrationMode.STICK_B: "Calibration: drag stick endpoint B, release to confirm",
            CalibrationMode.SET_ORIGIN: "Calibration: drag origin, release to confirm",
        }
        hint = cal_hints.get(self._calibration.mode)
        if hint:
            self._status.showMessage(f"{hint}  |  {frame_info}")
        else:
            self._status.showMessage(frame_info)

    def _export_csv(self) -> None:
        if not self.collector.marks:
            QMessageBox.warning(self, "Export", "No marks to export.")
            return
        if not self.pipeline.calibration.is_calibrated:
            QMessageBox.warning(
                self,
                "Export",
                "Calibration is required before exporting x (cm) and y (cm).",
            )
            return
        default_name = "export.csv"
        if self._video_path:
            default_name = f"{self._video_path.stem}_data.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            default_name,
            "CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            export_csv(path, self.collector, self.pipeline)
        except ValueError as exc:
            QMessageBox.warning(self, "Export", str(exc))
            return
        QMessageBox.information(self, "Export", f"Saved to {path}")

    def _save_preset(self) -> None:
        if not self._calibration.data.is_calibrated:
            QMessageBox.warning(
                self,
                "Save Preset",
                "Complete the stick + origin calibration before saving as preset.",
            )
            return
        CalibrationStore.save_preset(self._calibration.data)
        preset = preset_path()
        self._status.showMessage(
            f"Calibration preset saved ({preset.name})", 5000
        )

    def _clear_preset(self) -> None:
        CalibrationStore.clear_preset()
        self._status.showMessage("Calibration preset cleared", 5000)

    def _apply_preset(self) -> None:
        preset = CalibrationStore.load_preset()
        if not preset:
            QMessageBox.warning(
                self,
                "Apply Preset",
                "No saved preset found. Use Calibration > Save Current as Preset first.",
            )
            return
        self._calibration.set_data(preset)
        self.pipeline.set_calibration(preset)
        self._update_overlays()
        self._schedule_refresh()
        self._status.showMessage("Global calibration preset applied", 5000)
