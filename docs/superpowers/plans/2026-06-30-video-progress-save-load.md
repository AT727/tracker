# Video Progress Save/Load Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to explicitly save and load tracking progress (marks + series) as sidecar `.tracker.json` files beside videos.

**Architecture:** JSON sidecar file containing serialized series and marks, loaded/saved by a `ProgressStore` class in the tracking domain. `TrackingCollector` gains a `load_from()` method. File menu gets two new actions.

**Tech Stack:** Python, PyQt5, json, pathlib

---

### Task 1: Add `load_from()` to TrackingCollector

**Files:**
- Modify: `tracker/tracking/collector.py:94-99`
- Test: `tests/test_collector.py`

- [ ] **Step 1: Write the failing test**

```python
def test_load_from_resets_and_populates():
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 1.0, 2.0)  # existing mark to be cleared

    series_list = [
        {"id": "s1", "label": "A", "color": "#ff0000"},
        {"id": "s2", "label": "B", "color": "#00ff00"},
    ]
    marks_list = [
        {"frame": 5, "timestamp_s": 0.5, "px": 10.0, "py": 20.0, "series_id": "s1"},
        {"frame": 6, "timestamp_s": 0.6, "px": 30.0, "py": 40.0, "series_id": "s1"},
    ]
    collector.load_from(series_list, marks_list, active_series_id="s2")

    assert len(collector.marks) == 2
    assert len(collector.series) == 2
    assert collector.active_series_id == "s2"

    s1 = collector.get_series("s1")
    assert s1 is not None
    assert s1.label == "A"
    assert s1.color == "#ff0000"

    marks_for_s1 = collector.marks_for_series("s1")
    assert len(marks_for_s1) == 2
    assert marks_for_s1[0].frame == 5
    assert marks_for_s1[0].px == 10.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_collector.py::test_load_from_resets_and_populates -v`
Expected: FAIL with `AttributeError: 'TrackingCollector' object has no attribute 'load_from'`

- [ ] **Step 3: Implement `load_from` in TrackingCollector**

Add after `clear_marks()` at line 96:

```python
def load_from(
    self,
    series_list: list[dict],
    marks_list: list[dict],
    active_series_id: str | None = None,
) -> None:
    self._series.clear()
    self._marks.clear()
    self._marks_by_key.clear()
    self._active_series_id = None

    for sd in series_list:
        from tracker.tracking.series import PointSeries
        s = PointSeries(id=sd["id"], label=sd["label"], color=sd["color"])
        self._series[s.id] = s

    for md in marks_list:
        mark = Mark(
            frame=md["frame"],
            timestamp_s=md["timestamp_s"],
            px=md["px"],
            py=md["py"],
            series_id=md["series_id"],
        )
        self._marks.append(mark)
        self._marks_by_key[(md["series_id"], md["frame"])] = len(self._marks) - 1

    if active_series_id and active_series_id in self._series:
        self._active_series_id = active_series_id
    elif self._series:
        self._active_series_id = next(iter(self._series))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_collector.py::test_load_from_resets_and_populates -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tracker/tracking/collector.py tests/test_collector.py
git commit -m "feat: add load_from to TrackingCollector"
```

---

### Task 2: Create ProgressStore

