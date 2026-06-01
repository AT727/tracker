# Tracker Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop PyQt5 video analysis application for frame-by-frame point tracking on 128 fps wave tank experiment footage.

**Architecture:** Layered architecture with isolated coordinate pipeline (safety-critical, fully unit-tested), OpenCV on-demand decoding with forward ring-buffer cache, QGraphicsView scene-graph for stable zoom and overlay rendering, and signal-based data flow from click to table/plot updates.

**Tech Stack:** Python 3.10+, PyQt5, OpenCV, matplotlib, pytest, pytest-qt

---

### Task 0: Project Scaffold

**Files:**
- Create: `tracker/__init__.py`
- Create: `tracker/video/__init__.py`
- Create: `tracker/canvas/__init__.py`
- Create: `tracker/calibration/__init__.py`
- Create: `tracker/coordinates/__init__.py`
- Create: `tracker/tracking/__init__.py`
- Create: `tracker/panels/__init__.py`
- Create: `tracker/export/__init__.py`
- Create: `tracker/widgets/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `pyproject.toml`
- Create: `requirements.txt`

- [ ] **Step 1: Create directory structure and `__init__.py` files**

```bash
$directories = @(
    "tracker/video",
    "tracker/canvas",
    "tracker/calibration",
    "tracker/coordinates",
    "tracker/tracking",
    "tracker/panels",
    "tracker/export",
    "tracker/widgets",
    "tests"
)
foreach ($dir in $directories) {
    New-Item -ItemType Directory -Path $dir -Force
    New-Item -ItemType File -Path "$dir/__init__.py" -Force
}
New-Item -ItemType File -Path "tests/conftest.py" -Force
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "tracker-replacement"
version = "0.1.0"
description = "Desktop video analysis for frame-by-frame point tracking"
requires-python = ">=3.10"
dependencies = [
    "PyQt5>=5.15",
    "opencv-python>=4.8",
    "matplotlib>=3.7",
    "numpy>=1.24",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-qt>=4.2",
    "pytest-mock>=3.10",
]
```

- [ ] **Step 3: Create `requirements.txt`**

```
PyQt5>=5.15
opencv-python>=4.8
matplotlib>=3.7
numpy>=1.24
pytest>=7.0
pytest-qt>=4.2
pytest-mock>=3.10
```

- [ ] **Step 4: Create `tests/conftest.py` with sample-data fixtures**

```python
import numpy as np
import pytest
from PyQt5.QtGui import QImage


