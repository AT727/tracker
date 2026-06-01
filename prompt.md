# CONTEXT
Civil engineering research tool for fluid-solid interaction studies. Source data: MP4 video recordings of wave tank experiments, captured at 128 fps. Current toolchain uses Tracker (Open Source Physics) — replacing it due to clunky UX and unreliable click handling at speed.

# OBJECTIVE
Build a desktop-grade video analysis application replicating and improving on Tracker's core workflow. Target user performs frame-by-frame point tracking on every frame of a video to extract positional data for research analysis. 

# REQUIRED FEATURES

## 1. Video Import & Frame Navigation
- Import MP4 files and decompose into individual frames
- Frame-by-frame navigation (prev/next, scrubber, jump-to-frame)
- Display current frame index and timestamp
- Frame rate aware (support 128 fps source material)

## 2. Calibration System
- Calibration stick: user clicks two endpoints on a known real-world length (tape measure visible in video) to establish pixel-to-unit scale
- Origin grid: user-defined coordinate origin and axis orientation overlay
- Persist calibrations to file — videos share the same camera setup, so recalibration per video must be optional, not required
- Toggle visibility of calibration stick and origin grid independently

## 3. Point Tracking & Data Collection
- Click-to-mark points on each frame; coordinates auto-converted to calibrated real-world units
- Stable zoom (zoom in/out without viewport drift or point skipping) — critical: current tool loses accuracy at high click speeds and high zoom
- Supports fast clicking workflows (autoclicker compatible); no dropped data points regardless of click rate
- Allow marking multiple tracked objects/entities per frame if needed

## 4. Data View Panel (right side, same layout as Tracker)
- Live-updating data table: frame, time, x, y (in calibrated units)
- Live plot: configurable axes (e.g., x vs t, y vs t, y vs x)

## 5. Export
- Export collected data to CSV
- Columns: frame index, timestamp (s), x (calibrated), y (calibrated)

## 6. Menu bar
- File with option to import video and export to csv

# CONSTRAINTS
- Must handle 128 fps video smoothly
- Zoom must be stable — no viewport shift on zoom or during rapid clicking
- Calibration data must be saveable/loadable between sessions
- UI layout: video canvas left, data panel right (mirror Tracker's split-pane layout)