**Files:**
- Create: `tracker/tracking/persistence.py`
- Test: `tests/test_tracking_persistence.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from tracker.tracking.collector import TrackingCollector
from tracker.tracking.persistence import ProgressStore


def test_save_and_load_round_trip(tmp_path):
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 100.0, 200.0)
    collector.upsert_mark(1, 0.033, 110.0, 210.0)
    s2 = collector.add_series("Extra")
    collector.upsert_mark(2, 0.066, 120.0, 220.0, series_id=s2.id)

    path = tmp_path / "test.tracker.json"
    ProgressStore.save(path, collector)

    loaded_collector = TrackingCollector()
    ProgressStore.load_into(path, loaded_collector)

    assert len(loaded_collector.marks) == 3
    assert len(loaded_collector.series) == 2
    assert loaded_collector.get_series(s2.id) is not None

    marks = loaded_collector.marks
    assert marks[0].frame == 0
    assert marks[0].px == 100.0
    assert marks[1].frame == 1
    assert marks[2].frame == 2
    assert marks[2].series_id == s2.id


def test_save_sets_version_in_file(tmp_path):
    collector = TrackingCollector()
    path = tmp_path / "ver.tracker.json"
    ProgressStore.save(path, collector)
    with open(path) as f:
        data = json.load(f)
    assert data["version"] == 1


def test_load_missing_file_does_nothing(tmp_path):
    path = tmp_path / "nonexistent.tracker.json"
    collector = TrackingCollector()
    ProgressStore.load_into(path, collector)
    assert len(collector.marks) == 0
    assert len(collector.series) == 1  # default series still there


def test_load_corrupt_file_shows_warning(tmp_path, capsys):
    path = tmp_path / "bad.tracker.json"
    with open(path, "w") as f:
        f.write("not json")
    collector = TrackingCollector()
    ProgressStore.load_into(path, collector)
    captured = capsys.readouterr()
    assert "Could not load progress" in captured.out


def test_save_with_no_marks(tmp_path):
    collector = TrackingCollector()
    path = tmp_path / "empty.tracker.json"
    ProgressStore.save(path, collector)
    loaded = TrackingCollector()
    ProgressStore.load_into(path, loaded)
    assert len(loaded.series) == 1
    assert len(loaded.marks) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tracking_persistence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tracker.tracking.persistence'`

- [ ] **Step 3: Implement ProgressStore**

Create `tracker/tracking/persistence.py`:

```python
"""Save/load tracking progress as sidecar JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tracker.tracking.collector import TrackingCollector


class ProgressStore:
    @staticmethod
    def save(path: str | Path, collector: TrackingCollector) -> None:
        p = Path(path)
        payload: dict[str, Any] = {
            "version": 1,
            "active_series_id": collector.active_series_id,
            "series": [
                {"id": s.id, "label": s.label, "color": s.color}
                for s in collector.series
            ],
            "marks": [
                {
                    "frame": m.frame,
                    "timestamp_s": m.timestamp_s,
                    "px": m.px,
                    "py": m.py,
                    "series_id": m.series_id,
                }
                for m in collector.marks
            ],
        }
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @staticmethod
    def load_into(path: str | Path, collector: TrackingCollector) -> None:
        p = Path(path)
        if not p.is_file():
            return
        try:
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            print(f"Could not load progress from {p}")
            return
        series_list = data.get("series", [])
        marks_list = data.get("marks", [])
        active_series_id = data.get("active_series_id")
        collector.load_from(series_list, marks_list, active_series_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tracking_persistence.py -v`
Expected: PASS all 5 tests

- [ ] **Step 5: Commit**

```bash
git add tracker/tracking/persistence.py tests/test_tracking_persistence.py
git commit -m "feat: add ProgressStore for sidecar progress save/load"
```

---

### Task 3: Add Save/Load actions to MainWindow

**Files:**
- Modify: `tracker/app/main_window.py:215-260`
- Test: `tests/test_main_window.py`

- [ ] **Step 1: Write the failing test**

```python
def test_save_progress_action_disabled_when_no_video(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    save_action = None
    for action in window.menuBar().actions():
        if action.text() == "&File":
            for a in action.menu().actions():
                if "Save Progress" in a.text():
                    save_action = a
                    break
    assert save_action is not None
    assert not save_action.isEnabled()


def test_load_progress_with_existing_marks_shows_confirmation(qtbot, monkeypatch):
    from unittest.mock import MagicMock
    from PyQt5.QtWidgets import QMessageBox

    window = MainWindow()
    qtbot.addWidget(window)

    # Pretend we have marks already
    window.collector.upsert_mark(0, 0.0, 1.0, 2.0)

    confirmed = False
    def fake_question(*args, **kwargs):
        nonlocal confirmed
        confirmed = True
        return QMessageBox.Yes

    monkeypatch.setattr(QMessageBox, "question", fake_question)
    monkeypatch.setattr(window, "_do_load_progress", lambda path: None)

    from PyQt5.QtCore import QPoint
    load_action = None
    for action in window.menuBar().actions():
        if action.text() == "&File":
            for a in action.menu().actions():
                if "Load Progress" in a.text():
                    load_action = a
                    break
    assert load_action is not None
    load_action.trigger()
    assert confirmed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main_window.py::test_save_progress_action_disabled_when_no_video -v`
