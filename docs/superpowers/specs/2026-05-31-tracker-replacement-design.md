# Tracker Replacement: Video Analysis Desktop Application

## Overview

Desktop video analysis application for civil engineering fluid-solid interaction research. Replace Tracker (Open Source Physics) with a faster, more reliable PyQt5 app optimized for high-CPS frame-by-frame point tracking on 128 fps wave tank experiments.

## Architecture

### Tech Stack
- **Python 3.10+** with **PyQt5** for GUI
- **OpenCV** (`cv2.VideoCapture`) for on-demand frame decoding
- **QGraphicsView / QGraphicsScene** for the video canvas and overlay items
- **matplotlib** (`FigureCanvasQTAgg`) for live-plot panel
- **JSON** files for calibration persistence

### Module Layout

```
tracker/
├── main.py                   # QApplication entry point
├── window.py                 # QMainWindow, menu bar, splitter, status bar
├── video/
│   └── decoder.py            # OpenCV on-demand decoder + forward-only ring-buffer cache
├── canvas/
│   ├── view.py               # QGraphicsView subclass (stable zoom-about-cursor, pan)
│   ├── scene.py              # QGraphicsScene (layered overlay management)
│   └── items.py              # CalibrationStick, OriginGrid, TrackedPoint (QGraphicsItems)
├── calibration/
│   ├── controller.py         # Calibration workflow state machine
│   ├── data.py               # CalibrationData dataclass
│   └── persistence.py        # Save/load .calibration.json
├── coordinates/
│   ├── pipeline.py           # 5-step pixel→world transform (single source of truth)
│   └── transforms.py         # Scale, rotation, offset transform builders
├── tracking/
│   ├── collector.py          # TrackedPoint collection, append-only list
│   └── state.py              # App state (current frame, click mode, calibration status)
├── panels/
│   ├── data_table.py         # QTableWidget (frame, t, x, y)
│   └── plot_panel.py         # matplotlib FigureCanvas with configurable axes
├── export/
│   └── exporter.py           # CSV export of TrackedPoint list
└── widgets/
    └── frame_counter.py      # QGraphicsTextItem overlay (frame index + timestamp)
```

## Data Flow

### Click → Auto-Advance

```
[User clicks on canvas]
    → view.mousePressEvent: mapToScene(event.pos())
    → pipeline.coords_to_world(scene_x, scene_y)
    → collector.append(TrackedPoint{frame, timestamp, world_x, world_y, pixel_x, pixel_y})
    → emit point_recorded signal
    → frame_index += 1
    → decoder.get_frame(frame_index) → update scene background pixmap
    → status_bar update
    → IDLE (ready for next click)
```

Table and plot updates are deferred to the next event loop iteration so frame decode runs first:

```python
# In the slot connected to point_recorded:
QTimer.singleShot(0, data_table.update)
QTimer.singleShot(0, plot_panel.update)
```

## Stable Zoom

Zoom-about-cursor implemented via viewport translation, NOT `centerOn`:

```
In view.wheelEvent:
    old_pos = self.mapToScene(event.pos())
    factor = 1.15 or 1/1.15
    self.scale(factor, factor)
    new_pos = self.mapToScene(event.pos())
    delta = new_pos - old_pos
    self.translate(delta.x(), delta.y())
```

This cancels viewport drift by translating exactly the cursor's displacement after scaling.

## Frame Decoder & Cache

### On-Demand Extraction
- `cv2.VideoCapture` opened on video import
- Frame seek via `cv2.CAP_PROP_POS_FRAMES` (keyframe-based, acceptable for forward-only)
- Output: `cv2.mat` → `QImage` → `QPixmap` for scene background

### Forward-Only Ring Buffer
- Background thread pre-decodes N frames ahead of current position
- On frame advance: ring buffer provides instant frame (no decode latency). Frame advance is non-blocking; perceived latency is handled by the ring buffer pre-decode.
- Ring buffer size: configurable, default ~30 frames
- Backward seek: falls through to direct OpenCV seek + decode (accept latency for correction workflow)

