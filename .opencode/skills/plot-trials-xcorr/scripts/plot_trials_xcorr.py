"""
plot_trials_correlation.py

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


# ── cross-correlation alignment ──────────────────────────────────────────────
def compute_optimal_lag(signal: np.ndarray, reference: np.ndarray,
                        max_lag: int) -> int:
    """Find lag (in samples) that best aligns *signal* to *reference*.

    Positive lag means *signal* starts after *reference* (shift signal left).
    Negative lag means *signal* starts before *reference* (shift signal right).
    """
    sig_norm = signal - signal.mean()
    ref_norm = reference - reference.mean()
    denom = np.sqrt(np.sum(sig_norm ** 2) * np.sum(ref_norm ** 2))
    if denom == 0:
        return 0

    corr = np.correlate(sig_norm, ref_norm, mode="full")
    corr_norm = corr / denom

    center = len(ref_norm) - 1          # zero-lag index
    start  = max(0, center - max_lag)
    end    = min(len(corr), center + max_lag + 1)

    peak_idx = int(np.argmax(corr_norm[start:end])) + start
    return peak_idx - center


def apply_lag(signal: np.ndarray, lag: int, fill: float = np.nan) -> np.ndarray:
    """Shift *signal* by *lag* samples, filling vacated positions with *fill*."""
    if lag == 0:
        return signal.copy()
    n = len(signal)
    shifted = np.full(n, fill)
    if lag > 0:          # signal starts late → trim front, pad end
        shifted[:n - lag] = signal[lag:]
    else:                # signal starts early → pad front, trim end
        shifted[-lag:] = signal[:n + lag]
    return shifted


def align_to_ref(signals: list[np.ndarray],
                 max_lag_ratio: float = 0.2) -> tuple[list[np.ndarray], list[int]]:
    """Align all signals to the first signal (Trial 1) using cross-correlation.

    Uses normalised cross-correlation to find the optimal lag for each
    signal relative to Trial 1 (index 0).  Trial 1 is kept as-is.
    """
    ref = signals[0]
    n_samples = len(ref)
    max_lag_samps = int(n_samples * max_lag_ratio)

    aligned: list[np.ndarray] = [ref.copy()]
    lags = [0]

    for sig in signals[1:]:
        lag = compute_optimal_lag(sig, ref, max_lag_samps)
        lags.append(lag)
        aligned.append(apply_lag(sig, lag))

    # Trim to region where every shifted signal has valid data
    stack = np.vstack(aligned)
    valid = ~np.any(np.isnan(stack), axis=0)
    if valid.sum() >= 3:
        aligned = [row[valid].copy() for row in aligned]

    return aligned, lags


def align_signals(signals: list[np.ndarray],
                  max_lag_ratio: float = 0.2,
                  max_iter: int = 10,
                  tol: float = 1e-6) -> tuple[list[np.ndarray], list[int], bool]:
    """Iteratively align a group of signals to their running mean.

    Uses normalised cross-correlation to find the optimal lag for each
    signal relative to the current mean of the group.  Repeats until
    no signal shifts by more than *tol* samples.

    Parameters
    ----------
    signals
        List of equal-length 1-D arrays.
    max_lag_ratio
        Maximum allowed lag as a fraction of signal length.
    max_iter
        Maximum alignment iterations.
    tol
        Convergence threshold (mean absolute lag change < tol).

    Returns
    -------
    aligned
        Shifted copies (shorter if trimming occurred).
    final_lags
        Lag applied to each input signal.
    converged
        Whether iterative process converged.
    """
    n = len(signals)
    n_samples = len(signals[0])
    max_lag_samps = int(n_samples * max_lag_ratio)

    # Initial common-validity mask (all rows have data).
    stack = np.vstack(signals)
    valid = ~np.any(np.isnan(stack), axis=0)
    if valid.sum() < 3:
        valid = np.ones(n_samples, dtype=bool)
    stack = stack[:, valid]

    cumulative_lags = np.zeros(n, dtype=int)
    prev_delta_lags = np.zeros(n, dtype=int)
    converged = False

    for _it in range(max_iter):
        mean_ref = np.mean(stack, axis=0)

        new_delta_lags = np.zeros(n, dtype=int)
        new_rows = np.empty((n, stack.shape[1]))

        for i in range(n):
            lag = compute_optimal_lag(stack[i], mean_ref, max_lag_samps)
            new_delta_lags[i] = lag
            new_rows[i] = apply_lag(stack[i], lag)

        max_drift = np.mean(np.abs(new_delta_lags - prev_delta_lags))

        # Accumulate to cumulative lag
        cumulative_lags += new_delta_lags

        # Trim NaN introduced by shifting, then iterate
        valid = ~np.any(np.isnan(new_rows), axis=0)
        if valid.sum() < 3:
            break
        stack = new_rows[:, valid]
        prev_delta_lags = new_delta_lags

        if max_drift < tol:
            converged = True
            break

    aligned = [row.copy() for row in stack]
    return aligned, cumulative_lags.tolist(), converged


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


def plot_trials(csv_paths: list[str], output_path: str,
                align: bool = True, align_mode: str = "ref") -> None:
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

    # ── optional cross-correlation alignment ─────────────────────────────────
    if align and n >= 2:
        if align_mode == "ref":
            aligned, lags = align_to_ref(interp_signals)
            if any(l != 0 for l in lags):
                lag_str = ", ".join(f"Trial {i+1}: {l} samp" for i, l in enumerate(lags))
                print(f"  [i] Align-to-ref lags: {lag_str}")
        else:
            aligned, lags, converged = align_signals(interp_signals)
            if not converged:
                print("  [!] Iterative mean alignment did not fully converge.")
            if any(l != 0 for l in lags):
                lag_str = ", ".join(f"Trial {i+1}: {l} samp" for i, l in enumerate(lags))
                print(f"  [i] Iterative-mean lags: {lag_str}")

        # Trim t_common to match the trimmed signals (shorter after alignment)
        if len(aligned[0]) < len(t_common):
            t_common = t_common[:len(aligned[0])]
        interp_signals = aligned

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
        description="Plot aligned wave-height trials with mean ± 1σ and RMSE table.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Alignment modes:\n"
            "  ref   (default)  Align each trial to Trial 1 via cross-correlation.\n"
            "  mean             Iteratively align all trials to the group mean.\n"
        ),
    )
    parser.add_argument("csvs", nargs="+",
                        help="One or more CSV files (tab or comma separated).")
    parser.add_argument("--output", "-o", default="trials_aligned.png",
                        help="Output PNG path (default: trials_aligned.png).")
    parser.add_argument("--no-align", action="store_true",
                        help="Skip cross-correlation alignment (raw overlay).")
    parser.add_argument("--align-mode", choices=["ref", "mean"], default="ref",
                        help="Alignment algorithm (default: ref).")
    args = parser.parse_args()

    missing = [p for p in args.csvs if not os.path.isfile(p)]
    if missing:
        print(f"ERROR: file(s) not found: {missing}", file=sys.stderr)
        sys.exit(1)

    plot_trials(args.csvs, args.output,
                align=not args.no_align, align_mode=args.align_mode)


if __name__ == "__main__":
    main()