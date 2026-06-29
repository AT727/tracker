from __future__ import annotations

from functools import partial

import numpy as np

import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from wavealigner.model import Trial, TrialCollection
from wavealigner.plotting import TRIAL_COLORS, build_figure
from wavealigner.stats import compute_trial_stats


class WaveAlignerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Wave Aligner")
        self.resize(1400, 700)
        self._collection = TrialCollection()
        self._trial_widgets: dict[Trial, dict] = {}
        self._axis_history: list[tuple] = []
        self._axis_history_index: int = -1
        self._build_ui()
        self._build_menus()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        # ── Left: matplotlib canvas ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._fig = None
        self._canvas = FigureCanvasQTAgg(build_figure(
            np.array([0]), [], [], [], [], None, None, [], [], None, None
        ))
        self._canvas.setMinimumWidth(600)
        left_layout.addWidget(self._canvas, stretch=1)

        # Custom toolbar
        toolbar_layout = QHBoxLayout()
        self._undo_btn = QPushButton("\u21A9 Undo")
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(self._on_undo)
        self._redo_btn = QPushButton("\u21AA Redo")
        self._redo_btn.setEnabled(False)
        self._redo_btn.clicked.connect(self._on_redo)
        edit_axes_btn = QPushButton("Edit Axes")
        edit_axes_btn.clicked.connect(self._on_edit_axes)
        toolbar_layout.addWidget(self._undo_btn)
        toolbar_layout.addWidget(self._redo_btn)
        toolbar_layout.addWidget(edit_axes_btn)
        toolbar_layout.addStretch()
        left_layout.addLayout(toolbar_layout)

        # ── Right: scrollable control panel ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(320)
        scroll.setMaximumWidth(400)

        self._controls_container = QWidget()
        self._controls_layout = QVBoxLayout(self._controls_container)
        self._controls_layout.setSpacing(4)
        scroll.setWidget(self._controls_container)

        right_layout.addWidget(QLabel("<b>Trial Controls</b>"), 0)
        right_layout.addWidget(scroll, stretch=1)

        # ── Summary section ──
        summary_group = QGroupBox("Statistics")
        summary_layout = QVBoxLayout(summary_group)
        self._rmse_label = QLabel("RMSE: \u2014")
        self._nrmse_label = QLabel("NRMSE: \u2014")
        summary_layout.addWidget(self._rmse_label)
        summary_layout.addWidget(self._nrmse_label)
        right_layout.addWidget(summary_group)

        # ── Bottom buttons ──
        btn_layout = QHBoxLayout()
        reset_all_btn = QPushButton("Reset All")
        reset_all_btn.clicked.connect(self._on_reset_all)
        export_btn = QPushButton("Export Graph")
        export_btn.clicked.connect(self._on_export_graph)
        btn_layout.addWidget(reset_all_btn)
        btn_layout.addWidget(export_btn)
        right_layout.addLayout(btn_layout)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

        self._status = QStatusBar()
        self.setStatusBar(self._status)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        load_action = file_menu.addAction("Load CSV...")
        load_action.triggered.connect(self._on_load_csv)
        export_action = file_menu.addAction("Export Graph...")
        export_action.triggered.connect(self._on_export_graph)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(lambda: QMessageBox.about(
            self, "Wave Aligner",
            "Manual waveform alignment tool.\n\n"
            "Load CSV trial files, adjust horizontal shifts, "
            "and observe live RMSE/NRMSE statistics."
        ))

    def _on_load_csv(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select CSV Files", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not paths:
            return
        errors = []
        for path in paths:
            try:
                label = f"Trial {len(self._collection.trials) + 1:02d}"
                trial = self._collection.add_trial(path, label=label)
                self._add_trial_controls(trial)
            except ValueError as e:
                errors.append(str(e))
        if errors:
            QMessageBox.warning(self, "Load Errors", "\n".join(errors))
        self._update_plot()
        self._status.showMessage(f"Loaded {len(paths) - len(errors)} trial(s). "
                                 f"Total: {len(self._collection.trials)}")

    def _add_trial_controls(self, trial: Trial) -> None:
        color = TRIAL_COLORS[len(self._trial_widgets) % len(TRIAL_COLORS)]
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        layout = QGridLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Visibility checkbox
        cb = QCheckBox()
        cb.setChecked(trial.visible)
        cb.setStyleSheet(f"QCheckBox::indicator {{ width: 16px; height: 16px; }}")
        cb.toggled.connect(lambda checked, t=trial: self._on_visibility_toggled(t, checked))

        # Label + color indicator
        name_label = QLabel(f'<span style="color:{color}">\u25cf</span> {trial.label}')
        shift_label = QLabel("Shift: 0.000 s")

        # Spinbox for precise entry
        spin = QDoubleSpinBox()
        spin.setRange(-10.0, 10.0)
        spin.setSingleStep(0.01)
        spin.setDecimals(3)
        spin.setValue(0.0)
        spin.valueChanged.connect(lambda val, t=trial, sl=shift_label: self._on_shift_changed(t, val, sl))

        # Slider for quick drag
        slider = QSlider(Qt.Horizontal)
        slider.setRange(-1000, 1000)
        slider.setValue(0)
        slider.valueChanged.connect(
            lambda val, t=trial, sp=spin, sl=shift_label: self._on_slider_dragged(t, val, sp, sl)
        )

        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.setFixedWidth(60)
        reset_btn.clicked.connect(
            lambda checked, t=trial, sp=spin, sl=slider, sll=shift_label: self._on_reset_trial(t, sp, sl, sll)
        )

        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(60)
        remove_btn.clicked.connect(lambda checked, t=trial: self._on_remove_trial(t))

        layout.addWidget(cb, 0, 0, 1, 1)
        layout.addWidget(name_label, 0, 1, 1, 1)
        layout.addWidget(shift_label, 0, 2, 1, 1)
        layout.addWidget(spin, 1, 0, 1, 2)
        layout.addWidget(slider, 1, 2, 1, 1)
        layout.addWidget(reset_btn, 2, 0, 1, 1)
        layout.addWidget(remove_btn, 2, 1, 1, 1)

        self._controls_layout.addWidget(frame)
        self._trial_widgets[trial] = {
            "frame": frame,
            "checkbox": cb,
            "spin": spin,
            "slider": slider,
            "shift_label": shift_label,
        }

    def _on_visibility_toggled(self, trial: Trial, checked: bool) -> None:
        trial.visible = checked
        self._update_plot()

    def _on_shift_changed(self, trial: Trial, value: float, shift_label: QLabel) -> None:
        trial.shift_s = value
        shift_label.setText(f"Shift: {value:+.3f} s")
        self._update_plot()

    def _on_slider_dragged(self, trial: Trial, value: int, spin: QDoubleSpinBox, shift_label: QLabel) -> None:
        shift = value / 100.0
        spin.blockSignals(True)
        spin.setValue(shift)
        spin.blockSignals(False)
        trial.shift_s = shift
        shift_label.setText(f"Shift: {shift:+.3f} s")
        self._update_plot()

    def _on_reset_trial(self, trial: Trial, spin: QDoubleSpinBox, slider: QSlider, shift_label: QLabel) -> None:
        trial.shift_s = 0.0
        trial.visible = True
        spin.blockSignals(True)
        spin.setValue(0.0)
        spin.blockSignals(False)
        slider.setValue(0)
        shift_label.setText("Shift: 0.000 s")
        self._trial_widgets[trial]["checkbox"].setChecked(True)
        self._update_plot()

    def _on_reset_all(self) -> None:
        for trial, widgets in self._trial_widgets.items():
            widgets["spin"].blockSignals(True)
            widgets["spin"].setValue(0.0)
            widgets["spin"].blockSignals(False)
            widgets["slider"].setValue(0)
            widgets["shift_label"].setText("Shift: 0.000 s")
            widgets["checkbox"].setChecked(True)
            trial.shift_s = 0.0
            trial.visible = True
        self._update_plot()

    def _on_remove_trial(self, trial: Trial) -> None:
        widget_dict = self._trial_widgets.pop(trial, None)
        if widget_dict:
            self._controls_layout.removeWidget(widget_dict["frame"])
            widget_dict["frame"].deleteLater()
        self._collection.remove_trial(trial)
        self._rename_trials()
        self._update_plot()

    def _rename_trials(self) -> None:
        for i, trial in enumerate(self._collection.trials):
            trial.label = f"Trial {i + 1:02d}"

    def _on_export_graph(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Graph", "wave_aligner.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)"
        )
        if path:
            self._fig.savefig(path, dpi=150, bbox_inches="tight",
                              facecolor="white", edgecolor="none")
            self._status.showMessage(f"Exported -> {path}")

    def _on_edit_axes(self) -> None:
        if self._fig is None:
            return
        ax = self._fig.axes[0]
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()

        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Axes Limits")
        form = QFormLayout(dlg)

        xmin_spin = QDoubleSpinBox()
        xmin_spin.setRange(-1e6, 1e6)
        xmin_spin.setDecimals(4)
        xmin_spin.setValue(xmin)
        xmax_spin = QDoubleSpinBox()
        xmax_spin.setRange(-1e6, 1e6)
        xmax_spin.setDecimals(4)
        xmax_spin.setValue(xmax)
        ymin_spin = QDoubleSpinBox()
        ymin_spin.setRange(-1e6, 1e6)
        ymin_spin.setDecimals(4)
        ymin_spin.setValue(ymin)
        ymax_spin = QDoubleSpinBox()
        ymax_spin.setRange(-1e6, 1e6)
        ymax_spin.setDecimals(4)
        ymax_spin.setValue(ymax)

        form.addRow("X min:", xmin_spin)
        form.addRow("X max:", xmax_spin)
        form.addRow("Y min:", ymin_spin)
        form.addRow("Y max:", ymax_spin)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() == QDialog.Accepted:
            self._push_axis_state()
            ax.set_xlim(xmin_spin.value(), xmax_spin.value())
            ax.set_ylim(ymin_spin.value(), ymax_spin.value())
            self._canvas.draw()

    def _push_axis_state(self) -> None:
        if self._fig is None:
            return
        ax = self._fig.axes[0]
        state = (ax.get_xlim(), ax.get_ylim())
        self._axis_history = self._axis_history[:self._axis_history_index + 1]
        self._axis_history.append(state)
        self._axis_history_index = len(self._axis_history) - 1
        self._undo_btn.setEnabled(self._axis_history_index > 0)
        self._redo_btn.setEnabled(False)

    def _apply_axis_state(self) -> None:
        if self._fig is None or self._axis_history_index < 0:
            return
        xlim, ylim = self._axis_history[self._axis_history_index]
        ax = self._fig.axes[0]
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        self._canvas.draw()
        self._undo_btn.setEnabled(self._axis_history_index > 0)
        self._redo_btn.setEnabled(self._axis_history_index < len(self._axis_history) - 1)

    def _on_undo(self) -> None:
        if self._axis_history_index > 0:
            self._axis_history_index -= 1
            self._apply_axis_state()

    def _on_redo(self) -> None:
        if self._axis_history_index < len(self._axis_history) - 1:
            self._axis_history_index += 1
            self._apply_axis_state()

    def _update_plot(self) -> None:
        collection = self._collection
        visible = collection.visible_trials

        # Full data for display
        t_arrays = [t.df["t (s)"].values - t.shift_s for t in collection.trials]
        y_arrays = [t.df["correct y"].values for t in collection.trials]
        trial_labels = [t.label for t in collection.trials]

        # Aligned signals + stats (visible trials only, overlap region)
        interp_signals = collection.aligned_signals(visible_only=True)
        stats = compute_trial_stats(interp_signals) if len(interp_signals) >= 2 else {
            "mean_y": None, "std_y": None,
            "rmse_vals": [], "nrmse_vals": [],
            "mean_rmse": None, "mean_nrmse": None,
        }
        _, _, t_common = collection.overlap_region(visible_only=True)

        # Pad rmse/nrmse to match all trials (non-visible get None)
        rmse_vals, nrmse_vals = [], []
        vi = 0
        for t in collection.trials:
            if t.visible:
                rmse_vals.append(stats["rmse_vals"][vi] if vi < len(stats["rmse_vals"]) else None)
                nrmse_vals.append(stats["nrmse_vals"][vi] if vi < len(stats["nrmse_vals"]) else None)
                vi += 1
            else:
                rmse_vals.append(None)
                nrmse_vals.append(None)

        # Close previous figure to avoid memory leak
        if self._fig is not None:
            import matplotlib.pyplot as plt
            plt.close(self._fig)

        # Build figure
        self._fig = build_figure(
            t_common=t_common,
            interp_signals=interp_signals,
            t_arrays=t_arrays,
            y_arrays=y_arrays,
            trial_labels=trial_labels,
            mean_y=stats["mean_y"],
            std_y=stats["std_y"],
            rmse_vals=rmse_vals,
            nrmse_vals=nrmse_vals,
            mean_rmse=stats["mean_rmse"],
            mean_nrmse=stats["mean_nrmse"],
        )

        # Replace canvas content
        self._canvas.figure = self._fig
        self._canvas.draw()

        # Reset axis history with auto-scaled state from fresh build
        self._axis_history.clear()
        self._axis_history_index = -1
        self._push_axis_state()

        # Update sidebar summary
        if stats["mean_rmse"] is not None:
            self._rmse_label.setText(f"RMSE: {stats['mean_rmse']:.4f} cm")
            self._nrmse_label.setText(f"NRMSE: {stats['mean_nrmse']:.2f}%")
        else:
            self._rmse_label.setText("RMSE: \u2014 (need \u22652 visible trials)")
            self._nrmse_label.setText("NRMSE: \u2014")