`decoder.get_frame(frame_index)` returns `(QImage, timestamp_ms)` — timestamp from `cv2.CAP_PROP_POS_MSEC / 1000.0`, not computed as `frame / fps`.

## Coordinate Transform Pipeline

Single source of truth in `coordinates/pipeline.py`. Correct order (translate before scale):

```
1. scene_pos → video_pixel_pos — undo zoom + viewport offset (QGraphicsView.mapToScene yields scene coords; divide by current view scale, subtract viewport offset)
2. Subtract origin_px (translate origin to user-set position)
3. Apply scale factor (pixels → world units)
4. Apply rotation matrix (axis tilt correction)
→ Output: (x, y) in calibrated world units
```

Inverse transform (world → pixel) provided for rendering calibration grid and verification overlays.

## Calibration System

### Modes (toggle via toolbar/menu)

**Mode 1 — Calibration Stick:**
- Click endpoint A → red dot overlay
- Click endpoint B → red dot overlay + distance line
- Dialog: enter known real-world length (default 0.1 m)
- Scale factor = known_length / pixel_distance
- Rendered as labeled line overlay (toggle visibility)

**Mode 2 — Set Origin & Axis:**
- Click to place origin crosshair
- Numeric spinbox (degrees) to rotate axis orientation
- Grid overlay at calibrated unit spacing (toggle visibility)

### Persistence

Calibration saved as JSON alongside video file:
```
{video_basename}.calibration.json
```

```json
{
  "stick_endpoint_a_px": [120.5, 340.2],
  "stick_endpoint_b_px": [520.5, 340.2],
  "known_length": 0.1,
  "known_unit": "m",
  "origin_px": [320.0, 240.0],
  "axis_rotation_deg": 0.0,
  "video_frame0_hash": "a1b2c3d4e5f6..."
}
```

Identifier is a content hash (SHA-256) of frame 0's pixel data to match videos regardless of filename. Automatic lookup: hash first frame on video load → scan for `.calibration.json` files in same directory matching the hash. Falls back to filename-based matching if no hash match found.

- **Auto-load**: if `.calibration.json` exists next to video, load it
- **Override**: File → Load Calibration for manual selection
- **Recalibration optional**: share calibrations across videos from same camera setup

## Data Model

```python
@dataclass
class TrackedPoint:
    frame: int
    timestamp: float       # seconds from CAP_PROP_POS_MSEC / 1000.0
    x_world: float
    y_world: float
    x_pixel: float         # raw pixel coords (for verification/retroactive calibration)
    y_pixel: float
    track_id: str          # identifier for multi-object tracking; default "0" for single-point
    is_interpolated: bool = False  # True if point was gap-filled during retroactive calibration

# Stored as list[TrackedPoint] in tracking/collector.py
```

## UI Layout

### Main Window (QMainWindow)

```
┌──────────────────────────────────────────────────────────────┐
│ File                                              ─ □ × │
├──────────────────────────────────────┬───────────────────────┤
│                                      │  Data Panel           │
│  Video Canvas                        │  ┌───┬───┬───┬───┐   │
│  (QGraphicsView)                     │  │Frm│ T │ X │ Y │   │
│                                      │  ├───┼───┼───┼───┤   │
│  Frame counter overlay               │  │...│...│...│...│   │
│  (top-left, QGraphicsTextItem)       │  ├───┴───┴───┴───┤   │
│                                      │  │  Plot          │   │
│  128 fps  Frame 1247/20000           │  │  (matplotlib)  │   │
│  t = 9.74 s                          │  │                │   │
│                                      │  └────────────────┘   │
│  [Calibration Stick overlay]         │                       │
│  [Origin Grid overlay]               │                       │
│                                      │                       │
├──────────────────────────────────────┴───────────────────────┤
│ Status bar: click mode, calibration status, frame info       │
└──────────────────────────────────────────────────────────────┘
```

