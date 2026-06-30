# Wave Aligner GUI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PyQt5 + matplotlib desktop GUI for manually aligning multiple CSV waveform trials with live RMSE/NRMSE statistics.

**Architecture:** Four-module `wavealigner/` package (`model.py`, `plotting.py`, `stats.py`, `app.py`) plus a root entry point `run_wavealigner.py`. The plotting module reuses style constants and the table builder from the existing `.opencode/skills/plot-trials-threshold/scripts/plot_trials_threshold.py`.

**Tech Stack:** PyQt5, matplotlib, numpy, pandas, scipy

---

### Task 1: Scaffold project structure

**Files:**
- Create: `wavealigner/__init__.py`
- Create: `wavealigner/model.py`
- Create: `wavealigner/stats.py`
- Create: `wavealigner/plotting.py`
- Create: `wavealigner/app.py`
- Create: `run_wavealigner.py`

- [ ] **Step 1: Create the directory and empty files**

```bash
mkdir wavealigner
New-Item -ItemType File -Path wavealigner/__init__.py
New-Item -ItemType File -Path wavealigner/model.py
New-Item -ItemType File -Path wavealigner/stats.py
New-Item -ItemType File -Path wavealigner/plotting.py
New-Item -ItemType File -Path wavealigner/app.py
New-Item -ItemType File -Path run_wavealigner.py
```

- [ ] **Step 2: Verify all files exist**

Run: `Get-ChildItem -Recurse -LiteralPath wavealigner; Test-Path run_wavealigner.py`

Expected: All 6 files listed, `True`

---

### Task 2: Write `model.py` — Trial dataclass and TrialCollection

**Files:**
- Create: `wavealigner/model.py`

- [ ] **Step 1: Write `Trial` dataclass**

Write the following to `wavealigner/model.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Trial:
    path: str
    label: str
    df: pd.DataFrame
    shift_s: float = 0.0
    visible: bool = True
```

- [ ] **Step 2: Write `load_csv()` function**

Append to `wavealigner/model.py`. Exact copy from `plot_trials_threshold.py`'s `load_csv()`:

```python
CSV_REQUIRED_COLUMNS = {"t (s)", "correct y"}


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = df.columns.str.strip()
    if "t" in df.columns and "t (s)" not in df.columns:
        df = df.rename(columns={"t": "t (s)"})
    rename = {col: "correct y" for col in df.columns if col.lower().startswith("correc")}
    if rename:
        df = df.rename(columns=rename)
    elif "y (cm)" in df.columns:
        df = df.rename(columns={"y (cm)": "correct y"})
    missing = CSV_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"{path}: missing required columns.\n"
            f"  Expected: one of 'correct y', 'correc y', 'y (cm)'\n"
            f"  Found: {list(df.columns)}"
        )
    return df[["t (s)", "correct y"]].dropna().reset_index(drop=True)
```

- [ ] **Step 3: Write `TrialCollection` class**

Append to `wavealigner/model.py`:

```python
class TrialCollection:
    def __init__(self) -> None:
        self.trials: list[Trial] = []

    def add_trial(self, path: str, label: str | None = None) -> Trial:
        df = load_csv(path)
        if label is None:
            label = f"Trial {len(self.trials) + 1:02d}"
        trial = Trial(path=path, label=label, df=df.copy())
        self.trials.append(trial)
        return trial

    def remove_trial(self, trial: Trial) -> None:
        self.trials.remove(trial)

    def reset_all(self) -> None:
        for t in self.trials:
            t.shift_s = 0.0
            t.visible = True

    @property
    def visible_trials(self) -> list[Trial]:
        return [t for t in self.trials if t.visible]

    @property
    def t_arrays(self) -> list[np.ndarray]:
        return [t.df["t (s)"].values - t.shift_s for t in self.trials]

    @property
    def y_arrays(self) -> list[np.ndarray]:
        return [t.df["correct y"].values for t in self.trials]

    def overlap_region(self, visible_only: bool = True) -> tuple[float, float, np.ndarray]:
        trials = self.visible_trials if visible_only else self.trials
        if len(trials) < 2:
            t_min = min(t.df["t (s)"].min() - t.shift_s for t in trials)
            t_max = max(t.df["t (s)"].max() - t.shift_s for t in trials)
            return t_min, t_max, np.linspace(t_min, t_max, 1000)
        t_min = max(t.df["t (s)"].values.min() - t.shift_s for t in trials)
        t_max = min(t.df["t (s)"].values.max() - t.shift_s for t in trials)
        n_pts = max(len(t.df) for t in trials)
        t_common = np.linspace(t_min, t_max, n_pts)
        return t_min, t_max, t_common

    def aligned_signals(self, visible_only: bool = True) -> list[np.ndarray]:
        trials = self.visible_trials if visible_only else self.trials
        if len(trials) < 2:
            return []
        _, _, t_common = self.overlap_region(visible_only)
        return [
            np.interp(t_common, t.df["t (s)"].values - t.shift_s, t.df["correct y"].values)
            for t in trials
        ]
```

