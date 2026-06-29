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


def build_table_ax(fig, gs_table, trial_labels, rmse_vals, nrmse_vals,
                   mean_rmse, mean_nrmse):
    ax_t = fig.add_subplot(gs_table)
    ax_t.set_axis_off()

    n_trials = len(trial_labels)
    col_labels = ["Trial", "RMSE\n(cm)", "NRMSE\n(%)"]
    col_widths = [0.40, 0.30, 0.30]

    cell_text, cell_colors = [], []
    for i, lbl in enumerate(trial_labels):
        rmse_str = f"{rmse_vals[i]:.4f}" if i < len(rmse_vals) and rmse_vals[i] is not None else "\u2014"
        nrmse_str = f"{nrmse_vals[i]:.2f}" if i < len(nrmse_vals) and nrmse_vals[i] is not None else "\u2014"
        cell_text.append([lbl, rmse_str, nrmse_str])
        cell_colors.append(["white", "white", "white"])
    cell_text.append(["Mean \u03c3",
                      f"{mean_rmse:.4f}" if mean_rmse is not None else "\u2014",
                      f"{mean_nrmse:.2f}" if mean_nrmse is not None else "\u2014"])
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