### Splitter
- `QSplitter` (horizontal), canvas left / panel right
- Default ratio: 70/30
- User-resizable

### Menu Bar
- File: Import Video (Ctrl+O), Export CSV (Ctrl+Shift+E), separator, Exit

### Canvas Toolbar
- Prev Frame (←) / Next Frame (→)
- Zoom In / Zoom Out / Fit to View
- Toggle Calibration Stick visibility
- Toggle Origin Grid visibility
- Calibration button (enters calibration mode, cursor changes)

### Right Panel
- **Tab 1: Table** — QTableWidget with columns Frame, Time (s), X (units), Y (units). Scrolls with new data; auto-scroll to latest on insert.
- **Tab 2: Plot** — matplotlib FigureCanvas with dropdowns for axis configuration (x vs t, y vs t, y vs x).

## Modes

```python
from enum import Enum

class AppMode(Enum):
    IDLE = "idle"                       # no video loaded
    CALIBRATING_A = "calibrating_a"     # calibration mode: waiting for first stick endpoint click
    CALIBRATING_B = "calibrating_b"     # calibration mode: waiting for second stick endpoint click
    SETTING_ORIGIN = "setting_origin"   # calibration mode: setting origin point
    TRACKING = "tracking"               # normal click → mark → advance workflow
    EDITING = "editing"                 # right-click context menu active (point move/delete)
```

Mode transitions: toolbar button enters calibration mode → sub-states CALIBRATING_A → CALIBRATING_B → optionally SETTING_ORIGIN → done → returns to TRACKING. TRACKING is the default when a video is loaded and calibration exists or is completed.

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Calibration not set, attempting to record | Status bar warning; record pixel coords anyway (allow late calibration) |
| Click outside video bounds | Ignore (no point recorded) |
| Frame seek fails | Blank frame + status bar error |
| Open non-MP4 | File dialog filter restricts to `*.mp4` |
| Corrupt calibration JSON | Status bar error; skip auto-load |
| Export with no data | Grayed-out menu item; or empty CSV with headers only |
| Late calibration applied | Iterate all stored TrackedPoints, recompute x_world/y_world from stored x_pixel/y_pixel using new pipeline |

## Export Format

### Standard CSV (tracked frames only)

```csv
# Tracker-Replacement Export
# Video: PhaseII_TestD_0001_c4_01.MP4
# FPS: 128
# Total frames: 20000
# Calibration: 0.1 m / 400.0 px = 0.00025 m/px
# Origin (px): (320.0, 240.0)
# Axis rotation: 0.0 deg
# Export timestamp: 2026-05-31T12:00:00Z
frame,timestamp_s,x_world,y_world,track_id,is_interpolated
0,0.0,0.0425,0.1283,0,False
1,0.0078125,0.0431,0.1279,0,False
```

### Full CSV (all frames, NaN for untracked)

```csv
# Tracker-Replacement Export (full)
# Video: PhaseII_TestD_0001_c4_01.MP4
# FPS: 128
# ...
frame,timestamp_s,x_world,y_world,track_id,is_interpolated
0,0.0,0.0425,0.1283,0,False
1,0.0078125,0.0431,0.1279,0,False
2,0.015625,,,,
3,0.0234375,,,,
```

Full export includes a row for every frame in the video; untracked frames have empty x_world/y_world fields. This preserves frame alignment for downstream analysis pipelines.

Columns: `frame`, `timestamp_s`, `x_world`, `y_world`, `track_id`, `is_interpolated`

## Constraints

- Zoom must be stable — no viewport shift on zoom or during rapid clicking
- Calibration data must be saveable/loadable between sessions
- UI layout: video canvas left, data panel right
- Click → auto-advance must not drop or skip points regardless of CPS
- Forward frame seeking must be near-instant via ring-buffer pre-decode; backward seek may incur keyframe decode latency
- Frame advance is non-blocking; perceived latency is handled by the ring buffer, not by sub-frame timing guarantees