---

### Task 3: Write `stats.py` — RMSE/NRMSE computation

**Files:**
- Create: `wavealigner/stats.py`

- [ ] **Step 1: Write statistics functions**

Write to `wavealigner/stats.py`:

```python
from __future__ import annotations

import numpy as np


def compute_rmse(signal: np.ndarray, reference: np.ndarray) -> float:
    min_len = min(len(signal), len(reference))
    diff = signal[:min_len] - reference[:min_len]
    return float(np.sqrt(np.mean(diff ** 2)))


def compute_nrmse(rmse: float, y_range: float) -> float:
    if y_range <= 0:
        return 0.0
    return rmse / y_range * 100
```

- [ ] **Step 2: Write the `TrialStatistics` function**

Append to `wavealigner/stats.py`:

```python
def compute_trial_stats(interp_signals: list[np.ndarray]) -> dict:
    if len(interp_signals) < 2:
        return {
            "mean_y": None,
            "std_y": None,
            "rmse_vals": [],
            "nrmse_vals": [],
            "mean_rmse": None,
            "mean_nrmse": None,
        }
    stack = np.vstack(interp_signals)
    mean_y = stack.mean(axis=0)
    std_y = stack.std(axis=0)
    y_range = float(mean_y.max() - mean_y.min())
    if y_range <= 0:
        y_range = 1.0
    rmse_vals = [compute_rmse(s, mean_y) for s in interp_signals]
    nrmse_vals = [compute_nrmse(r, y_range) for r in rmse_vals]
    mean_rmse = float(np.mean(rmse_vals))
    mean_nrmse = float(np.mean(nrmse_vals))
    return {
        "mean_y": mean_y,
        "std_y": std_y,
        "rmse_vals": rmse_vals,
        "nrmse_vals": nrmse_vals,
        "mean_rmse": mean_rmse,
        "mean_nrmse": mean_nrmse,
    }
```

---

### Task 4: Write `plotting.py` — Matplotlib figure builder

**Files:**
- Create: `wavealigner/plotting.py`

This module reuses style constants and the table builder from the reference.

- [ ] **Step 1: Write style constants and imports**

Write to `wavealigner/plotting.py`:

```python
from __future__ import annotations

import os

import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

TRIAL_COLORS = ["#4878cf", "#e8855a", "#6aa453", "#9b59b6", "#e74c3c", "#1abc9c"]
MEAN_COLOR = "black"
BAND_COLOR = "#cccccc"
TABLE_WIDTH_FRACTION = 0.22
```

- [ ] **Step 2: Write `build_table_ax()`**

Copy the `build_table_ax()` function from `plot_trials_threshold.py` (lines 207-246):

