---
name: plot-trials-threshold
description: >
  Batch-runs plot_trials.py across multiple folders of trial CSV files, producing
  one aligned PNG per folder. Use this skill whenever the user wants to process
  multiple folders of wave/hydraulic trial CSVs at once, mentions "batch graphing",
  "all my folders", "one shot all data", or describes a folder-of-CSVs → PNG workflow.
  Each folder becomes one output PNG named FOLDERNAME_trials_aligned.png.
  Trigger even if the user just says "graph all my data" or "run it on all folders".
---

# Batch Plot Trials Skill

Automates running `plot_trials.py` across one or more folders, each containing
trial CSV files. Outputs one PNG per folder, named `<folder_name>_trials_aligned.png`.

## Expected layout

```
PhaseII_TestD_0001_c4/
    PhaseII_TestD_0001_c4_01.csv
    PhaseII_TestD_0001_c4_02.csv
    PhaseII_TestD_0001_c4_03.csv

PhaseII_TestD_0002_c4/
    PhaseII_TestD_0002_c4_01.csv
    PhaseII_TestD_0002_c4_02.csv
```

CSV headers required: `frame`, `t (s)`, `x (cm)`, `y (cm)`, `correct y`
(or `correc y` — the typo is handled automatically by plot_trials.py).

Trials are automatically aligned to Trial 1 using cross-correlation (shifts each
signal to best match the first trial). Use `--no-align` to disable alignment.

## Workflow

**Step 1 — Locate scripts**

Both `batch_plot.py` and `plot_trials.py` live in this skill's `scripts/` folder.
Run them directly from there — no copying needed.

**Step 2 — Discover folders**

The batch runner:
- Accepts one or more folder paths as arguments (or `--parent` for all subfolders)
- Finds all `.csv` files inside each folder
- Skips folders with fewer than 2 CSV files (warns the user)
- Runs `plot_trials.py` with all CSVs in the folder
- Names the output `<folder_name>_trials_aligned.png` next to each folder — unless `--output-dir` is set

**Step 3 — Run**

Run `batch_plot.py` directly from the skill's `scripts/` directory. Always show
the user the command being run and summarise results.

## Using the batch runner

```powershell
# Process ALL subfolders of a parent directory (most common):
python .opencode\skills\batch-plot-trials\scripts\batch_plot.py --parent "path\to\data"

# Process specific folders:
python .opencode\skills\batch-plot-trials\scripts\batch_plot.py path\to\PhaseII_TestD_0001_c4 path\to\PhaseII_TestD_0002_c4

# Custom output directory for PNGs:
python .opencode\skills\batch-plot-trials\scripts\batch_plot.py --parent path\to\data --output-dir path\to\plots

# Skip cross-correlation alignment:
python .opencode\skills\batch-plot-trials\scripts\batch_plot.py --parent path\to\data --no-align
```

## What to tell the user

After running, report:
- ✅ Succeeded: list of folders + output filenames
- ⚠️  Skipped: folders with <2 CSVs
- ❌ Failed: folders with errors + the error message

If any folder fails, suggest checking that `plot_trials.py` is in the same
directory and that the CSVs have the correct headers.