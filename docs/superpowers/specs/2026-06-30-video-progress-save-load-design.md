# Video Progress Save/Load

## Goal

Allow users to save tracking progress (marks + series) on a video and load it back later, so long videos can be worked on across multiple sessions.

## Data Model

Saved data is explicit (File menu), not auto-saved. Calibration is already handled separately via auto-saved sidecar JSON.

### Sidecar file: `{video_stem}.tracker.json`

Saved beside the video, alongside the existing `{video_stem}.json` calibration file.

```json
{
  "version": 1,
  "active_series_id": "series-1",
  "series": [
    { "id": "series-1", "label": "Series 1", "color": "#0a84ff" }
  ],
  "marks": [
    { "frame": 0, "timestamp_s": 0.0, "px": 123.4, "py": 567.8, "series_id": "series-1" }
  ]
}
```

## Components

### New: `tracker/persistence/progress.py`

A `ProgressStore` class with static `save(path, collector)` and `load(path)` methods, mirroring `CalibrationStore`.

- `save`: Takes a file path and `TrackingCollector`, writes JSON with version, series, marks, active_series_id.
- `load`: Takes a file path, returns a dict with `{series, marks, active_series_id}` or `None` if file missing.

### Modified: `tracker/tracking/collector.py`

Add a `load_from(series_list, marks_list, active_series_id)` method:

1. Clear all existing series and marks (reset internal state)
2. Import each series from saved list
3. Import each mark from saved list
4. Set active series

### Modified: `tracker/app/main_window.py`

File menu gets two new actions above Quit:

- **Save Progress...** — `QFileDialog.getSaveFileName` defaulting to `{video_stem}.tracker.json` in the video's directory. Disabled if no video open.
- **Load Progress...** — `QFileDialog.getOpenFileName` filtered to `*.tracker.json`. If existing marks exist, warn with confirmation dialog. Calls `collector.load_from(...)`, then refreshes all panels.

## Edge Cases

- Save with no marks -> allowed, saves series structure
- Save with no video open -> menu item disabled
- Load into session with existing marks -> confirmation dialog: "This will replace all current marks. Continue?"
- Load from a file where series referenced by marks don't exist -> marks with orphan series_id are still loaded (collector holds them), but won't show in any active series display
- Corrupt/missing file -> show error message