```python
def build_table_ax(fig, gs_table, trial_labels, rmse_vals, nrmse_vals,
                   mean_rmse, mean_nrmse):
    ax_t = fig.add_subplot(gs_table)
    ax_t.set_axis_off()

    n_trials = len(trial_labels)
    col_labels = ["Trial", "RMSE\n(cm)", "NRMSE\n(%)"]
    col_widths = [0.40, 0.30, 0.30]

    cell_text, cell_colors = [], []
    for i, lbl in enumerate(trial_labels):
        cell_text.append([lbl, f"{rmse_vals[i]:.4f}" if rmse_vals else "—",
                          f"{nrmse_vals[i]:.2f}" if nrmse_vals else "—"])
        cell_colors.append(["white", "white", "white"])
    cell_text.append(["Mean \u03c3",
                      f"{mean_rmse:.4f}" if mean_rmse is not None else "—",
                      f"{mean_nrmse:.2f}" if mean_nrmse is not None else "—"])
    cell_colors.append(["#f5f5f5", "#f5f5f5", "#f5f5f5"])

    tbl = ax_t.table(
        cellText=cell_text,
        colLabels=col_labels,
        colWidths=col_widths,
        cellColours=cell_colors,
        loc="upper center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)

    sep_row = n_trials + 1
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#aaaaaa")
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_text_props(fontweight="bold")
            cell.set_facecolor("#e8e8e8")
            cell.set_edgecolor("#888888")
        if r == sep_row:
            cell.set_edgecolor("#555555")

    tbl.scale(1, 1.4)
    return ax_t
```

- [ ] **Step 3: Write `build_figure()`**

Append to `wavealigner/plotting.py`:

```python
def build_figure(
    t_common: np.ndarray,
    interp_signals: list[np.ndarray],
    t_arrays: list[np.ndarray],
    y_arrays: list[np.ndarray],
    trial_labels: list[str],
    mean_y: np.ndarray | None,
    std_y: np.ndarray | None,
    rmse_vals: list[float],
    nrmse_vals: list[float],
    mean_rmse: float | None,
    mean_nrmse: float | None,
    title: str = "Wave Aligner",
    x_label: str = "Time (s)",
) -> Figure:
    fig = plt.figure(figsize=(14, 6), facecolor="white")
    gs = gridspec.GridSpec(
        1, 2,
        width_ratios=[1.0 - TABLE_WIDTH_FRACTION, TABLE_WIDTH_FRACTION],
        wspace=0.03,
        left=0.07, right=0.98, top=0.91, bottom=0.12,
    )
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor("white")

    ax.grid(True, linestyle="--", linewidth=0.6, color="#cccccc", alpha=0.8, zorder=0)
    ax.set_axisbelow(True)

    # Mean ± 1σ band
    if mean_y is not None and std_y is not None:
        ax.fill_between(t_common, mean_y - std_y, mean_y + std_y,
                        color=BAND_COLOR, alpha=0.6, zorder=1)

    # Full-data step plots for each trial
    for i, (t, y) in enumerate(zip(t_arrays, y_arrays)):
        ax.step(t, y, where="post",
                color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                linewidth=1.2, zorder=2 + i)

    # Mean line
    if mean_y is not None:
        ax.plot(t_common, mean_y,
                color=MEAN_COLOR, linewidth=1.8, linestyle="--",
                dashes=(6, 3), zorder=10)

    # Labels
    ax.set_title(title, fontsize=13, pad=10)
    ax.set_xlabel(x_label, fontsize=11)
    ax.set_ylabel("Water Elevation (cm)", fontsize=11)
    ax.tick_params(labelsize=10)

    # Legend
    band_patch = mpatches.Patch(facecolor=BAND_COLOR, edgecolor="none", label="Mean \u00b1 1\u03c3")
    trial_lines = [
        Line2D([0], [0], color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
               linewidth=1.4, label=trial_labels[i])
        for i in range(len(t_arrays))
    ]
    mean_line = Line2D([0], [0], color=MEAN_COLOR, linewidth=1.8,
                       linestyle="--", dashes=(6, 3), label="Mean")
    ax.legend(handles=[band_patch] + trial_lines + [mean_line],
              loc="upper left", fontsize=9, framealpha=0.9,
              edgecolor="#aaaaaa", fancybox=False)

    # RMSE table
    build_table_ax(fig, gs[1], trial_labels,
                   rmse_vals, nrmse_vals, mean_rmse, mean_nrmse)

    # Auto-expand x-axis to show all shifted data
    all_t = np.concatenate(t_arrays) if t_arrays else np.array([0, 1])
    x_pad = (all_t.max() - all_t.min()) * 0.02 or 0.5
    ax.set_xlim(all_t.min() - x_pad, all_t.max() + x_pad)

    return fig
```