@pytest.fixture
def sample_qimage():
    """A 640x480 test image with a gradient pattern."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    arr[:, :, 0] = np.linspace(0, 255, 640, dtype=np.uint8)
    arr[:, :, 1] = np.linspace(0, 255, 480, dtype=np.uint8)[:, np.newaxis]
    return QImage(arr.data, 640, 480, QImage.Format_RGB888)


@pytest.fixture
def sample_calibration_data():
    from tracker.calibration.data import CalibrationData
    return CalibrationData(
        stick_endpoint_a_px=(100.0, 300.0),
        stick_endpoint_b_px=(500.0, 300.0),
        known_length=0.1,
        known_unit="m",
        origin_px=(320.0, 240.0),
        axis_rotation_deg=0.0,
        pixel_distance=400.0,
        scale=0.00025,
    )
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: scaffold project structure"
```

---

### Task 1: Data Models

**Files:**
- Create: `tracker/calibration/data.py`
- Create: `tracker/tracking/state.py`
- Create: `tests/test_data_models.py`

- [ ] **Step 1: Write failing tests**

`tests/test_data_models.py`:

```python
from tracker.calibration.data import CalibrationData
from tracker.tracking.state import AppMode


def test_calibration_data_defaults():
    data = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
    )
    assert data.known_unit == "m"
    assert data.scale == 0.01


def test_calibration_data_scale_computation():
    data = CalibrationData.from_endpoints(
        endpoint_a=(100.0, 300.0),
        endpoint_b=(500.0, 300.0),
        known_length=0.1,
    )
    assert data.pixel_distance == 400.0
    assert data.scale == 0.00025
    assert data.known_unit == "m"


def test_app_mode_values():
    assert AppMode.IDLE.value == "idle"
    assert AppMode.TRACKING.value == "tracking"
    assert AppMode.CALIBRATING_A.value == "calibrating_a"
    assert AppMode.CALIBRATING_B.value == "calibrating_b"
    assert AppMode.SETTING_ORIGIN.value == "setting_origin"
    assert AppMode.EDITING.value == "editing"
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_data_models.py -v
```
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement data models**

`tracker/calibration/data.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple


@dataclass
class CalibrationData:
    stick_endpoint_a_px: Tuple[float, float]
    stick_endpoint_b_px: Tuple[float, float]
    known_length: float
    known_unit: str
    origin_px: Tuple[float, float]
    axis_rotation_deg: float
    pixel_distance: float
    scale: float
    video_frame0_hash: str = ""

    @classmethod
    def from_endpoints(
        cls,
        endpoint_a: Tuple[float, float],
        endpoint_b: Tuple[float, float],
        known_length: float,
        unit: str = "m",
    ) -> "CalibrationData":
        dx = endpoint_b[0] - endpoint_a[0]
        dy = endpoint_b[1] - endpoint_a[1]
        pixel_distance = (dx**2 + dy**2) ** 0.5
        scale = known_length / pixel_distance
        return cls(
            stick_endpoint_a_px=endpoint_a,
            stick_endpoint_b_px=endpoint_b,
            known_length=known_length,
            known_unit=unit,
            origin_px=(0.0, 0.0),
            axis_rotation_deg=0.0,
            pixel_distance=pixel_distance,
            scale=scale,
        )

    @property
    def is_valid(self) -> bool:
        return self.pixel_distance > 0 and self.scale > 0

    def to_dict(self) -> dict:
        return {
            "stick_endpoint_a_px": list(self.stick_endpoint_a_px),
            "stick_endpoint_b_px": list(self.stick_endpoint_b_px),
            "known_length": self.known_length,
            "known_unit": self.known_unit,
            "origin_px": list(self.origin_px),
            "axis_rotation_deg": self.axis_rotation_deg,
            "pixel_distance": self.pixel_distance,
            "scale": self.scale,
            "video_frame0_hash": self.video_frame0_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationData":
        return cls(
            stick_endpoint_a_px=tuple(data["stick_endpoint_a_px"]),
            stick_endpoint_b_px=tuple(data["stick_endpoint_b_px"]),
            known_length=data["known_length"],
            known_unit=data["known_unit"],
            origin_px=tuple(data["origin_px"]),
            axis_rotation_deg=data["axis_rotation_deg"],
            pixel_distance=data["pixel_distance"],
            scale=data["scale"],
            video_frame0_hash=data.get("video_frame0_hash", ""),
        )
```

`tracker/tracking/state.py`:

```python
from enum import Enum


class AppMode(Enum):
    IDLE = "idle"
    CALIBRATING_A = "calibrating_a"
    CALIBRATING_B = "calibrating_b"
    SETTING_ORIGIN = "setting_origin"
    TRACKING = "tracking"
    EDITING = "editing"
```

- [ ] **Step 4: Run to pass**

```bash
pytest tests/test_data_models.py -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tracker/calibration/data.py tracker/tracking/state.py tests/test_data_models.py
git commit -m "feat: add data models (CalibrationData, AppMode)"
```

---

### Task 2: TrackedPoint and TrackingCollector

**Files:**
- Create: `tracker/tracking/collector.py`
- Modify: `tests/test_data_models.py` (append)

- [ ] **Step 1: Add TrackedPoint tests**

Append to `tests/test_data_models.py`:

```python
from tracker.tracking.collector import TrackedPoint, TrackingCollector


def test_tracked_point_defaults():
    p = TrackedPoint(frame=0, timestamp=0.0, x_world=1.0, y_world=2.0, x_pixel=100.0, y_pixel=200.0)
    assert p.track_id == "0"
    assert p.is_interpolated is False


def test_collector_append_and_iterate():
    collector = TrackingCollector()
    collector.record(0, 0.0, 1.0, 2.0, 100.0, 200.0)
    collector.record(1, 0.008, 1.5, 2.5, 150.0, 250.0)
    assert len(collector) == 2


def test_collector_get_by_frame():
    collector = TrackingCollector()
    collector.record(5, 0.04, 3.0, 4.0, 300.0, 400.0)
    pt = collector.get_by_frame(5)
    assert pt is not None
    assert collector.get_by_frame(0) is None


def test_collector_recompute_world_coords():
    collector = TrackingCollector()
    collector.record(0, 0.0, 0.0, 0.0, 100.0, 200.0)
    collector.recompute_world_coords(lambda px, py: (px * 0.01, py * 0.01))
    assert collector[0].x_world == 1.0
    assert collector[0].y_world == 2.0


def test_collector_all_frames_range():
    collector = TrackingCollector()
    collector.record(2, 0.016, 1.0, 1.0, 100.0, 100.0)
    collector.record(5, 0.04, 2.0, 2.0, 200.0, 200.0)
    all_frames = collector.all_frames_range(total_frames=10)
    assert all_frames[0] is None
    assert all_frames[2] is not None
    assert len(all_frames) == 10
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_data_models.py -v
```

- [ ] **Step 3: Implement `TrackedPoint` and `TrackingCollector`**

`tracker/tracking/collector.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple


@dataclass
class TrackedPoint:
    frame: int
    timestamp: float
    x_world: float
    y_world: float
    x_pixel: float
    y_pixel: float
    track_id: str = "0"
    is_interpolated: bool = False


class TrackingCollector:
    def __init__(self):
        self._points: List[TrackedPoint] = []

    def record(self, frame: int, timestamp: float, x_world: float, y_world: float,
               x_pixel: float, y_pixel: float, track_id: str = "0") -> TrackedPoint:
        pt = TrackedPoint(
            frame=frame, timestamp=timestamp, x_world=x_world, y_world=y_world,
            x_pixel=x_pixel, y_pixel=y_pixel, track_id=track_id,
        )
        self._points.append(pt)
        return pt

    def recompute_world_coords(self, pixel_to_world: Callable[[float, float], Tuple[float, float]]):
        for pt in self._points:
            pt.x_world, pt.y_world = pixel_to_world(pt.x_pixel, pt.y_pixel)

    def get_by_frame(self, frame: int) -> Optional[TrackedPoint]:
        for pt in self._points:
            if pt.frame == frame:
                return pt
        return None

    def all_frames_range(self, total_frames: int) -> List[Optional[TrackedPoint]]:
        lookup = {pt.frame: pt for pt in self._points}
        return [lookup.get(i) for i in range(total_frames)]

    def __len__(self) -> int:
        return len(self._points)

    def __getitem__(self, index: int) -> TrackedPoint:
        return self._points[index]

    def __iter__(self):
        return iter(self._points)
```

- [ ] **Step 4: Run to pass**

```bash
pytest tests/test_data_models.py -v
```
Expected: All 8 pass

- [ ] **Step 5: Commit**

```bash
git add tracker/tracking/collector.py tests/test_data_models.py
git commit -m "feat: add TrackedPoint and TrackingCollector"
```

---

### Task 3: Coordinate Transform Pipeline

**Files:**
- Create: `tracker/coordinates/transforms.py`
- Create: `tracker/coordinates/pipeline.py`
- Create: `tests/test_coordinates.py`

- [ ] **Step 1: Write failing tests**

`tests/test_coordinates.py`:

```python
import pytest
from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.calibration.data import CalibrationData


def test_pixel_to_world_identity():
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(1.0, 0.0),
        known_length=1.0, known_unit="m", origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0, pixel_distance=1.0, scale=1.0,
    )
    pipeline = CoordinatePipeline(cal)
    wx, wy = pipeline.pixel_to_world(100.0, 200.0)
    assert wx == pytest.approx(100.0)
    assert wy == pytest.approx(200.0)


def test_pixel_to_world_with_origin_offset():
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0, known_unit="m", origin_px=(320.0, 240.0),
        axis_rotation_deg=0.0, pixel_distance=100.0, scale=0.01,
    )
    pipeline = CoordinatePipeline(cal)
    wx, wy = pipeline.pixel_to_world(320.0, 240.0)
    assert wx == pytest.approx(0.0)
    assert wy == pytest.approx(0.0)
    wx, wy = pipeline.pixel_to_world(420.0, 240.0)
    assert wx == pytest.approx(1.0)


def test_pixel_to_world_scale_and_origin():
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(200.0, 0.0),
        known_length=2.0, known_unit="m", origin_px=(100.0, 50.0),
        axis_rotation_deg=0.0, pixel_distance=200.0, scale=0.01,
    )
    pipeline = CoordinatePipeline(cal)
    wx, wy = pipeline.pixel_to_world(200.0, 50.0)
    assert wx == pytest.approx(1.0)
    assert wy == pytest.approx(0.0)


def test_pixel_to_world_with_rotation():
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0, known_unit="m", origin_px=(0.0, 0.0),
        axis_rotation_deg=90.0, pixel_distance=100.0, scale=0.01,
    )
    pipeline = CoordinatePipeline(cal)
    wx, wy = pipeline.pixel_to_world(0.0, 100.0)
    assert wx == pytest.approx(-1.0, abs=1e-10)
    assert wy == pytest.approx(0.0, abs=1e-10)


def test_world_to_pixel_roundtrip():
    cal = CalibrationData(
        stick_endpoint_a_px=(50.0, 50.0), stick_endpoint_b_px=(450.0, 50.0),
        known_length=0.4, known_unit="m", origin_px=(250.0, 200.0),
        axis_rotation_deg=15.0, pixel_distance=400.0, scale=0.001,
    )
    pipeline = CoordinatePipeline(cal)
    px, py = 300.0, 250.0
    wx, wy = pipeline.pixel_to_world(px, py)
    px2, py2 = pipeline.world_to_pixel(wx, wy)
    assert px2 == pytest.approx(px, abs=1e-6)
    assert py2 == pytest.approx(py, abs=1e-6)


def test_scene_to_pixel_then_pixel_to_world():
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0, known_unit="m", origin_px=(50.0, 50.0),
        axis_rotation_deg=0.0, pixel_distance=100.0, scale=0.01,
    )
    pipeline = CoordinatePipeline(cal)
    wx, wy = pipeline.scene_to_world(200.0, 100.0, view_scale=2.0)
    assert wx == pytest.approx(-0.5, abs=1e-10)
    assert wy == pytest.approx(0.0, abs=1e-10)
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_coordinates.py -v
```
Expected: All fail (ModuleNotFoundError)

- [ ] **Step 3: Implement transforms**

`tracker/coordinates/transforms.py`:

```python
import math
from typing import Tuple


def build_translate_matrix(tx: float, ty: float):
    def translate(x: float, y: float) -> Tuple[float, float]:
        return x - tx, y - ty
    return translate


def build_scale_matrix(sx: float, sy: float):
    def scale(x: float, y: float) -> Tuple[float, float]:
        return x * sx, y * sy
    return scale


def build_rotation_matrix(degrees: float):
    rad = math.radians(degrees)
    c = math.cos(rad)
    s = math.sin(rad)
    def rotate(x: float, y: float) -> Tuple[float, float]:
        return x * c - y * s, x * s + y * c
    return rotate


def compose(*transforms):
    def composed(x: float, y: float) -> Tuple[float, float]:
        for t in transforms:
            x, y = t(x, y)
        return x, y
    return composed


def inverse_translate(tx: float, ty: float):
    def translate(x: float, y: float) -> Tuple[float, float]:
        return x + tx, y + ty
    return translate


def inverse_scale(sx: float, sy: float):
    def scale(x: float, y: float) -> Tuple[float, float]:
        return x / sx if sx != 0 else x, y / sy if sy != 0 else y
    return scale


def inverse_rotation(degrees: float):
    return build_rotation_matrix(-degrees)
```

- [ ] **Step 4: Implement pipeline**

`tracker/coordinates/pipeline.py`:

```python
from __future__ import annotations
from typing import Tuple
from tracker.calibration.data import CalibrationData
from tracker.coordinates.transforms import (
    build_translate_matrix, build_scale_matrix, build_rotation_matrix,
    compose, inverse_translate, inverse_scale, inverse_rotation,
)


class CoordinatePipeline:
    """5-step pixel-to-world coordinate transform (translate before scale)."""

    def __init__(self, calibration: CalibrationData):
        self.cal = calibration
        self._forward = compose(
            build_translate_matrix(calibration.origin_px[0], calibration.origin_px[1]),
            build_scale_matrix(calibration.scale, -calibration.scale),
            build_rotation_matrix(calibration.axis_rotation_deg),
        )
        self._inverse = compose(
            inverse_rotation(calibration.axis_rotation_deg),
            inverse_scale(calibration.scale, -calibration.scale),
            inverse_translate(calibration.origin_px[0], calibration.origin_px[1]),
        )

    def scene_to_world(self, sx: float, sy: float, view_scale: float = 1.0) -> Tuple[float, float]:
        px = sx / view_scale
        py = sy / view_scale
        return self.pixel_to_world(px, py)

    def pixel_to_world(self, px: float, py: float) -> Tuple[float, float]:
        return self._forward(px, py)

    def world_to_pixel(self, wx: float, wy: float) -> Tuple[float, float]:
        return self._inverse(wx, wy)

    def world_to_scene(self, wx: float, wy: float, view_scale: float = 1.0) -> Tuple[float, float]:
        px, py = self._inverse(wx, wy)
        return px * view_scale, py * view_scale

    @classmethod
    def identity(cls) -> CoordinatePipeline:
        cal = CalibrationData(
            stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(1.0, 0.0),
            known_length=1.0, known_unit="px", origin_px=(0.0, 0.0),
            axis_rotation_deg=0.0, pixel_distance=1.0, scale=1.0,
        )
        return cls(cal)
```

- [ ] **Step 5: Run to pass**

```bash
pytest tests/test_coordinates.py -v
```
Expected: All 7 pass

- [ ] **Step 6: Commit**

```bash
git add tracker/coordinates/ tests/test_coordinates.py
git commit -m "feat: add coordinate transform pipeline"
```

---

### Task 4: Calibration Persistence

**Files:**
- Create: `tracker/calibration/persistence.py`
- Create: `tests/test_calibration.py`

- [ ] **Step 1: Write failing tests**

`tests/test_calibration.py`:

```python
from pathlib import Path
from tracker.calibration.data import CalibrationData
from tracker.calibration.persistence import CalibrationStore


def test_save_and_load_roundtrip(tmp_path):
    cal = CalibrationData(
        stick_endpoint_a_px=(100.0, 300.0), stick_endpoint_b_px=(500.0, 300.0),
        known_length=0.1, known_unit="m", origin_px=(320.0, 240.0),
        axis_rotation_deg=0.0, pixel_distance=400.0, scale=0.00025, video_frame0_hash="abc123",
    )
    path = tmp_path / "test_calibration.json"
    store = CalibrationStore(tmp_path)
    store.save(cal, filename=path.name)
    loaded = store.load(filename=path.name)
    assert loaded.known_length == 0.1
    assert loaded.origin_px == (320.0, 240.0)
    assert loaded.scale == 0.00025
    assert loaded.video_frame0_hash == "abc123"


def test_load_missing_file_returns_none(tmp_path):
    store = CalibrationStore(tmp_path / "nonexistent.json")
    assert store.load() is None


def test_load_corrupt_file_returns_none(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("not json")
    store = CalibrationStore(tmp_path)
    assert store.load(filename=path.name) is None


def test_find_by_hash_matches(tmp_path):
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0, known_unit="m", origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0, pixel_distance=100.0, scale=0.01, video_frame0_hash="target_hash",
    )
    store = CalibrationStore(tmp_path)
    store.save(cal, filename="match.calibration.json")
    result = CalibrationStore.find_by_hash(tmp_path, "target_hash")
    assert result is not None
    assert result.known_length == 1.0


def test_find_by_hash_no_match(tmp_path):
    result = CalibrationStore.find_by_hash(tmp_path, "nope")
    assert result is None
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_calibration.py -v
```

- [ ] **Step 3: Implement persistence**

`tracker/calibration/persistence.py`:

```python
from __future__ import annotations
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional
from PyQt5.QtGui import QImage
from tracker.calibration.data import CalibrationData

logger = logging.getLogger(__name__)


class CalibrationStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)

    def save(self, cal: CalibrationData, filename: Optional[str] = None) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (filename or f"{cal.video_frame0_hash}.calibration.json")
        with open(path, "w") as f:
            json.dump(cal.to_dict(), f, indent=2)
        return path

    def load(self, filename: Optional[str] = None) -> Optional[CalibrationData]:
        if filename:
            path = self.directory / filename
        else:
            candidates = list(self.directory.glob("*.calibration.json"))
            if not candidates:
                return None
            path = candidates[0]
        if not path.exists():
            return None
        try:
            with open(path) as f:
                return CalibrationData.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to load calibration %s: %s", path, e)
            return None

    @staticmethod
    def find_by_hash(search_dir: Path, frame0_hash: str) -> Optional[CalibrationData]:
        for fpath in Path(search_dir).glob("*.calibration.json"):
            try:
                with open(fpath) as f:
                    data = json.load(f)
                if data.get("video_frame0_hash") == frame0_hash:
                    return CalibrationData.from_dict(data)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        return None

    @staticmethod
    def compute_frame0_hash(qimage: QImage) -> str:
        ptr = qimage.constBits()
        ptr.setsize(qimage.byteCount())
        data = bytes(ptr.asarray(qimage.byteCount()))
        return hashlib.sha256(data).hexdigest()
```

- [ ] **Step 4: Run to pass**

```bash
pytest tests/test_calibration.py -v
```
Expected: All 5 pass

- [ ] **Step 5: Commit**

```bash
git add tracker/calibration/persistence.py tests/test_calibration.py
git commit -m "feat: add calibration persistence"
```

---

### Task 5: Video Decoder

**Files:**
- Create: `tracker/video/decoder.py`
- Create: `tests/test_decoder.py`

- [ ] **Step 1: Write failing tests**

`tests/test_decoder.py`:

```python
from pathlib import Path
from tracker.video.decoder import VideoDecoder


def test_decoder_opens_nonexistent_raises():
    dec = VideoDecoder()
    try:
        dec.open(Path("nonexistent.mp4"))
        assert False
    except FileNotFoundError:
        pass


def test_decoder_frame_count_with_no_video():
    dec = VideoDecoder()
    assert dec.total_frames == 0
    assert dec.fps == 0.0


def test_decoder_get_nonexistent_frame():
    dec = VideoDecoder()
    assert dec.get_frame(0) is None


def test_ring_buffer_initial_state():
    dec = VideoDecoder()
    assert dec.ring_buffer_size == 30
    assert dec.cache_hits == 0
    assert dec.cache_misses == 0


def test_ring_buffer_size_config():
    dec = VideoDecoder(ring_buffer_size=10)
    assert dec.ring_buffer_size == 10
```

- [ ] **Step 2: Run to verify failures**

```bash
pytest tests/test_decoder.py -v
```
Expected: All fail

- [ ] **Step 3: Implement VideoDecoder**

`tracker/video/decoder.py`:

```python
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np
from PyQt5.QtGui import QImage

logger = logging.getLogger(__name__)


class FrameCache:
    def __init__(self, size: int = 30):
        self.size = size
        self._frames: dict[int, Tuple[QImage, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, frame_index: int) -> Optional[Tuple[QImage, float]]:
        result = self._frames.get(frame_index)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    def put(self, frame_index: int, data: Tuple[QImage, float]):
        self._frames[frame_index] = data
        if len(self._frames) > self.size * 2:
            self._evict()

    def _evict(self):
        sorted_keys = sorted(self._frames.keys())
        to_remove = sorted_keys[:len(sorted_keys) - self.size]
        for k in to_remove:
            del self._frames[k]

    def prefill(self, cap: cv2.VideoCapture, start: int, count: int):
        for i in range(count):
            idx = start + i
            if idx in self._frames or idx < 0:
                continue
            result = self._decode_frame(cap, idx)
            if result is not None:
                self._frames[idx] = result

    @staticmethod
    def _decode_frame(cap: cv2.VideoCapture, idx: int) -> Optional[Tuple[QImage, float]]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, mat = cap.read()
        if not ret:
            return None
        timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        mat_rgb = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)
        h, w, ch = mat_rgb.shape
        qimg = QImage(mat_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        return qimg, timestamp_ms / 1000.0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses


class VideoDecoder:
    def __init__(self, ring_buffer_size: int = 30):
        self._cap: Optional[cv2.VideoCapture] = None
        self._total_frames: int = 0
        self._fps: float = 0.0
        self._width: int = 0
        self._height: int = 0
        self._current_frame: int = -1
        self._cache = FrameCache(ring_buffer_size)

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def ring_buffer_size(self) -> int:
        return self._cache.size

    @property
    def cache_hits(self) -> int:
        return self._cache.hits

    @property
    def cache_misses(self) -> int:
        return self._cache.misses

    def open(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Video not found: {path}")
        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video: {path}")
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._current_frame = -1

    def close(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._total_frames = 0
        self._fps = 0.0
        self._current_frame = -1

    def get_frame(self, frame_index: int) -> Optional[Tuple[QImage, float]]:
        if self._cap is None:
            return None
        if frame_index < 0 or frame_index >= self._total_frames:
            return None
        cached = self._cache.get(frame_index)
        if cached is not None:
            self._current_frame = frame_index
            return cached
        result = FrameCache._decode_frame(self._cap, frame_index)
        if result is not None:
            self._cache.put(frame_index, result)
            self._current_frame = frame_index
            self._cache.prefill(self._cap, frame_index + 1, self._cache.size)
        return result

    def get_frame_info(self) -> str:
        return f"{self._fps:.0f} fps  Frame {self._current_frame + 1}/{self._total_frames}"
```

- [ ] **Step 4: Run to pass**

```bash
pytest tests/test_decoder.py -v
```
Expected: All 5 pass

- [ ] **Step 5: Commit**

```bash
git add tracker/video/decoder.py tests/test_decoder.py
git commit -m "feat: add video decoder with ring buffer"
```

---

### Task 6: Canvas Overlay Items

**Files:**
- Create: `tracker/canvas/items.py`

- [ ] **Step 1: Implement overlay items**

`tracker/canvas/items.py`:

```python
from __future__ import annotations
import math
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPainter, QPainterPath
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem
from tracker.calibration.data import CalibrationData


class CalibrationStickItem(QGraphicsLineItem):
    def __init__(self, calibration: CalibrationData, parent=None):
        super().__init__(parent)
        self.setPen(QPen(QColor(0, 255, 0), 2, Qt.SolidLine))
        self.setLine(
            calibration.stick_endpoint_a_px[0], calibration.stick_endpoint_a_px[1],
            calibration.stick_endpoint_b_px[0], calibration.stick_endpoint_b_px[1],
        )
        mid = QPointF(
            (calibration.stick_endpoint_a_px[0] + calibration.stick_endpoint_b_px[0]) / 2,
            (calibration.stick_endpoint_a_px[1] + calibration.stick_endpoint_b_px[1]) / 2,
        )
        self._label = QGraphicsTextItem(self)
        self._label.setPlainText(f"{calibration.known_length} {calibration.known_unit}")
        self._label.setDefaultTextColor(QColor(0, 255, 0))
        self._label.setFont(QFont("Monospace", 10, QFont.Bold))
        self._label.setPos(mid + QPointF(5, -15))
        for x, y in [calibration.stick_endpoint_a_px, calibration.stick_endpoint_b_px]:
            dot = QGraphicsEllipseItem(-4, -4, 8, 8, self)
            dot.setPos(x, y)
            dot.setBrush(QBrush(QColor(0, 255, 0)))
            dot.setPen(QPen(Qt.NoPen))

    def update_calibration(self, calibration: CalibrationData):
        self.setLine(
            calibration.stick_endpoint_a_px[0], calibration.stick_endpoint_a_px[1],
            calibration.stick_endpoint_b_px[0], calibration.stick_endpoint_b_px[1],
        )


class OriginGridItem(QGraphicsItem):
    def __init__(self, calibration: CalibrationData, pipeline=None, parent=None):
        super().__init__(parent)
        self._cal = calibration
        self._pipeline = pipeline
        self._grid_spacing = 0.01

    def boundingRect(self):
        return QRectF(-10000, -10000, 20000, 20000)

    def paint(self, painter: QPainter, option, widget=None):
        ox, oy = self._cal.origin_px
        painter.setPen(QPen(QColor(255, 0, 0, 180), 1, Qt.DashLine))
        cs = 20
        painter.drawLine(QPointF(ox - cs, oy), QPointF(ox + cs, oy))
        painter.drawLine(QPointF(ox, oy - cs), QPointF(ox, oy + cs))
        if self._pipeline is not None and self._cal.scale > 0:
            painter.setPen(QPen(QColor(255, 0, 0, 80), 1, Qt.DotLine))
            spacing_px = self._grid_spacing / self._cal.scale
            angle_rad = math.radians(self._cal.axis_rotation_deg)
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            for i in range(-50, 51):
                if i == 0:
                    continue
                offset = i * spacing_px
                dx = offset * cos_a
                dy = offset * sin_a
                painter.drawLine(
                    QPointF(ox + dx - 5000 * (-sin_a), oy + dy - 5000 * cos_a),
                    QPointF(ox + dx + 5000 * (-sin_a), oy + dy + 5000 * cos_a),
                )

    def update_calibration(self, calibration: CalibrationData, pipeline=None):
        self._cal = calibration
        self._pipeline = pipeline
        self.update()


class TrackedPointDot(QGraphicsEllipseItem):
    def __init__(self, px: float, py: float, radius: float = 4.0, parent=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2, parent)
        self.setPos(px, py)
        self.setBrush(QBrush(QColor(255, 0, 0)))
        self.setPen(QPen(QColor(200, 0, 0), 1))
        self.setZValue(10)


class FrameCounterItem(QGraphicsTextItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Monospace", 12, QFont.Bold))
        self.setDefaultTextColor(QColor(255, 255, 0))
        self.setPlainText("No video loaded")
        self.setPos(10, 10)
        self.setZValue(100)

    def update_info(self, fps: float, frame: int, total: int, timestamp: float):
        self.setPlainText(f"{fps:.0f} fps  Frame {frame + 1}/{total}  t = {timestamp:.3f} s")

    def set_idle(self):
        self.setPlainText("No video loaded")
```

- [ ] **Step 2: Commit**

```bash
git add tracker/canvas/items.py
git commit -m "feat: add canvas overlay items"
```

---

### Task 7: Canvas Scene and View

**Files:**
- Create: `tracker/canvas/scene.py`
- Create: `tracker/canvas/view.py`

- [ ] **Step 1: Implement scene**

`tracker/canvas/scene.py`:

```python
from __future__ import annotations
from typing import Optional
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWidgets import QGraphicsScene
from tracker.canvas.items import CalibrationStickItem, OriginGridItem, TrackedPointDot, FrameCounterItem


class TrackerScene(QGraphicsScene):
    point_clicked = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._background: Optional[QPixmap] = None
        self._calibration_stick: Optional[CalibrationStickItem] = None
        self._origin_grid: Optional[OriginGridItem] = None
        self._frame_counter = FrameCounterItem()
        self._dots: list[TrackedPointDot] = []
        self._show_stick = True
        self._show_grid = True
        self.setSceneRect(-10000, -10000, 20000, 20000)
        self.addItem(self._frame_counter)

    def set_background(self, pixmap: Optional[QPixmap]):
        self._background = pixmap
        if pixmap is not None:
            self.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        if self._background is not None:
            painter.drawPixmap(0, 0, self._background)

    def set_calibration_stick(self, stick: Optional[CalibrationStickItem]):
        if self._calibration_stick is not None:
            self.removeItem(self._calibration_stick)
        self._calibration_stick = stick
        if stick is not None:
            self.addItem(stick)
            stick.setVisible(self._show_stick)

    def set_origin_grid(self, grid: Optional[OriginGridItem]):
        if self._origin_grid is not None:
            self.removeItem(self._origin_grid)
        self._origin_grid = grid
        if grid is not None:
            self.addItem(grid)
            grid.setVisible(self._show_grid)

    def toggle_stick(self, visible: bool):
        self._show_stick = visible
        if self._calibration_stick is not None:
            self._calibration_stick.setVisible(visible)

    def toggle_grid(self, visible: bool):
        self._show_grid = visible
        if self._origin_grid is not None:
            self._origin_grid.setVisible(visible)

    def add_dot(self, px: float, py: float) -> TrackedPointDot:
        dot = TrackedPointDot(px, py)
        self.addItem(dot)
        self._dots.append(dot)
        return dot

    def clear_dots(self):
        for dot in self._dots:
            self.removeItem(dot)
        self._dots.clear()

    @property
    def frame_counter(self) -> FrameCounterItem:
        return self._frame_counter
```

- [ ] **Step 2: Implement view**

`tracker/canvas/view.py`:

```python
from __future__ import annotations
from typing import Optional, Callable
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QWheelEvent, QMouseEvent, QPainter
from PyQt5.QtWidgets import QGraphicsView
from tracker.canvas.scene import TrackerScene


class TrackerView(QGraphicsView):
    canvas_clicked = pyqtSignal(float, float)

    def __init__(self, scene: TrackerScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCursor(Qt.CrossCursor)
        self._min_zoom = 0.05
        self._max_zoom = 50.0
        self._click_callback: Optional[Callable] = None

    def set_click_callback(self, callback: Optional[Callable]):
        self._click_callback = callback

    def wheelEvent(self, event: QWheelEvent):
        old_pos = self.mapToScene(event.pos())
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_zoom = self.transform().m11() * factor
        if new_zoom < self._min_zoom or new_zoom > self._max_zoom:
            return
        self.scale(factor, factor)
        new_pos = self.mapToScene(event.pos())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            self.canvas_clicked.emit(pos.x(), pos.y())
            if self._click_callback is not None:
                self._click_callback(pos.x(), pos.y())
        super().mousePressEvent(event)

    def fit_to_view(self):
        self.resetTransform()
        self.setSceneRect(self.scene().sceneRect())
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def get_view_scale(self) -> float:
        return self.transform().m11()
```

- [ ] **Step 3: Commit**

```bash
git add tracker/canvas/scene.py tracker/canvas/view.py
git commit -m "feat: add canvas scene and view with stable zoom"
```

---

### Task 8: Calibration Controller

**Files:**
- Create: `tracker/calibration/controller.py`
- Modify: `tests/test_calibration.py` (append)

- [ ] **Step 1: Add controller tests**

Append to `tests/test_calibration.py`:

```python
from tracker.calibration.controller import CalibrationController
from tracker.tracking.state import AppMode


def test_controller_starts_idle():
    ctrl = CalibrationController()
    assert ctrl.mode == AppMode.IDLE
    assert not ctrl.is_active


def test_controller_stick_mode_flow():
    ctrl = CalibrationController()
    ctrl.start_stick_calibration()
    assert ctrl.mode == AppMode.CALIBRATING_A
    result = ctrl.handle_click(100.0, 200.0)
    assert result is None
    assert ctrl.mode == AppMode.CALIBRATING_B
    result = ctrl.handle_click(500.0, 200.0)
    assert result is not None
    assert result.pixel_distance == 400.0


def test_controller_stick_cancel():
    ctrl = CalibrationController()
    ctrl.start_stick_calibration()
    ctrl.handle_click(100.0, 200.0)
    ctrl.cancel()
    assert ctrl.mode == AppMode.IDLE


def test_controller_origin_mode():
    ctrl = CalibrationController()
    ctrl.start_origin_calibration()
    assert ctrl.mode == AppMode.SETTING_ORIGIN
    ctrl.handle_origin_click(320.0, 240.0)
    assert ctrl._pending_origin == (320.0, 240.0)
    ctrl.finish_origin_calibration()
    assert ctrl.mode == AppMode.IDLE


def test_controller_handle_click_idle():
    ctrl = CalibrationController()
    assert ctrl.handle_click(100.0, 100.0) is None
```

- [ ] **Step 2: Run to verify**

```bash
pytest tests/test_calibration.py -v
```
Expected: New tests fail

- [ ] **Step 3: Implement controller**

`tracker/calibration/controller.py`:

```python
from __future__ import annotations
from typing import Optional, Tuple
from tracker.calibration.data import CalibrationData
from tracker.tracking.state import AppMode


class CalibrationController:
    def __init__(self):
        self._mode = AppMode.IDLE
        self._stick_a: Optional[Tuple[float, float]] = None
        self._pending_origin: Optional[Tuple[float, float]] = None
        self._known_length: float = 0.1

    @property
    def mode(self) -> AppMode:
        return self._mode

    @property
    def is_active(self) -> bool:
        return self._mode not in (AppMode.IDLE, AppMode.TRACKING)

    def start_stick_calibration(self, known_length: float = 0.1):
        self._mode = AppMode.CALIBRATING_A
        self._stick_a = None
        self._known_length = known_length

    def handle_click(self, sx: float, sy: float) -> Optional[CalibrationData]:
        if self._mode == AppMode.CALIBRATING_A:
            self._stick_a = (sx, sy)
            self._mode = AppMode.CALIBRATING_B
            return None
        if self._mode == AppMode.CALIBRATING_B and self._stick_a is not None:
            cal = CalibrationData.from_endpoints(self._stick_a, (sx, sy), self._known_length)
            self._mode = AppMode.IDLE
            return cal
        return None

    def start_origin_calibration(self):
        self._mode = AppMode.SETTING_ORIGIN
        self._pending_origin = None

    def handle_origin_click(self, sx: float, sy: float):
        if self._mode == AppMode.SETTING_ORIGIN:
            self._pending_origin = (sx, sy)

    def finish_origin_calibration(self, rotation_deg: float = 0.0) -> Optional[CalibrationData]:
        if self._pending_origin is None:
            return None
        self._mode = AppMode.IDLE
        return CalibrationData(
            stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(1.0, 0.0),
            known_length=1.0, known_unit="m", origin_px=self._pending_origin,
            axis_rotation_deg=rotation_deg, pixel_distance=1.0, scale=1.0,
        )

    def cancel(self):
        self._mode = AppMode.IDLE
        self._stick_a = None
        self._pending_origin = None
```

- [ ] **Step 4: Run to pass**

```bash
pytest tests/test_calibration.py -v
```
Expected: All 10 pass

- [ ] **Step 5: Commit**

```bash
git add tracker/calibration/controller.py tests/test_calibration.py
git commit -m "feat: add calibration controller"
```

---

### Task 9: CSV Export Module

**Files:**
- Create: `tracker/export/exporter.py`
- Create: `tests/test_exporter.py`

- [ ] **Step 1: Write failing tests**

`tests/test_exporter.py`:

```python
from io import StringIO
from tracker.export.exporter import Exporter
from tracker.tracking.collector import TrackingCollector
from tracker.calibration.data import CalibrationData


def test_export_standard_csv():
    col = TrackingCollector()
    col.record(0, 0.0, 0.0425, 0.1283, 100.0, 200.0)
    col.record(1, 0.0078125, 0.0431, 0.1279, 101.0, 199.0)
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(100.0, 0.0),
        known_length=0.1, known_unit="m", origin_px=(320.0, 240.0),
        axis_rotation_deg=0.0, pixel_distance=100.0, scale=0.001,
    )
    exporter = Exporter()
    buf = StringIO()
    exporter.export_standard(buf, col, cal, "test.mp4", 128, 20000)
    buf.seek(0)
    content = buf.read()
    assert "# Video: test.mp4" in content
    assert "0,0.0,0.0425,0.1283,0,False" in content


def test_export_full_csv_includes_untracked():
    col = TrackingCollector()
    col.record(2, 0.015625, 1.0, 2.0, 100.0, 100.0)
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0, known_unit="m", origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0, pixel_distance=100.0, scale=0.01,
    )
    exporter = Exporter()
    buf = StringIO()
    exporter.export_full(buf, col, cal, "test.mp4", 128, 5)
    buf.seek(0)
    lines = [l for l in buf.readlines() if not l.startswith("#")]
    assert lines[0].startswith("0,")
    assert ",," in lines[0]  # untracked frame


def test_export_empty_collector():
    exporter = Exporter()
    buf = StringIO()
    exporter.export_standard(buf, TrackingCollector(), None, "empty.mp4", 30, 100)
    buf.seek(0)
    content = buf.read()
    assert "# Video: empty.mp4" in content
```

- [ ] **Step 2: Run to verify**

```bash
pytest tests/test_exporter.py -v
```
Expected: All fail

- [ ] **Step 3: Implement exporter**

`tracker/export/exporter.py`:

```python
from __future__ import annotations
import csv
from datetime import datetime, timezone
from typing import IO, Optional
from tracker.tracking.collector import TrackingCollector
from tracker.calibration.data import CalibrationData


class Exporter:
    def _write_header(self, f: IO, video_name: str, fps: float, total_frames: int,
                      calibration: Optional[CalibrationData], mode: str = ""):
        f.write(f"# Tracker-Replacement Export{mode}\n")
        f.write(f"# Video: {video_name}\n")
        f.write(f"# FPS: {fps}\n")
        f.write(f"# Total frames: {total_frames}\n")
        if calibration is not None:
            f.write(f"# Calibration: {calibration.known_length} {calibration.known_unit} / "
                    f"{calibration.pixel_distance:.1f} px = {calibration.scale:.6f} {calibration.known_unit}/px\n")
            f.write(f"# Origin (px): ({calibration.origin_px[0]:.1f}, {calibration.origin_px[1]:.1f})\n")
            f.write(f"# Axis rotation: {calibration.axis_rotation_deg:.1f} deg\n")
        f.write(f"# Export timestamp: {datetime.now(timezone.utc).isoformat()}\n")

    def export_standard(self, f: IO, collector: TrackingCollector,
                        calibration: Optional[CalibrationData],
                        video_name: str, fps: float, total_frames: int):
        self._write_header(f, video_name, fps, total_frames, calibration)
        writer = csv.writer(f)
        writer.writerow(["frame", "timestamp_s", "x_world", "y_world", "track_id", "is_interpolated"])
        for pt in collector:
            writer.writerow([pt.frame, pt.timestamp, pt.x_world, pt.y_world, pt.track_id, pt.is_interpolated])

    def export_full(self, f: IO, collector: TrackingCollector,
                    calibration: Optional[CalibrationData],
                    video_name: str, fps: float, total_frames: int):
        self._write_header(f, video_name, fps, total_frames, calibration, mode=" (full)")
        writer = csv.writer(f)
        writer.writerow(["frame", "timestamp_s", "x_world", "y_world", "track_id", "is_interpolated"])
        for i, pt in enumerate(collector.all_frames_range(total_frames)):
            if pt is not None:
                writer.writerow([pt.frame, pt.timestamp, pt.x_world, pt.y_world, pt.track_id, pt.is_interpolated])
            else:
                ts = i / fps if fps > 0 else 0.0
                writer.writerow([i, f"{ts:.6f}", "", "", "", ""])
```

- [ ] **Step 4: Run to pass**

```bash
pytest tests/test_exporter.py -v
```
Expected: All 3 pass

- [ ] **Step 5: Commit**

```bash
git add tracker/export/exporter.py tests/test_exporter.py
git commit -m "feat: add CSV export (standard + full)"
```

---

### Task 10: Data Table and Plot Panels

**Files:**
- Create: `tracker/panels/data_table.py`
- Create: `tracker/panels/plot_panel.py`

- [ ] **Step 1: Implement data table panel**

`tracker/panels/data_table.py`:

```python
from __future__ import annotations
from typing import Optional
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QVBoxLayout, QWidget, QLabel
from tracker.tracking.collector import TrackingCollector


class DataTablePanel(QWidget):
    COLUMNS = ["Frame", "Time (s)", "X", "Y", "Track ID"]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("<b>Data</b>"))
        self._table = QTableWidget(0, len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self._table)
        self._collector: Optional[TrackingCollector] = None

    def set_collector(self, collector: TrackingCollector):
        self._collector = collector

    @pyqtSlot()
    def refresh(self):
        if self._collector is None:
            return
        self._table.setRowCount(len(self._collector))
        for i, pt in enumerate(self._collector):
            self._table.setItem(i, 0, QTableWidgetItem(str(pt.frame)))
            self._table.setItem(i, 1, QTableWidgetItem(f"{pt.timestamp:.6f}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"{pt.x_world:.6f}"))
            self._table.setItem(i, 3, QTableWidgetItem(f"{pt.y_world:.6f}"))
            self._table.setItem(i, 4, QTableWidgetItem(pt.track_id))
        self._table.scrollToBottom()
```

- [ ] **Step 2: Implement plot panel**

`tracker/panels/plot_panel.py`:

```python
from __future__ import annotations
from typing import Optional
import numpy as np
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from tracker.tracking.collector import TrackingCollector


class PlotPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("X axis:"))
        self._x_combo = QComboBox()
        self._x_combo.addItems(["t (time)", "x", "y"])
        controls.addWidget(self._x_combo)
        controls.addWidget(QLabel("Y axis:"))
        self._y_combo = QComboBox()
        self._y_combo.addItems(["y", "x", "t (time)"])
        controls.addWidget(self._y_combo)
        layout.addLayout(controls)
        self._fig = Figure(figsize=(5, 4))
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)
        self._collector: Optional[TrackingCollector] = None
        self._x_combo.currentTextChanged.connect(self.refresh)
        self._y_combo.currentTextChanged.connect(self.refresh)

    def set_collector(self, collector: TrackingCollector):
        self._collector = collector

    def _get_values(self, key: str):
        if self._collector is None:
            return np.array([])
        if key == "t (time)":
            return np.array([pt.timestamp for pt in self._collector])
        return np.array([pt.x_world if key == "x" else pt.y_world for pt in self._collector])

    @pyqtSlot()
    def refresh(self):
        if self._collector is None or len(self._collector) == 0:
            return
        x = self._get_values(self._x_combo.currentText())
        y = self._get_values(self._y_combo.currentText())
        self._ax.clear()
        self._ax.plot(x, y, "r.-", markersize=3, linewidth=0.5)
        self._ax.set_xlabel(self._x_combo.currentText())
        self._ax.set_ylabel(self._y_combo.currentText())
        self._ax.grid(True, alpha=0.3)
        self._canvas.draw_idle()
```

- [ ] **Step 3: Commit**

```bash
git add tracker/panels/data_table.py tracker/panels/plot_panel.py
git commit -m "feat: add data table and plot panels"
```

---

### Task 11: Main Window

**Files:**
- Create: `tracker/window.py`

- [ ] **Step 1: Implement MainWindow**

`tracker/window.py`:

```python
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QMessageBox, QSplitter,
    QWidget, QVBoxLayout, QPushButton, QToolBar, QLabel,
    QTabWidget, QDoubleSpinBox, QFormLayout, QDialog, QDialogButtonBox,
)
from tracker.canvas.scene import TrackerScene
from tracker.canvas.view import TrackerView
from tracker.canvas.items import CalibrationStickItem, OriginGridItem
from tracker.video.decoder import VideoDecoder
from tracker.calibration.data import CalibrationData
from tracker.calibration.controller import CalibrationController
from tracker.calibration.persistence import CalibrationStore
from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.tracking.collector import TrackingCollector
from tracker.tracking.state import AppMode
from tracker.panels.data_table import DataTablePanel
from tracker.panels.plot_panel import PlotPanel
from tracker.export.exporter import Exporter


class LengthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration Length")
        layout = QFormLayout(self)
        self._spin = QDoubleSpinBox()
        self._spin.setRange(0.0001, 1000.0)
        self._spin.setValue(0.1)
        self._spin.setDecimals(6)
        self._spin.setSuffix(" m")
        layout.addRow("Known length:", self._spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def length(self) -> float:
        return self._spin.value()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker Replacement")
        self.resize(1400, 900)
        self._decoder = VideoDecoder(ring_buffer_size=30)
        self._cal_controller = CalibrationController()
        self._collector = TrackingCollector()
        self._exporter = Exporter()
        self._calibration: Optional[CalibrationData] = None
        self._pipeline: Optional[CoordinatePipeline] = None
        self._frame_index: int = 0
        self._video_path: Optional[Path] = None
        self._app_mode: AppMode = AppMode.IDLE
        self._scene = TrackerScene()
        self._view = TrackerView(self._scene)
        self._view.canvas_clicked.connect(self._on_canvas_clicked)
        self._data_table = DataTablePanel()
        self._data_table.set_collector(self._collector)
        self._plot_panel = PlotPanel()
        self._plot_panel.set_collector(self._collector)
        right_tabs = QTabWidget()
        right_tabs.addTab(self._data_table, "Table")
        right_tabs.addTab(self._plot_panel, "Plot")
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._view)
        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)
        self._setup_toolbar()
        self._setup_menus()
        self._update_ui_state()

    def _setup_menus(self):
        menu = self.menuBar().addMenu("File")
        act_import = QAction("Import Video...", self)
        act_import.setShortcut(QKeySequence.Open)
        act_import.triggered.connect(self._import_video)
        menu.addAction(act_import)
        act_exp = QAction("Export CSV (Standard)...", self)
        act_exp.setShortcut(QKeySequence("Ctrl+Shift+E"))
        act_exp.triggered.connect(lambda: self._do_export(standard=True))
        menu.addAction(act_exp)
        act_exp_full = QAction("Export CSV (Full)...", self)
        act_exp_full.triggered.connect(lambda: self._do_export(standard=False))
        menu.addAction(act_exp_full)
        menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.setShortcut(QKeySequence.Quit)
        act_exit.triggered.connect(self.close)
        menu.addAction(act_exit)

    def _setup_toolbar(self):
        tb = self.addToolBar("Tools")
        tb.setMovable(False)
        self._prev_btn = QPushButton("◀ Prev")
        self._prev_btn.clicked.connect(self._prev_frame)
        tb.addWidget(self._prev_btn)
        self._next_btn = QPushButton("Next ▶")
        self._next_btn.clicked.connect(self._next_frame)
        tb.addWidget(self._next_btn)
        tb.addSeparator()
        zin = QPushButton("Zoom +")
        zin.clicked.connect(lambda: self._view.scale(1.5, 1.5))
        tb.addWidget(zin)
        zout = QPushButton("Zoom -")
        zout.clicked.connect(lambda: self._view.scale(1 / 1.5, 1 / 1.5))
        tb.addWidget(zout)
        fit = QPushButton("Fit")
        fit.clicked.connect(self._view.fit_to_view)
        tb.addWidget(fit)
        tb.addSeparator()
        self._cal_btn = QPushButton("Calibrate Stick")
        self._cal_btn.clicked.connect(self._start_stick_calibration)
        tb.addWidget(self._cal_btn)
        self._origin_btn = QPushButton("Set Origin")
        self._origin_btn.clicked.connect(self._start_origin_calibration)
        tb.addWidget(self._origin_btn)
        tb.addSeparator()
        self._ts_btn = QPushButton("Hide Stick")
        self._ts_btn.setCheckable(True)
        self._ts_btn.setChecked(True)
        self._ts_btn.clicked.connect(self._toggle_stick)
        tb.addWidget(self._ts_btn)
        self._tg_btn = QPushButton("Hide Grid")
        self._tg_btn.setCheckable(True)
        self._tg_btn.setChecked(True)
        self._tg_btn.clicked.connect(self._toggle_grid)
        tb.addWidget(self._tg_btn)

    def _update_ui_state(self):
        has_vid = self._decoder.total_frames > 0
        has_cal = self._calibration is not None
        self._prev_btn.setEnabled(has_vid)
        self._next_btn.setEnabled(has_vid)
        self._cal_btn.setEnabled(has_vid)
        self._origin_btn.setEnabled(has_vid)
        self._ts_btn.setEnabled(has_cal)
        self._tg_btn.setEnabled(has_cal)

    def _import_video(self):
        path_str, _ = QFileDialog.getOpenFileName(self, "Import Video", "", "Video Files (*.mp4 *.MP4)")
        if not path_str:
            return
        path = Path(path_str)
        try:
            self._decoder.close()
            self._decoder.open(path)
        except (FileNotFoundError, RuntimeError) as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self._video_path = path
        self._frame_index = 0
        self._collector = TrackingCollector()
        self._data_table.set_collector(self._collector)
        self._plot_panel.set_collector(self._collector)
        self._app_mode = AppMode.TRACKING
        store = CalibrationStore(path.parent)
        cal = store.load(filename=path.with_suffix(".calibration.json").name)
        if cal is None and store.directory.exists():
            first_frame = self._decoder.get_frame(0)
            if first_frame is not None:
                cal = store.find_by_hash(path.parent, CalibrationStore.compute_frame0_hash(first_frame[0]))
        if cal is not None:
            self._apply_calibration(cal)
        self._show_current_frame()
        self._update_ui_state()
        self.statusBar().showMessage(f"Loaded: {path.name}  ({self._decoder.total_frames} fr @ {self._decoder.fps:.0f} fps)")

    def _show_current_frame(self):
        result = self._decoder.get_frame(self._frame_index)
        if result is None:
            return
        qimg, ts = result
        self._scene.set_background(QPixmap.fromImage(qimg))
        self._scene.frame_counter.update_info(self._decoder.fps, self._frame_index, self._decoder.total_frames, ts)
        self.setWindowTitle(f"Tracker — {self._video_path.name if self._video_path else ''}  Fr {self._frame_index + 1}/{self._decoder.total_frames}")

    def _next_frame(self):
        if self._frame_index < self._decoder.total_frames - 1:
            self._frame_index += 1
            self._show_current_frame()

    def _prev_frame(self):
        if self._frame_index > 0:
            self._frame_index -= 1
            self._show_current_frame()

    def _start_stick_calibration(self):
        dialog = LengthDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        self._cal_controller.start_stick_calibration(known_length=dialog.length)
        self._app_mode = AppMode.CALIBRATING_A
        self.statusBar().showMessage("Calibration: click first endpoint")

    def _start_origin_calibration(self):
        self._cal_controller.start_origin_calibration()
        self._app_mode = AppMode.SETTING_ORIGIN
        self.statusBar().showMessage("Origin: click to place origin")

    def _apply_calibration(self, cal: CalibrationData):
        self._calibration = cal
        self._pipeline = CoordinatePipeline(cal)
        if self._pipeline is not None and len(self._collector) > 0:
            self._collector.recompute_world_coords(self._pipeline.pixel_to_world)
        self._scene.set_calibration_stick(CalibrationStickItem(cal))
        self._scene.set_origin_grid(OriginGridItem(cal, self._pipeline))
        if self._video_path is not None:
            store = CalibrationStore(self._video_path.parent)
            store.save(cal, filename=self._video_path.with_suffix(".calibration.json").name)
        self._data_table.refresh()
        self._plot_panel.refresh()
        self._update_ui_state()
        self.statusBar().showMessage(f"Cal: {cal.known_length} {cal.known_unit} / {cal.pixel_distance:.0f} px")

    def _toggle_stick(self, visible: bool):
        self._scene.toggle_stick(visible)
        self._ts_btn.setText("Hide Stick" if visible else "Show Stick")

    def _toggle_grid(self, visible: bool):
        self._scene.toggle_grid(visible)
        self._tg_btn.setText("Hide Grid" if visible else "Show Grid")

    def _on_canvas_clicked(self, sx: float, sy: float):
        if self._app_mode in (AppMode.CALIBRATING_A, AppMode.CALIBRATING_B):
            result = self._cal_controller.handle_click(sx, sy)
            if result is not None:
                self._apply_calibration(result)
                self._app_mode = AppMode.TRACKING
                self.statusBar().showMessage("Tracking mode — click to mark points")
            else:
                self.statusBar().showMessage("Calibration: click second endpoint")
            return
        if self._app_mode == AppMode.SETTING_ORIGIN:
            self._cal_controller.handle_origin_click(sx, sy)
            base = self._calibration
            if base is not None:
                nc = CalibrationData(
                    stick_endpoint_a_px=base.stick_endpoint_a_px, stick_endpoint_b_px=base.stick_endpoint_b_px,
                    known_length=base.known_length, known_unit=base.known_unit,
                    origin_px=(sx, sy), axis_rotation_deg=base.axis_rotation_deg,
                    pixel_distance=base.pixel_distance, scale=base.scale,
                )
            else:
                nc = CalibrationData(
                    stick_endpoint_a_px=(0.0, 0.0), stick_endpoint_b_px=(1.0, 0.0),
                    known_length=1.0, known_unit="m", origin_px=(sx, sy),
                    axis_rotation_deg=0.0, pixel_distance=1.0, scale=1.0,
                )
            self._apply_calibration(nc)
            self._app_mode = AppMode.TRACKING
            self.statusBar().showMessage("Tracking mode — click to mark points")
            return
        if self._app_mode == AppMode.TRACKING and self._decoder.total_frames > 0:
            vs = self._view.get_view_scale()
            if self._pipeline is not None:
                wx, wy = self._pipeline.scene_to_world(sx, sy, vs)
            else:
                wx, wy = sx, sy
            result = self._decoder.get_frame(self._frame_index)
            ts = result[1] if result is not None else 0.0
            self._collector.record(self._frame_index, ts, wx, wy, sx / vs, sy / vs)
            self._scene.add_dot(sx / vs, sy / vs)
            QTimer.singleShot(0, self._data_table.refresh)
            QTimer.singleShot(0, self._plot_panel.refresh)
            if self._frame_index < self._decoder.total_frames - 1:
                self._frame_index += 1
                self._show_current_frame()

    def _do_export(self, standard: bool):
        if len(self._collector) == 0:
            QMessageBox.information(self, "Export", "No data to export.")
            return
        name = "export_standard.csv" if standard else "export_full.csv"
        path_str, _ = QFileDialog.getSaveFileName(self, "Export CSV", name, "CSV Files (*.csv)")
        if not path_str:
            return
        path = Path(path_str)
        vname = self._video_path.name if self._video_path else "unknown"
        try:
            with open(path, "w", newline="") as f:
                if standard:
                    self._exporter.export_standard(f, self._collector, self._calibration,
                                                   vname, self._decoder.fps, self._decoder.total_frames)
                else:
                    self._exporter.export_full(f, self._collector, self._calibration,
                                               vname, self._decoder.fps, self._decoder.total_frames)
            self.statusBar().showMessage(f"Exported: {path.name}")
        except OSError as e:
            QMessageBox.critical(self, "Export Error", str(e))
```

- [ ] **Step 2: Commit**

```bash
git add tracker/window.py
git commit -m "feat: add main window wiring all components"
```

---

### Task 12: Entry Point

**Files:**
- Create: `tracker/main.py`
- Create: `run.py`

- [ ] **Step 1: Create entry point files**

`tracker/main.py`:

```python
import sys
from PyQt5.QtWidgets import QApplication
from tracker.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Tracker Replacement")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
```

`run.py`:

```python
#!/usr/bin/env python3
from tracker.main import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it launches**

```bash
python run.py
```
Expected: Application window opens, toolbar visible, canvas + data panel layout correct.

- [ ] **Step 3: Commit**

```bash
git add tracker/main.py run.py
git commit -m "feat: add entry point"
```

---

### Self-Review Checklist

1. **Spec coverage:**
   - Video Import & Frame Navigation → Tasks 5, 7, 11
   - Calibration System → Tasks 1, 4, 6, 8
   - Point Tracking → Tasks 2, 3, 6, 11
   - Data View Panel → Task 10
   - Export → Task 9
   - Menu bar → Task 11
   - Stable zoom → Task 7
   - Calibration persistence → Task 4
   - Split-pane layout → Task 11
   - Retroactive recalculation → Task 11 (`_apply_calibration` calls `recompute_world_coords`)
   - AppMode enum → Task 1
   - Frame counter overlay → Task 6

2. **Placeholder check:** Every step has real code, exact file paths, and expected test outputs. No TBD/TODO/vague steps.

3. **Type consistency:** `CalibrationData.from_endpoints()`, `.to_dict()`, `.from_dict()`, `CoordinatePipeline.scene_to_world()`, `TrackingCollector.record()` use consistent signatures across all tasks.
