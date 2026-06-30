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