---

### Task 5: Write `app.py` — Main window with embedded matplotlib

**Files:**
- Create: `wavealigner/app.py`

This is the largest task. The main window contains:
- Menu bar (File > Load CSV, File > Export Graph, File > Quit)
- Left: matplotlib canvas with NavigationToolbar2QT
- Right: scrollable trial control panel
- Live-updating statistics summary

- [ ] **Step 1: Write the imports and class skeleton**

Write to `wavealigner/app.py`:

```python
from __future__ import annotations

from functools import partial

import numpy as np

import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
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

        toolbar = NavigationToolbar2QT(self._canvas, left)
        left_layout.addWidget(toolbar)

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
        self._rmse_label = QLabel("RMSE: —")
        self._nrmse_label = QLabel("NRMSE: —")
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

        self._status = QStatusBar()
        self.setStatusBar(self._status)
```

- [ ] **Step 2: Write menu builder**

Append to `wavealigner/app.py` (before the existing methods):

```python
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
```

- [ ] **Step 3: Write `_on_load_csv()`**

Append to `wavealigner/app.py`:

```python
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
```

- [ ] **Step 4: Write `_add_trial_controls()`**

Append to `wavealigner/app.py`:

```python
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
        name_label = QLabel(f'<span style="color:{color}">●</span> {trial.label}')
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
```

- [ ] **Step 5: Write all signal handlers**

Append to `wavealigner/app.py`:

```python
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
```

- [ ] **Step 6: Write `_update_plot()` — the core redraw method**

Append to `wavealigner/app.py`:

```python
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

        # Build figure
        self._fig = build_figure(
            t_common=t_common,
            interp_signals=interp_signals,
            t_arrays=t_arrays,
            y_arrays=y_arrays,
            trial_labels=trial_labels,
            mean_y=stats["mean_y"],
            std_y=stats["std_y"],
            rmse_vals=stats["rmse_vals"],
            nrmse_vals=stats["nrmse_vals"],
            mean_rmse=stats["mean_rmse"],
            mean_nrmse=stats["mean_nrmse"],
        )

        # Replace canvas content
        self._canvas.figure = self._fig
        self._canvas.draw()

        # Update sidebar summary
        if stats["mean_rmse"] is not None:
            self._rmse_label.setText(f"RMSE: {stats['mean_rmse']:.4f} cm")
            self._nrmse_label.setText(f"NRMSE: {stats['mean_nrmse']:.2f}%")
        else:
            self._rmse_label.setText("RMSE: — (need ≥2 visible trials)")
            self._nrmse_label.setText("NRMSE: —")
```

---

### Task 6: Write `run_wavealigner.py` — entry point

**Files:**
- Create: `run_wavealigner.py`

- [ ] **Step 1: Write the entry point**

Write to `run_wavealigner.py`:

```python
#!/usr/bin/env python3
"""Launch the Wave Aligner GUI."""

import sys

from PyQt5.QtWidgets import QApplication

from wavealigner.app import WaveAlignerWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Wave Aligner")
    window = WaveAlignerWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the app launches**

Run: `python run_wavealigner.py`

Expected: A window titled "Wave Aligner" appears with an empty plot and trial controls panel. (Close it manually.)

---

### Task 7: Compare output against `plot_trials_threshold.py`

**Files:**
- Test: Any available trial CSV files (from the dataset folders used by the original skill)

- [ ] **Step 1: Find sample CSV data**

Search for sample CSV files from the original workflow:

```bash
Get-ChildItem -Recurse -Filter "PhaseII_TestD_*.csv" | Select-Object -First 3 -ExpandProperty FullName
```

If none exist in the repo, note that the user needs to provide CSV files for verification.

- [ ] **Step 2: Generate reference plot**

Generate a reference plot using the original script with —no-align:

```bash
python .opencode/skills/plot-trials-threshold/scripts/plot_trials_threshold.py csv1.csv csv2.csv --output reference.png --no-align
```

Expected: `reference.png` saved with the standard 14×6 layout.

- [ ] **Step 3: Load same CSVs in the GUI and export**

Open the GUI, load the same CSVs, export the graph to `gui_output.png`.

Expected: The exported graph should visually match `reference.png`:
- Same grid style (`--`, `#cccccc`, 0.6pt)
- Same step line colors (TRIAL_COLORS cycling)
- Same mean ± 1σ band (`#cccccc`, alpha=0.6)
- Same mean line (black dashed (6,3), 1.8pt)
- Same legend position and font
- Same table layout and formatting

