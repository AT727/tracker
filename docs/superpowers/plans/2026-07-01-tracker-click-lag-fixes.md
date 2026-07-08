# Tracker Advance-Click Lag Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate progressive lag in advance-click recording for long videos (10 min / 128 fps / 76,800 frames).

**Architecture:** Four independent changes — (1) O(1) mark frame lookup replaces O(n) full-list iteration, (2) async paint scheduling replaces synchronous repaint, (3) minimal viewport update mode reduces paint area, (4) cache size scales with frame dimensions.

**Tech Stack:** Python 3.12+, PyQt5 (QGraphicsView, QGraphicsScene, QGraphicsItem), OpenCV (cv2.VideoCapture), pytest + pytest-qt.

---

### Task 1: Add frame-level index to TrackingCollector

**Files:**
- Modify: `tracker/tracking/collector.py` — add `_marks_by_frame` index, `marks_for_frame()` method
- Test: `tests/test_collector.py` — add tests for frame-level queries

- [ ] **Step 1: Add `_marks_by_frame` dict and `marks_for_frame()` to collector**

Edit `tracker/tracking/collector.py`:

In `__init__`, add the new index:
```python
def __init__(self) -> None:
    self._series: dict[str, PointSeries] = {}
    self._marks: list[Mark] = []
    self._marks_by_key: dict[tuple[str, int], int] = {}
    self._marks_by_frame: dict[int, list[Mark]] = {}
    self._active_series_id: Optional[str] = None
    self._ensure_default_series()
```

In `upsert_mark`, update the index when inserting or replacing:
```python
def upsert_mark(
    self,
    frame: int,
    timestamp_s: float,
    px: float,
    py: float,
    series_id: str | None = None,
) -> tuple[Mark, bool]:
    sid = series_id or self._active_series_id
    if sid is None or sid not in self._series:
        raise ValueError("No active series")
    mark = Mark(frame=frame, timestamp_s=timestamp_s, px=px, py=py, series_id=sid)
    key = (sid, frame)

    existing_idx = self._marks_by_key.get(key)
    if existing_idx is not None:
        old = self._marks[existing_idx]
        old_frame_marks = self._marks_by_frame.get(old.frame)
        if old_frame_marks is not None:
            try:
                old_frame_marks.remove(old)
            except ValueError:
                pass
        self._marks[existing_idx] = mark
        self._marks_by_frame.setdefault(mark.frame, []).append(mark)
        return mark, True

    self._marks.append(mark)
    self._marks_by_key[key] = len(self._marks) - 1
    self._marks_by_frame.setdefault(mark.frame, []).append(mark)
    return mark, False
```

In `append_mark`, add to the index:
```python
def append_mark(self, ...) -> Mark:
    ...
    mark = Mark(...)
    self._marks.append(mark)
    self._marks_by_frame.setdefault(mark.frame, []).append(mark)
    return mark
```

In `clear_marks`, clear the new index:
```python
def clear_marks(self) -> None:
    self._marks.clear()
    self._marks_by_key.clear()
    self._marks_by_frame.clear()
```

In `load_from`, rebuild the new index:
```python
def load_from(self, series_list, marks_list, active_series_id) -> None:
    self._series.clear()
    self._marks.clear()
    self._marks_by_key.clear()
    self._marks_by_frame.clear()
    ...
    for m in marks_list:
        mark = Mark(...)
        self._marks.append(mark)
        self._marks_by_key[(mark.series_id, mark.frame)] = len(self._marks) - 1
        self._marks_by_frame.setdefault(mark.frame, []).append(mark)
    ...
```

Add public method:
```python
def marks_for_frame(self, frame: int) -> list[Mark]:
    return list(self._marks_by_frame.get(frame, []))
```

- [ ] **Step 2: Write tests for frame-level mark queries**

Add to `tests/test_collector.py`:

```python
def test_marks_for_frame_returns_frame_marks():
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 1.0, 2.0)
    collector.upsert_mark(0, 0.1, 3.0, 4.0)  # replace
    collector.upsert_mark(1, 0.2, 5.0, 6.0)
    assert len(collector.marks_for_frame(0)) == 1
    assert len(collector.marks_for_frame(1)) == 1
    assert len(collector.marks_for_frame(99)) == 0


def test_marks_for_frame_upsert_frame_change():
    """Upserting a mark at a new frame moves the old mark's frame entry."""
    collector = TrackingCollector()
    collector.upsert_mark(5, 0.0, 1.0, 2.0)
    # Replace at the same (series, frame) key — frame doesn't change
    collector.upsert_mark(5, 0.1, 3.0, 4.0)
    assert len(collector.marks_for_frame(5)) == 1
    assert len(collector.marks_for_frame(0)) == 0


def test_marks_for_frame_after_clear():
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 1.0, 2.0)
    collector.clear_marks()
    assert len(collector.marks_for_frame(0)) == 0
```

- [ ] **Step 3: Run new tests**

