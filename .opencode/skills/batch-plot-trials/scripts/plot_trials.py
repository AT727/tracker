"""
plot_trials.py

Usage:
    python plot_trials.py trial01.csv trial02.csv trial03.csv --output my_plot.png

Each CSV must have headers: frame  t (s)  x (cm)  y (cm)  correct y  (or correc y)
Plots "correct y" vs "t (s)" for each trial, with mean ± 1σ band and an RMSE table.

The output filename (without extension) is used as the plot title.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D

# ── colour palette ────────────────────────────────────────────────────────────
TRIAL_COLORS = ["#4878cf", "#e8855a", "#6aa453", "#9b59b6", "#e74c3c", "#1abc9c"]
MEAN_COLOR   = "black"
BAND_COLOR   = "#cccccc"

# How wide the table column is as a fraction of total figure width.
# Increase if you have many characters; decrease to give more room to the plot.
TABLE_WIDTH_FRACTION = 0.22


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = df.columns.str.strip()

    # accept both "correct y" and "correc y" (common typo in source CSVs)
    rename = {}
    for col in df.columns:
        if col.lower().startswith("correc"):
            rename[col] = "correct y"
    if rename:
        df = df.rename(columns=rename)

    required = {"t (s)", "correct y"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {missing}. Found: {list(df.columns)}")
    return df[["t (s)", "correct y"]].dropna()


def compute_rmse(signal: np.ndarray, reference: np.ndarray) -> float:
    min_len = min(len(signal), len(reference))
    diff = signal[:min_len] - reference[:min_len]
    return float(np.sqrt(np.mean(diff ** 2)))


def build_table_ax(fig, gs_table, trial_labels, rmse_vals, nrmse_vals,
                   mean_rmse, mean_nrmse):
    """Draw the RMSE table in its own dedicated axes column."""
    ax_t = fig.add_subplot(gs_table)
    ax_t.set_axis_off()

    n_trials = len(trial_labels)

    col_labels  = ["Trial", "RMSE\n(cm)", "NRMSE\n(%)"]
    col_widths  = [0.40, 0.30, 0.30]   # relative, must sum to 1

    # Build cell text & colours
    cell_text   = []
    cell_colors = []
    for i, lbl in enumerate(trial_labels):
        cell_text.append([lbl, f"{rmse_vals[i]:.4f}", f"{nrmse_vals[i]:.2f}"])
        cell_colors.append(["white", "white", "white"])
    # separator row (blank + light rule drawn via edge colour)
    cell_text.append(["Mean σ", f"{mean_rmse:.4f}", f"{mean_nrmse:.2f}"])
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

    # Style header row
    for j in range(len(col_labels)):
        cell = tbl[0, j]
        cell.set_text_props(fontweight="bold")
        cell.set_facecolor("#e8e8e8")
        cell.set_edgecolor("#888888")

    # Style separator before last data row (Mean σ)
    sep_row = n_trials + 1          # 0 = header, 1..n = trials, n+1 = mean σ
    for j in range(len(col_labels)):
        tbl[sep_row, j].set_edgecolor("#555555")

    # Uniform cell edges
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#aaaaaa")
        cell.set_linewidth(0.6)
        # Override header & separator edges
        if r == 0:
            cell.set_edgecolor("#888888")
        if r == sep_row:
            cell.set_edgecolor("#555555")

    # Scale rows to be a bit taller
    tbl.scale(1, 1.4)

    return ax_t


def plot_trials(csv_paths: list[str], output_path: str) -> None:
    # ── load ──────────────────────────────────────────────────────────────────
    trials: list[pd.DataFrame] = [load_csv(p) for p in csv_paths]
    n = len(trials)
    trial_labels = [f"Trial {i+1:02d}" for i in range(n)]

    # ── common time axis ──────────────────────────────────────────────────────
    t_min    = max(df["t (s)"].min() for df in trials)
    t_max    = min(df["t (s)"].max() for df in trials)
    n_pts    = max(len(df) for df in trials)
    t_common = np.linspace(t_min, t_max, n_pts)

    interp_signals = [
        np.interp(t_common, df["t (s)"].values, df["correct y"].values)
        for df in trials
    ]

    stack  = np.vstack(interp_signals)
    mean_y = stack.mean(axis=0)
    std_y  = stack.std(axis=0)

    # ── RMSE ──────────────────────────────────────────────────────────────────
    y_range    = mean_y.max() - mean_y.min() or 1.0
    rmse_vals  = [compute_rmse(s, mean_y) for s in interp_signals]
    nrmse_vals = [r / y_range * 100 for r in rmse_vals]
    mean_rmse  = float(np.mean(rmse_vals))
    mean_nrmse = float(np.mean(nrmse_vals))

    # ── layout: plot | table  (GridSpec) ──────────────────────────────────────
    # Table column is TABLE_WIDTH_FRACTION of figure width; plot gets the rest.
    plot_w  = 1.0 - TABLE_WIDTH_FRACTION
    fig_w   = 14          # total figure width in inches
    fig_h   = 6
    fig     = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    gs = gridspec.GridSpec(
        1, 2,
        width_ratios=[plot_w, TABLE_WIDTH_FRACTION],
        wspace=0.03,        # tiny gap between plot and table
        left=0.07, right=0.98, top=0.91, bottom=0.12
    )

    ax = fig.add_subplot(gs[0])
    ax.set_facecolor("white")

    # ── plot ──────────────────────────────────────────────────────────────────
    ax.grid(True, linestyle="--", linewidth=0.6, color="#cccccc", alpha=0.8, zorder=0)
    ax.set_axisbelow(True)

    ax.fill_between(t_common, mean_y - std_y, mean_y + std_y,
                    color=BAND_COLOR, alpha=0.6, zorder=1)

    for i, (sig, lbl) in enumerate(zip(interp_signals, trial_labels)):
        ax.step(t_common, sig, where="post",
                color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                linewidth=1.2, zorder=2 + i)

    ax.plot(t_common, mean_y,
            color=MEAN_COLOR, linewidth=1.8, linestyle="--",
            dashes=(6, 3), zorder=10)

    # ── labels ────────────────────────────────────────────────────────────────
    title = os.path.splitext(os.path.basename(output_path))[0]
    ax.set_title(title, fontsize=13, pad=10)
    ax.set_xlabel("Time (s)", fontsize=11)
    ax.set_ylabel("Water Elevation (cm)", fontsize=11)
    ax.tick_params(labelsize=10)

    # ── legend ────────────────────────────────────────────────────────────────
    band_patch = mpatches.Patch(facecolor=BAND_COLOR, edgecolor="none", label="Mean ± 1σ")
    trial_lines = [
        Line2D([0], [0], color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
               linewidth=1.4, label=trial_labels[i])
        for i in range(n)
    ]
    mean_line = Line2D([0], [0], color=MEAN_COLOR, linewidth=1.8,
                       linestyle="--", dashes=(6, 3), label="Mean")
    ax.legend(handles=[band_patch] + trial_lines + [mean_line],
              loc="upper left", fontsize=9, framealpha=0.9,
              edgecolor="#aaaaaa", fancybox=False)

    # ── table (right column) ──────────────────────────────────────────────────
    build_table_ax(fig, gs[1], trial_labels,
                   rmse_vals, nrmse_vals, mean_rmse, mean_nrmse)

    # ── save ──────────────────────────────────────────────────────────────────
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved -> {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Plot aligned wave-height trials with mean ± 1σ and RMSE table."
    )
    parser.add_argument("csvs", nargs="+",
                        help="One or more CSV files (tab or comma separated).")
    parser.add_argument("--output", "-o", default="trials_aligned.png",
                        help="Output PNG path (default: trials_aligned.png).")
    args = parser.parse_args()

    missing = [p for p in args.csvs if not os.path.isfile(p)]
    if missing:
        print(f"ERROR: file(s) not found: {missing}", file=sys.stderr)
        sys.exit(1)

    plot_trials(args.csvs, args.output)


if __name__ == "__main__":
    main()