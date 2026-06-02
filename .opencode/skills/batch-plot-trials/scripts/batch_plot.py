"""
batch_plot.py

Batch runner for plot_trials.py. Processes one or more folders of trial CSVs
and outputs one aligned PNG per folder.

Usage:
    # Specific folders
    python batch_plot.py PhaseII_TestD_0001_c4 PhaseII_TestD_0002_c4

    # All subfolders of a parent directory
    python batch_plot.py --parent ./data

    # Custom output directory for PNGs
    python batch_plot.py --parent ./data --output-dir ./plots

    # Specify a different location for plot_trials.py
    python batch_plot.py --parent ./data --script ../tools/plot_trials.py
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def find_csvs(folder: Path) -> list[Path]:
    """Return sorted list of .csv files directly inside folder (non-recursive)."""
    return sorted(folder.glob("*.csv"))


def process_folder(folder: Path, script: Path, output_dir: Path | None,
                   no_align: bool = False,
                   align_mode: str | None = None) -> tuple[bool, str]:
    """
    Run plot_trials.py on all CSVs in folder.
    Returns (success, message).
    """
    csvs = find_csvs(folder)

    if len(csvs) < 2:
        return False, f"Skipped — only {len(csvs)} CSV file(s) found (need ≥ 2)"

    # ── output name reflects alignment mode ──────────────────────────────────
    base_name = folder.name
    if no_align:
        mode_tag = "noalign"
    elif align_mode == "mean":
        mode_tag = "align_mean"
    else:
        mode_tag = "align_ref"

    output_name = f"{base_name}_trials_{mode_tag}.png"
    if output_dir:
        output_path = output_dir / output_name
    else:
        output_path = folder / output_name

    cmd = [
        sys.executable,
        str(script),
        *[str(c) for c in csvs],
        "--output", str(output_path),
    ]
    if no_align:
        cmd.append("--no-align")
    elif align_mode:
        cmd.extend(["--align-mode", align_mode])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(folder.parent),  # run from parent so relative paths work
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            return False, f"Error:\n{err}"
        return True, str(output_path)
    except Exception as e:
        return False, f"Exception: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Batch-run plot_trials.py across folders of trial CSVs."
    )
    parser.add_argument(
        "folders", nargs="*",
        help="One or more folder paths to process."
    )
    parser.add_argument(
        "--parent", "-p", type=Path, default=None,
        help="Process all immediate subfolders of this directory."
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=None,
        help="Directory to write output PNGs into (default: next to each folder)."
    )
    parser.add_argument(
        "--script", "-s", type=Path, default=None,
        help="Path to plot_trials.py (default: looks in same dir as batch_plot.py)."
    );
    parser.add_argument(
        "--no-align", action="store_true",
        help="Skip cross-correlation alignment (pass through to plot_trials.py)."
    );
    parser.add_argument(
        "--align-mode", choices=["ref", "mean"], default=None,
        help="Alignment algorithm (pass through to plot_trials.py)."
    );
    args = parser.parse_args()

    # ── locate plot_trials.py ─────────────────────────────────────────────────
    if args.script:
        script = args.script.resolve()
    else:
        script = Path(__file__).parent / "plot_trials.py"

    if not script.exists():
        print(f"ERROR: Cannot find plot_trials.py at {script}", file=sys.stderr)
        print("Use --script to specify its location.", file=sys.stderr)
        sys.exit(1)

    # ── collect folders ───────────────────────────────────────────────────────
    folders: list[Path] = []

    if args.parent:
        parent = args.parent.resolve()
        if not parent.is_dir():
            print(f"ERROR: --parent '{parent}' is not a directory.", file=sys.stderr)
            sys.exit(1)
        folders = sorted(p for p in parent.iterdir() if p.is_dir())
        if not folders:
            print(f"No subfolders found in '{parent}'.", file=sys.stderr)
            sys.exit(1)

    for f in args.folders:
        p = Path(f).resolve()
        if not p.is_dir():
            print(f"WARNING: '{f}' is not a directory — skipping.", file=sys.stderr)
        else:
            folders.append(p)

    if not folders:
        parser.print_help()
        sys.exit(1)

    # ── output dir ───────────────────────────────────────────────────────────
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    # ── process ───────────────────────────────────────────────────────────────
    successes, skipped, failures = [], [], []

    print(f"\nProcessing {len(folders)} folder(s) with {script.name}...\n")

    for folder in folders:
        print(f"  [{folder.name}] ", end="", flush=True)
        ok, msg = process_folder(folder, script, args.output_dir,
                                 no_align=args.no_align,
                                 align_mode=args.align_mode)
        if ok:
            print(f"[OK]  {msg}")
            successes.append((folder.name, msg))
        elif "Skipped" in msg:
            print(f"[SKIP] {msg}")
            skipped.append((folder.name, msg))
        else:
            print(f"[FAIL] {msg}")
            failures.append((folder.name, msg))

    # ── summary ───────────────────────────────────────────────────────────────
    print(f"\n{'-'*60}")
    print(f"  Succeeded : {len(successes)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Failed    : {len(failures)}")
    print(f"{'-'*60}\n")

    if failures:
        print("Failed folders:")
        for name, msg in failures:
            print(f"  {name}: {msg}")
        print()

    if skipped:
        print("Skipped folders (< 2 CSVs):")
        for name, msg in skipped:
            print(f"  {name}: {msg}")
        print()


if __name__ == "__main__":
    main()