```bash
cd tracker && pytest tests/test_collector.py -v -k "marks_for_frame"
```
Expected: All 3 tests PASS.

---

### Task 2: Optimize main window frame sync and paint

**Files:**
- Modify: `tracker/app/main_window.py` — two changes: use `marks_for_frame()`, `repaint()` → `update()`

- [ ] **Step 1: Replace O(n) `_sync_marks_for_frame` with O(1) `marks_for_frame()`**

In `tracker/app/main_window.py`, replace:
```python
def _sync_marks_for_frame(self, frame: int) -> None:
    marks = [mark for mark in self.collector.marks if mark.frame == frame]
    if marks:
        self._marks_by_frame[frame] = marks
    else:
        self._marks_by_frame.pop(frame, None)
```
With:
```python
def _sync_marks_for_frame(self, frame: int) -> None:
    marks = self.collector.marks_for_frame(frame)
    if marks:
        self._marks_by_frame[frame] = marks
    else:
        self._marks_by_frame.pop(frame, None)
```

- [ ] **Step 2: Replace synchronous `repaint()` with async `update()`**

In `tracker/app/main_window.py`, at line 365 in `_on_frame_ready`, change:
```python
self._canvas.viewport().repaint()
```
To:
```python
self._canvas.viewport().update()
```

---

### Task 3: Minimal viewport updates

**Files:**
- Modify: `tracker/canvas/view.py` — one-line change

- [ ] **Step 1: Change viewport update mode**

In `tracker/canvas/view.py`, at line 32, change:
```python
self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
```
To:
```python
self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
```

Rationale: Frame pixmap changes always cover the full scene rect (dirty region = entire viewport), but overlay-only updates (marks, stick, grid) only repaint their bounding rects. The explicit `viewport().update()` in `_on_frame_ready` is a no-op since the scene's `update()` chain already schedules a viewport paint.

---

### Task 4: Adaptive cache sizing

**Files:**
- Modify: `tracker/video/decoder_worker.py` — compute cache size from frame dimensions
- Test: `tests/test_decoder_worker.py` — verify cache size adapts

- [ ] **Step 1: Add cache-size calculation helper and apply after open**

Add to `VideoDecoderWorker` in `tracker/video/decoder_worker.py`:

```python
@staticmethod
def _infer_cache_size(width: int, height: int) -> int:
    if width <= 0 or height <= 0:
        return 60
    pixels = width * height
    target_pixels = 100_000_000  # ~300 MB at 3 bytes/pixel × 300 frames
    size = target_pixels // pixels if pixels > 0 else 60
    return max(30, min(300, size))
```

In `__init__`, change:
```python
self._cache: FrameCache[tuple[QImage, float]] = FrameCache(max_size=60)
```
To:
```python
self._cache: FrameCache[tuple[QImage, float]] = FrameCache(max_size=60)
self._cache_max_size = 60
```

(The `__init__` default 60 is overridden after `_open_capture` sets real dimensions.)

In `_open_capture`, after setting `self._height` and `self._width`, add:
```python
self._cache_max_size = self._infer_cache_size(self._width, self._height)
self._cache = FrameCache(max_size=self._cache_max_size)
```

- [ ] **Step 2: Write test for cache sizing**

Add to `tests/test_decoder_worker.py`:

```python
def test_infer_cache_size_respects_bounds():
    assert VideoDecoderWorker._infer_cache_size(0, 0) == 60
    assert VideoDecoderWorker._infer_cache_size(768, 432) == 300   # ~332K px
    assert VideoDecoderWorker._infer_cache_size(1920, 1080) == 48   # ~2.07M px
    assert VideoDecoderWorker._infer_cache_size(3840, 2160) == 30   # ~8.29M px
    assert VideoDecoderWorker._infer_cache_size(1, 1) == 300        # clamp
```

Expected: `pytest tests/test_decoder_worker.py -v -k "infer_cache_size"` → PASS

- [ ] **Step 3: Verify cache is rebuilt on open**

Run the existing decoder tests to confirm `_open_capture` still works:
```bash
cd tracker && pytest tests/test_decoder_worker.py -v -k "opens_and_decodes or rapid_scrub"
```
Expected: Both tests PASS.

---

### Self-Review Checklist

1. **Spec coverage:** Each fix in the spec maps to exactly one task (Fix1→Task1, Fix2→Task2, Fix3→Task3, Fix4→Task4). No gaps.
2. **Placeholder scan:** All steps contain actual code or commands. No TBD, TODO, or "fill in details".
3. **Type consistency:** `marks_for_frame(frame: int) -> list[Mark]` used consistently in both collector.py and main_window.py. `_infer_cache_size(width, height) -> int` has one definition, one call site.
4. **Edge cases:** Cache sizing handles width=0/height=0 (default 60), tiny images clamp to 300, huge images clamp to 30. `marks_for_frame` returns empty list for missing frames.

---

### Execution Handoff

Plan complete. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
