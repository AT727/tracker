from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from wavealigner.stats import compute_trial_stats


@dataclass
class Trial:
    path: str
    label: str
    df: pd.DataFrame
    shift_s: float = 0.0
    visible: bool = True

    def __hash__(self) -> int:
        return id(self)


CSV_REQUIRED_Y_COLUMNS = {"correct y"}
CSV_TIME_COLUMNS = {"t", "t (s)"}


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = df.columns.str.strip()

    # Normalize time column to "t (s)"
    time_col = next((c for c in CSV_TIME_COLUMNS if c in df.columns), None)
    if time_col and time_col != "t (s)":
        df = df.rename(columns={time_col: "t (s)"})

    # Normalize y column to "correct y"
    rename_y = {col: "correct y" for col in df.columns if col.lower().startswith("correc")}
    if rename_y:
        df = df.rename(columns=rename_y)
    elif "y (cm)" in df.columns:
        df = df.rename(columns={"y (cm)": "correct y"})

    missing = set()
    if "t (s)" not in df.columns:
        missing.add("time column 't (s)' (or 't')")
    missing.update(CSV_REQUIRED_Y_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(
            f"{path}: missing required columns.\n"
            f"  Expected: 't (s)' (or 't') and one of 'correct y', 'correc y', 'y (cm)'\n"
            f"  Found: {list(df.columns)}"
        )
    return df[["t (s)", "correct y"]].dropna().reset_index(drop=True)


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

    def remove_all(self) -> None:
        self.trials.clear()

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
        if not trials:
            return 0.0, 1.0, np.array([0.0, 1.0])
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

    def summary_data(self, visible_only: bool = True) -> dict:
        trials = self.visible_trials if visible_only else self.trials
        if len(trials) < 2:
            return {}
        _, _, t_common = self.overlap_region(visible_only)
        interp_signals = [
            np.interp(t_common, t.df["t (s)"].values - t.shift_s, t.df["correct y"].values)
            for t in trials
        ]
        stats = compute_trial_stats(interp_signals)
        return {
            "t_common": t_common,
            "mean_y": stats["mean_y"],
            "std_y": stats["std_y"],
            "rmse_vals": stats["rmse_vals"],
            "nrmse_vals": stats["nrmse_vals"],
            "mean_rmse": stats["mean_rmse"],
            "mean_nrmse": stats["mean_nrmse"],
            "trial_labels": [t.label for t in trials],
            "shifts": [t.shift_s for t in trials],
        }

    def export_shifted_csvs(self, output_dir: str) -> list[str]:
        exported = []
        for trial in self.trials:
            df = trial.df.copy()
            df["t (s)"] = df["t (s)"] - trial.shift_s
            eps = 1e-12
            df.loc[abs(df["t (s)"]) < eps, "t (s)"] = 0.0
            df = df[df["t (s)"] >= 0].reset_index(drop=True)
            stem = os.path.splitext(os.path.basename(trial.path))[0]
            out = os.path.join(output_dir, f"{stem}_timeshift.csv")
            df.to_csv(out, index=False)
            exported.append(out)
        return exported
