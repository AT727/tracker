# Tracker Advance-Click Lag Fixes

## Problem

When recording tracking points in a long video (10 min at 128 fps = 76,800 frames),
each click to record a point and advance the frame feels progressively more sluggish.
The delay accumulates over the session — frame 1 is snappy, frame 70,000 is not.

## Root Causes

### 1. O(n) mark frame sync on every click

`_sync_marks_for_frame(main_window.py:604)` is called on every `_record_click_at`.
It calls `self.collector.marks` which copies the entire `_marks` list (O(n)),
then filters to marks matching the current frame via list comprehension (second O(n)).
With 76,800 marks, each click copies and iterates 76,800 items.

### 2. Synchronous `repaint()` blocks the GUI thread

`_on_frame_ready` (main_window.py:365) calls `viewport().repaint()`, which is
*synchronous* — it immediately renders the full viewport and does not return until
the paint completes. All input events (clicks, key presses) are queued during this
time, creating perceived lag.

### 3. `FullViewportUpdate` forces unnecessary full redraws

`CanvasView` (view.py:32) uses `FullViewportUpdate`, which repaints the *entire*
viewport on any scene change. Even small overlay updates (mark position tweak,
grid overlay toggling) redraw every pixel. Combined with `repaint()`, every update
is maximally expensive.

### 4. Small cache at high frame rates

`VideoDecoderWorker` (decoder_worker.py:31) uses a fixed `max_size=60` cache.
At 128 fps this holds only 0.47 seconds of video — nearly useless for navigation
in a long video where the user might scrub back to previous frames.

## Fixes

### Fix 1: O(1) mark frame sync

**File:** `tracker/tracking/collector.py`

- Add `_marks_by_frame: dict[int, list[Mark]]` index to `TrackingCollector`
- Maintain incrementally in `upsert_mark` (append new mark, remove old on update)
- Maintain incrementally in `append_mark`
- Maintain in `clear_marks` and `load_from`
- Add `marks_for_frame(frame: int) -> list[Mark]` public method that returns a copy
  of the internal list for that frame (prevents external mutation of index)
- Update `_sync_marks_for_frame` in main_window.py to call `marks_for_frame`
- Handle all mutation paths: `upsert_mark`, `append_mark`, `clear_marks`, `load_from`

Effect: `_sync_marks_for_frame` goes from O(total marks) to O(marks in current frame)
— typically 1-2 items regardless of session length.

### Fix 2: Async repaint

**File:** `tracker/app/main_window.py`

- Change `self._canvas.viewport().repaint()` to `self._canvas.viewport().update()`
  at line 365 in `_on_frame_ready`

Effect: Paint is scheduled for the next event-loop iteration instead of blocking
the current one. The GUI thread can process the next click immediately.

### Fix 3: Minimal viewport updates

**File:** `tracker/canvas/view.py`

- Change `FullViewportUpdate` to `MinimalViewportUpdate` at line 32

Effect: Overlay-only changes (marks, stick, grid) repaint only the dirty bounding
rects instead of the full viewport. Frame pixmap changes still cover the full scene
rect so the paint area is the same for frame changes.

### Fix 4: Adaptive cache sizing

**File:** `tracker/video/decoder_worker.py`

- Infer a sensible `max_size` from frame dimensions:
  - Formula: `max_size = clamp(100_000_000 / (width * height), 30, 300)`
  - 100M pixels ~ 300 MB at 3 bytes/pixel across 300 frames
  - Edge case: if width or height is 0 (not yet opened), use default of 60
  - Must be computed after `_open_capture` sets `_width`/`_height`

Effect: Small-frame videos (like 768×432) get 300 frames; 1920×1080 gets 60;
3840×2160 gets 30. Cache memory stays under ~300 MB for any resolution, while
small-frame videos get a usefully large window for re-navigation.

## Files Changed

| File | Change |
|------|--------|
| `tracker/tracking/collector.py` | Add `_marks_by_frame` index, `marks_for_frame()` method |
| `tracker/app/main_window.py` | `repaint()` → `update()`; use `marks_for_frame()` |
| `tracker/canvas/view.py` | `FullViewportUpdate` → `MinimalViewportUpdate` |
| `tracker/video/decoder_worker.py` | Dynamic cache size from frame dimensions |

## Verification

1. Open a 10-minute video at 128 fps (768×432 or similar)
2. Record tracking points at ~2 clicks/sec for 60+ seconds
3. Verify click responsiveness does not degrade over time
4. Verify the next frame appears promptly after each click
5. GUI remains responsive during frame changes (no frozen frames)
6. Regression: verify the same session works identically for short videos
   and for large-frame videos (1920×1080)
