# CONTEXT
Civil engineering research tool for fluid-solid interaction studies. Source data: MP4 video recordings of wave tank experiments, captured at 128 fps. Current toolchain uses Tracker (Open Source Physics) — replacing it due to clunky UX and unreliable click handling at speed.

# OBJECTIVE
Build a desktop-grade video analysis application replicating and improving on Tracker's core workflow. Target user performs frame-by-frame point tracking on every frame of a video to extract positional data for research analysis. Python + PyQt5.

# REQUIRED FEATURES

## 1. Video Import & Frame Navigation
- Import MP4 files and decompose into individual frames via OpenCV (cv2)
- Buffer max 60 decoded frames in memory; load remaining frames on demand
- Frame-by-frame navigation (prev/next, scrubber, jump-to-frame)
- Display current frame index and timestamp
- Frame rate aware (support 128 fps source material)

## 2. Calibration System
- Calibration stick: user clicks two endpoints on a known real-world length (tape measure visible in video) to establish pixel-to-unit scale. Must support cm.
- Origin + axis: user sets an origin point (single click), positive-x direction = right. Y-axis is perpendicular and positive-y = up. No skew or rotation beyond this.
- Persist calibration to a `.json` sidecar file in the same directory as the video, using the same filename stem. On video open, auto-load the sidecar if present — recalibration per video is optional, not required.
- Toggle visibility of calibration stick and origin grid independently
- If no calibration is set, allow marking but display "(px)" as the unit and note "uncalibrated" in export

## 3. Point Tracking & Data Collection
- Click-to-mark points on each frame
- Data model: each tracked entity is a named "point series" with a label and color. Multiple series can be active simultaneously. The data table and CSV export include a `series` column.
- Store raw pixel coordinates internally. Apply calibration transform on display and export only — if calibration changes, all displayed values update automatically without re-marking.
- Zoom implementation: maintain explicit `(scale, pan_x, pan_y)` state. On scroll zoom, adjust pan offset so the pixel under the cursor stays fixed. Compute QTransform fresh from stored state each render — never use QTransform as persistent state.
- Click handling: process mouse clicks synchronously on the main thread without blocking on frame decode. If a frame decode is pending, record the click position and associate it with the current frame index immediately.
- Autoclicker compatible — no dropped data points regardless of click rate

## 4. Data View Panel (right side, same layout as Tracker)
- Live-updating data table: frame, time, series, x, y (in calibrated units or px if uncalibrated)
- Live plot: embed pyqtgraph. Configurable axes (x vs t, y vs t, y vs x). All active series shown simultaneously with matching colors.
- Toggle visibility of table and plot independently

## 5. Export
- Export collected data to CSV
- Columns: frame index, timestamp (s), series, x (calibrated), y (calibrated)

# TECHNICAL CONSTRAINTS
- Video decoding: OpenCV (cv2). Buffer max 60 decoded frames in memory; load on demand.
- Zoom: explicit `(scale, pan_x, pan_y)` state. Scroll zoom keeps pixel under cursor invariant. Recompute QTransform each render from stored state.
- Click handling: synchronous on main thread. Do not block on frame decode — record click immediately, associate to current frame index.
- Video decoding runs in a QThread worker.