Expected: FAIL (assertion on save_action being not None or isEnabled will fail)

- [ ] **Step 3: Implement menu actions in `_build_menus`**

Add after the `export_action` block (line 222) and before `quit_action` (line 223):

```python
        save_progress_action = QAction("Save Progress...", self)
        save_progress_action.triggered.connect(self._save_progress)
        save_progress_action.setEnabled(False)
        file_menu.addAction(save_progress_action)
        load_progress_action = QAction("Load Progress...", self)
        load_progress_action.triggered.connect(self._load_progress)
        file_menu.addAction(load_progress_action)
        file_menu.addSeparator()
```

Store `save_progress_action` on self (add in `__init__`) and update `_load_video` to enable it when a video is loaded.

Add to `__init__` (after `self._autoclicker` line):
```python
        self._save_progress_action: QAction | None = None
```

Note: `save_progress_action` is set in `_build_menus`, store it:

In `_build_menus`, change:
```python
        save_progress_action = QAction("Save Progress...", self)
```
to:
```python
        self._save_progress_action = QAction("Save Progress...", self)
        self._save_progress_action.triggered.connect(self._save_progress)
        self._save_progress_action.setEnabled(False)
        file_menu.addAction(self._save_progress_action)
```

- [ ] **Step 3a: Enable save action when video is loaded**

In `_load_video` (`main_window.py:307`), at the end of the method:
```python
        if self._save_progress_action:
            self._save_progress_action.setEnabled(True)
```

- [ ] **Step 3b: Implement save handler**

```python
    def _save_progress(self) -> None:
        if not self._video_path:
            return
        default_name = f"{self._video_path.stem}.tracker.json"
        default_dir = str(self._video_path.parent)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Progress",
            str(Path(default_dir) / default_name),
            "Tracker Progress (*.tracker.json);;All Files (*)",
        )
        if not path:
            return
        from tracker.tracking.persistence import ProgressStore
        ProgressStore.save(path, self.collector)
        self._status.showMessage(f"Progress saved to {Path(path).name}", 5000)
```

- [ ] **Step 3c: Implement load handler**

```python
    def _load_progress(self) -> None:
        if not self._video_path:
            return
        if self.collector.marks:
            reply = QMessageBox.question(
                self,
                "Load Progress",
                "This will replace all current marks. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        default_dir = str(self._video_path.parent)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Progress",
            default_dir,
            "Tracker Progress (*.tracker.json);;All Files (*)",
        )
        if not path:
            return
        from tracker.tracking.persistence import ProgressStore
        ProgressStore.load_into(path, self.collector)
        self._marks_by_frame.clear()
        for mark in self.collector.marks:
            marks_for_frame = self._marks_by_frame.setdefault(mark.frame, [])
            marks_for_frame.append(mark)
        self._refresh_panels()
        self._refresh_marks_on_canvas()
        self._update_overlays()
        self._status.showMessage(f"Progress loaded from {Path(path).name}", 5000)
```

Add `self._marks_by_frame` handling — it already has `_sync_marks_for_frame` but `load_from` bulk-loads via `ProgressStore.load_into`, so we need to rebuild the frame index:

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main_window.py::test_save_progress_action_disabled_when_no_video tests/test_main_window.py::test_load_progress_with_existing_marks_shows_confirmation -v`
Expected: PASS

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests passing

- [ ] **Step 6: Commit**

```bash
git add tracker/app/main_window.py tests/test_main_window.py
git commit -m "feat: add Save/Load Progress menu actions"
```
