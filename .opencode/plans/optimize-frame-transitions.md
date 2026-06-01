# Optimize Frame-to-Frame Transition Latency

## Problem

Manual clicking for frame navigation has noticeable delay at every frame step (128 fps video).

## Root Cause

Three compounding issues in the click → frame-advance pipeline:

### 1. `_refresh_marks_on_canvas()` called TWICE per click (main_window.py)
- Line 385 in `_record_click_at()` refreshes marks for the **current** (departing) frame
- Line 478 in `_go_to_frame()` refreshes marks for the **target** frame
- The first call is invisible work — user never sees the departing frame's refreshed marks
- Each call destroys and recreates all mark `QGraphicsItem`s → multiple full viewport repaints

### 2. `_advance_frame()` called LAST in `_record_click_at()` (main_window.py:390)
The frame decode request (and any `frame_ready` cache-hit signal) is queued only after marks refresh, table refresh, and plot check all complete. The main thread must return to the event loop before `frame_ready` can be dispatched.

### 3. `set_marks()` destructively removes/creates items (scene.py:61-71)
Each call does `removeItem` + `clear` + `new MarkSquareItem` + `addItem` for every mark. With `FullViewportUpdate` mode (view.py:32), each add/remove triggers a full viewport repaint. For 5 marks: 10 repaints per call × 2 calls = 20 repaints per click.

## Proposed Changes

### Fix 1 + Fix 2: Reorder `_record_click_at()` (main_window.py:373-390)

Move `_advance_frame()` right after `upsert_mark() + _sync_marks_for_frame()`. Remove the redundant `_refresh_marks_on_canvas()` call.

**Before:**
```python
def _record_click_at(self, px: float, py: float) -> None:
    if self._frame_count <= 0:
        return
    mark, _ = self.collector.upsert_mark(...)
    self._sync_marks_for_frame(mark.frame)
    self._canvas.tracker_scene.show_click_feedback(px, py)
    self._refresh_marks_on_canvas()           # ← wasteful, removed
    if self._show_table.isChecked():
        QTimer.singleShot(0, self._refresh_table)
    self._maybe_refresh_plot()
    self._advance_frame()                     # ← called last
```

**After:**
```python
def _record_click_at(self, px: float, py: float) -> None:
    if self._frame_count <= 0:
        return
    mark, _ = self.collector.upsert_mark(...)
    self._sync_marks_for_frame(mark.frame)
    self._advance_frame()                     # ← called early
    self._canvas.tracker_scene.show_click_feedback(px, py)
    if self._show_table.isChecked():
        QTimer.singleShot(0, self._refresh_table)
    self._maybe_refresh_plot()
```

### Fix 3: Reuse mark items in `set_marks()` (scene.py:61-71)

Instead of removing all items and creating new ones, reuse existing `MarkSquareItem` instances by updating their position. Only create or destroy items when the count changes.

**Before:**
```python
def set_marks(self, marks: list[tuple[float, float, str]]) -> None:
    for item in self._mark_items:
        self.removeItem(item)
    self._mark_items.clear()
    for px, py, style in marks:
        if style == "dot":
            item = MarkDotItem(px, py)
        else:
            item = MarkSquareItem(px, py)
        self.addItem(item)
        self._mark_items.append(item)
```

**After:**
```python
def set_marks(self, marks: list[tuple[float, float, str]]) -> None:
    # Reuse existing items, update positions in-place.
    for i, (px, py, style) in enumerate(marks):
        if i < len(self._mark_items):
            item = self._mark_items[i]
            item.setPos(px, py)
        else:
            item = MarkSquareItem(px, py)
            self.addItem(item)
            self._mark_items.append(item)
    # Remove excess items.
    while len(self._mark_items) > len(marks):
        item = self._mark_items.pop()
        self.removeItem(item)
```

## Files to Modify

| File | Change |
|------|--------|
| `tracker/app/main_window.py:373-390` | Reorder `_record_click_at()` — move `_advance_frame()` early, remove duplicate `_refresh_marks_on_canvas()` |
| `tracker/canvas/scene.py:61-71` | Refactor `set_marks()` to reuse items in-place |

## Verification

1. Run `pytest` to confirm no test regressions
2. Check for any lint issues (`ruff` or `pyflakes`)
3. Manual smoke test: click through frames, verify marks still render correctly
