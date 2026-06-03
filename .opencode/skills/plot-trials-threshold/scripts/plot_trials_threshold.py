"""
plot_trials_threshold.py

Usage:
    python plot_trials.py trial01.csv trial02.csv trial03.csv --output my_plot.png

    # Threshold alignment (recommended for gradual-rise signals)
    python plot_trials.py *.csv --output out.png --align-mode threshold
    python plot_trials.py *.csv --output out.png --align-mode threshold --threshold 0.4

    # First-peak alignment (for signals with a clear sharp crest)
    python plot_trials.py *.csv --output out.png --align-mode peak
    python plot_trials.py *.csv --output out.png --align-mode peak --prominence 0.5 --height 0.05

    # No alignment (raw timestamps)
    python plot_trials.py *.csv --output out.png --no-align

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
from scipy.signal import find_peaks

# ── colour palette ────────────────────────────────────────────────────────────
TRIAL_COLORS = ["#4878cf", "#e8855a", "#6aa453", "#9b59b6", "#e74c3c", "#1abc9c"]
MEAN_COLOR   = "black"
BAND_COLOR   = "#cccccc"

TABLE_WIDTH_FRACTION = 0.22

# How many samples at the start of the signal to use for baseline estimation
BASELINE_SAMPLES = 50


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = df.columns.str.strip()

    # accept both "correct y" and "correc y" (common typo in source CSVs)
    rename = {col: "correct y" for col in df.columns if col.lower().startswith("correc")}
    if rename:
        df = df.rename(columns=rename)

    required = {"t (s)", "correct y"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {missing}. Found: {list(df.columns)}")
    return df[["t (s)", "correct y"]].dropna().reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Alignment: threshold (rising edge)
# ─────────────────────────────────────────────────────────────────────────────

def find_threshold_crossing(
    y: np.ndarray,
    threshold_frac: float,
    baseline_samples: int = BASELINE_SAMPLES,
) -> int:
    """
    Return the index where y first crosses:
        baseline + threshold_frac * (max - baseline)

    threshold_frac=0.4 means "40% of the way up from still water to peak".
    Falls back to argmax if signal never crosses.
    """
    baseline  = y[:baseline_samples].mean()
    peak_val  = y.max()
    threshold = baseline + threshold_frac * (peak_val - baseline)

    crossings = np.where(y > threshold)[0]
    if len(crossings) == 0:
        print(f"  [!] No threshold crossing found — falling back to argmax.")
        return int(np.argmax(y))

    return int(crossings[0])


def align_to_threshold(
    trials: list[pd.DataFrame],
    threshold_frac: float,
) -> tuple[list[np.ndarray], list[np.ndarray], list[int]]:
    """
    Shift each trial so its rising-edge threshold crossing lands at t=0.
    Returns (t_arrays, y_arrays, crossing_indices).
    """
    t_arrays, y_arrays, cross_idxs = [], [], []

    for df in trials:
        t = df["t (s)"].values.copy()
        y = df["correct y"].values.copy()

        idx = find_threshold_crossing(y, threshold_frac)
        cross_idxs.append(idx)
        t_arrays.append(t - t[idx])
        y_arrays.append(y)

    return t_arrays, y_arrays, cross_idxs


# ─────────────────────────────────────────────────────────────────────────────
# Alignment: first prominent peak
# ─────────────────────────────────────────────────────────────────────────────

def find_first_prominent_peak(
    y: np.ndarray,
    prominence: float,
    distance: int,
    height: float | None,
) -> int:
    kwargs: dict = dict(prominence=prominence, distance=distance)
    if height is not None:
        kwargs["height"] = height

    peaks, _ = find_peaks(y, **kwargs)

    if len(peaks) == 0:
        print(f"  [!] No peak found with given filters — falling back to argmax.")
        return int(np.argmax(y))

    return int(peaks[0])


def align_to_first_peak(
    trials: list[pd.DataFrame],
    prominence: float,
    distance: int,
    height: float | None,
) -> tuple[list[np.ndarray], list[np.ndarray], list[int]]:
    """
    Shift each trial so its first prominent peak lands at t=0.
    Returns (t_arrays, y_arrays, peak_indices).
    """
    t_arrays, y_arrays, peak_idxs = [], [], []

    for df in trials:
        t = df["t (s)"].values.copy()
        y = df["correct y"].values.copy()

        idx = find_first_prominent_peak(y, prominence, distance, height)
        peak_idxs.append(idx)
        t_arrays.append(t - t[idx])
        y_arrays.append(y)

    return t_arrays, y_arrays, peak_idxs


# ─────────────────────────────────────────────────────────────────────────────
# Common grid builder (shared by both alignment methods)
# ─────────────────────────────────────────────────────────────────────────────

def build_common_grid(
    t_arrays: list[np.ndarray],
    y_arrays: list[np.ndarray],
    n_pts: int,
) -> tuple[np.ndarray, list[np.ndarray]]:
    t_min    = max(t.min() for t in t_arrays)
    t_max    = min(t.max() for t in t_arrays)
    t_common = np.linspace(t_min, t_max, n_pts)

    interp_signals = [
        np.interp(t_common, t, y)
        for t, y in zip(t_arrays, y_arrays)
    ]
    return t_common, interp_signals


# ─────────────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────────────

def compute_rmse(signal: np.ndarray, reference: np.ndarray) -> float:
    min_len = min(len(signal), len(reference))
    diff = signal[:min_len] - reference[:min_len]
    return float(np.sqrt(np.mean(diff ** 2)))


# ─────────────────────────────────────────────────────────────────────────────
# Table
# ─────────────────────────────────────────────────────────────────────────────

def build_table_ax(fig, gs_table, trial_labels, rmse_vals, nrmse_vals,
                   mean_rmse, mean_nrmse):
    ax_t = fig.add_subplot(gs_table)
    ax_t.set_axis_off()

    n_trials   = len(trial_labels)
    col_labels = ["Trial", "RMSE\n(cm)", "NRMSE\n(%)"]
    col_widths = [0.40, 0.30, 0.30]

    cell_text, cell_colors = [], []
    for i, lbl in enumerate(trial_labels):
        cell_text.append([lbl, f"{rmse_vals[i]:.4f}", f"{nrmse_vals[i]:.2f}"])
        cell_colors.append(["white", "white", "white"])
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


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def plot_trials(
    csv_paths: list[str],
    output_path: str,
    align_mode: str = "threshold",   # "threshold" | "peak" | "none"
    threshold_frac: float = 0.4,
    prominence: float = 1.0,
    distance: int = 5,
    height: float | None = None,
) -> None:

    trials       = [load_csv(p) for p in csv_paths]
    n            = len(trials)
    trial_labels = [f"Trial {i+1:02d}" for i in range(n)]
    n_pts        = max(len(df) for df in trials)

    # ── alignment ─────────────────────────────────────────────────────────────
    if align_mode == "threshold":
        t_arrays, y_arrays, ref_idxs = align_to_threshold(trials, threshold_frac)
        t_common, interp_signals = build_common_grid(t_arrays, y_arrays, n_pts)

        for i, (df, idx) in enumerate(zip(trials, ref_idxs)):
            t_cross = df["t (s)"].values[idx]
            y_cross = df["correct y"].values[idx]
            print(f"  {trial_labels[i]}: threshold crossing at "
                  f"t={t_cross:.3f}s, y={y_cross:.4f}cm  (shift={-t_cross:+.3f}s)")

        x_label   = f"Time relative to {threshold_frac*100:.0f}% rise (s)"
        show_vline = True

    elif align_mode == "peak":
        t_arrays, y_arrays, ref_idxs = align_to_first_peak(
            trials, prominence, distance, height)
        t_common, interp_signals = build_common_grid(t_arrays, y_arrays, n_pts)

        for i, (df, idx) in enumerate(zip(trials, ref_idxs)):
            t_peak = df["t (s)"].values[idx]
            y_peak = df["correct y"].values[idx]
            print(f"  {trial_labels[i]}: first peak at "
                  f"t={t_peak:.3f}s, y={y_peak:.4f}cm  (shift={-t_peak:+.3f}s)")

        x_label   = "Time relative to first peak (s)"
        show_vline = True

    else:  # none
        t_min    = max(df["t (s)"].min() for df in trials)
        t_max    = min(df["t (s)"].max() for df in trials)
        t_common = np.linspace(t_min, t_max, n_pts)
        interp_signals = [
            np.interp(t_common, df["t (s)"].values, df["correct y"].values)
            for df in trials
        ]
        x_label    = "Time (s)"
        show_vline = False

    # ── statistics ────────────────────────────────────────────────────────────
    stack      = np.vstack(interp_signals)
    mean_y     = stack.mean(axis=0)
    std_y      = stack.std(axis=0)
    y_range    = mean_y.max() - mean_y.min() or 1.0
    rmse_vals  = [compute_rmse(s, mean_y) for s in interp_signals]
    nrmse_vals = [r / y_range * 100 for r in rmse_vals]
    mean_rmse  = float(np.mean(rmse_vals))
    mean_nrmse = float(np.mean(nrmse_vals))

    # ── figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 6), facecolor="white")
    gs  = gridspec.GridSpec(
        1, 2,
        width_ratios=[1.0 - TABLE_WIDTH_FRACTION, TABLE_WIDTH_FRACTION],
        wspace=0.03,
        left=0.07, right=0.98, top=0.91, bottom=0.12,
    )
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor("white")

    ax.grid(True, linestyle="--", linewidth=0.6, color="#cccccc", alpha=0.8, zorder=0)
    ax.set_axisbelow(True)

    ax.fill_between(t_common, mean_y - std_y, mean_y + std_y,
                    color=BAND_COLOR, alpha=0.6, zorder=1)

    for i, sig in enumerate(interp_signals):
        ax.step(t_common, sig, where="post",
                color=TRIAL_COLORS[i % len(TRIAL_COLORS)],
                linewidth=1.2, zorder=2 + i)

    ax.plot(t_common, mean_y,
            color=MEAN_COLOR, linewidth=1.8, linestyle="--",
            dashes=(6, 3), zorder=10)

    if show_vline:
        ax.axvline(0, color="#888888", linewidth=0.8, linestyle=":", zorder=1)

    title = os.path.splitext(os.path.basename(output_path))[0]
    ax.set_title(title, fontsize=13, pad=10)
    ax.set_xlabel(x_label, fontsize=11)
    ax.set_ylabel("Water Elevation (cm)", fontsize=11)
    ax.tick_params(labelsize=10)

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

    build_table_ax(fig, gs[1], trial_labels,
                   rmse_vals, nrmse_vals, mean_rmse, mean_nrmse)

    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    print(f"Saved -> {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Plot aligned wave-height trials with mean ± 1σ and RMSE table.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Alignment modes:\n"
            "  threshold  (default) Align to when signal first crosses baseline + N%% of rise.\n"
            "                       Best for gradual-rise signals without a sharp crest.\n"
            "  peak                 Align to first prominent peak.\n"
            "                       Best for signals with a clear sharp wave crest.\n"
            "  none                 No alignment — plot raw timestamps.\n"
        ),
    )
    parser.add_argument("csvs", nargs="+", help="One or more CSV files.")
    parser.add_argument("--output", "-o", default="trials_aligned.png",
                        help="Output PNG path.")
    parser.add_argument(
        "--no-align", action="store_true",
        help="Skip alignment (equivalent to --align-mode none)."
    )
    parser.add_argument(
        "--align-mode", choices=["threshold", "peak", "none"], default="threshold",
        help="Alignment method (default: threshold)."
    )

    thr = parser.add_argument_group("threshold alignment options")
    thr.add_argument(
        "--threshold", type=float, default=0.4, metavar="FRAC",
        help="Fraction of the rise to use as the crossing threshold (default: 0.4 = 40%%). "
             "0.1 triggers earlier on the rising edge; 0.9 triggers near the peak."
    )

    pk = parser.add_argument_group("peak alignment options")
    pk.add_argument(
        "--prominence", type=float, default=1.0,
        help="Minimum peak prominence in cm (default: 1.0)."
    )
    pk.add_argument(
        "--distance", type=int, default=5,
        help="Minimum samples between peaks (default: 5)."
    )
    pk.add_argument(
        "--height", type=float, default=None,
        help="Minimum absolute peak height in cm (default: off)."
    )

    args = parser.parse_args()

    missing = [p for p in args.csvs if not os.path.isfile(p)]
    if missing:
        print(f"ERROR: file(s) not found: {missing}", file=sys.stderr)
        sys.exit(1)

    mode = "none" if args.no_align else args.align_mode

    plot_trials(
        args.csvs,
        args.output,
        align_mode=mode,
        threshold_frac=args.threshold,
        prominence=args.prominence,
        distance=args.distance,
        height=args.height,
    )


if __name__ == "__main__":
    main()