- [ ] **Step 4: Document any discrepancies**

If differences exist, note them and adjust `plotting.py` to match exactly.

---

### Task 8: Verify display-all-data invariant

**Files:**
- Test: Create a synthetic CSV with different lengths

- [ ] **Step 1: Create test CSVs with different lengths**

Create `_test_data/trial01.csv` (50 rows) and `_test_data/trial02.csv` (100 rows) via Python:

```python
import numpy as np; import pandas as pd
t1 = np.linspace(0, 1, 50)
t2 = np.linspace(0, 2, 100)
y1 = np.sin(2 * np.pi * t1)
y2 = np.sin(2 * np.pi * t2)
pd.DataFrame({"t (s)": t1, "correct y": y1}).to_csv("_test_data/trial01.csv", index=False)
pd.DataFrame({"t (s)": t2, "correct y": y2}).to_csv("_test_data/trial02.csv", index=False)
```

Run this via: `python -c "import numpy as np; import pandas as pd; ..."`

- [ ] **Step 2: Load both in GUI and verify**

Load both CSVs. Check that:
- trial01 shows all 50 samples (shorter trace ends earlier)
- trial02 shows all 100 samples (longer trace extends beyond trial01)
- x-axis auto-expands to show both fully
- Mean band only covers the overlap region (t=0 to t=1)

- [ ] **Step 3: Shift and verify no clipping**

Slide trial01 +0.5s to the right. Verify:
- trial01 shifts right but all 50 samples still visible
- x-axis expands to accommodate
- Mean band shifts to new overlap region

- [ ] **Step 4: Clean up**

```bash
Remove-Item -Recurse -Force _test_data
```

---

### Task 9: Verify live statistics update

**Files:**
- Manual test in GUI

- [ ] **Step 1: Load 3+ CSV files and note initial RMSE/NRMSE**

When loaded with zero shifts, both the graph table and sidebar summary should show identical values.

- [ ] **Step 2: Shift one trial by +0.1s**

Verify:
- RMSE/NRMSE values change on the graph table
- Sidebar RMSE/NRMSE labels match the graph table's "Mean σ" row
- Both update within one frame of releasing the slider

- [ ] **Step 3: Hide a trial**

Uncheck the visibility checkbox. Verify:
- Mean and stats recompute without the hidden trial
- RMSE values change
- Hidden trial's line disappears from plot

- [ ] **Step 4: Re-check the trial**

Verify mean and stats return to include it.

---

### Task 10: Final walkthrough and polishing

**Files:** (all project files)

- [ ] **Step 1: Verify all GUI features work**

Checklist:
- [ ] Load CSV (multi-select) — loads and shows trials
- [ ] Remove trial — removes from list and plot
- [ ] Show/hide individual trials — visibility toggle works
- [ ] Slider shift — shifts corresponding trial
- [ ] Spinbox shift — same as slider
- [ ] Reset Trial — sets shift to 0
- [ ] Reset All — all shifts to 0, all visible
- [ ] Export Graph — saves PNG matching displayed graph
- [ ] RMSE table on graph — matches sidebar
- [ ] NRMSE table on graph — matches sidebar
- [ ] Mean band — only on overlap region
- [ ] Full data display — no clipping
- [ ] x-axis auto-expands after shifts

- [ ] **Step 2: Check error handling**

Test:
- Load a non-CSV file → should show warning
- Load CSV with missing columns → should show warning
- Load 1 trial only → mean disabled, stats show "—"

- [ ] **Step 3: Announce completion**

Print: "Wave Aligner GUI implementation complete. Run with `python run_wavealigner.py`. Compare output against `plot_trials_threshold.py` by loading the same CSV files with —no-align and exporting the GUI graph."
