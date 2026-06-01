import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from tracker.calibration.data import CalibrationData
from tracker.calibration.persistence import CalibrationStore


def _make_test_video(tmp_path: Path, filename: str = "test_video.mp4") -> Path:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[30:70, 30:70] = [255, 0, 0]
    video_path = tmp_path / filename
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (100, 100))
    out.write(frame)
    out.release()
    return video_path


def _frame_hash(frame: np.ndarray) -> str:
    return hashlib.sha256(cv2.imencode(".png", frame)[1].tobytes()).hexdigest()


def test_save_creates_json_file(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
    )
    saved_path = store.save("video.mp4", cal)

    assert Path(saved_path).parent == tmp_path
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) == 1
    assert Path(saved_path).exists()


def test_save_and_load_roundtrip(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
    )
    saved_path = store.save("video.mp4", cal)

    with open(saved_path) as f:
        data = json.load(f)

    assert "metadata" in data
    assert data["metadata"]["video_filename"] == "video.mp4"
    assert "timestamp" in data["metadata"]

    restored = CalibrationData.from_dict(data)
    assert restored == cal


def test_find_matching_by_hash(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))

    video_path = _make_test_video(tmp_path)
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()
    assert ret

    expected_hash = _frame_hash(frame)

    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
        video_frame0_hash=expected_hash,
    )
    store.save("test_video.mp4", cal)

    result = store.find_matching(str(video_path))
    assert result is not None
    assert result.video_frame0_hash == expected_hash
    assert result.scale == 0.01


def test_find_matching_fallback_by_filename(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))

    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
        video_frame0_hash="",
    )
    store.save("my_video.mp4", cal)

    video_path = _make_test_video(tmp_path, "my_video.mp4")

    result = store.find_matching(str(video_path))
    assert result is not None
    assert result.video_frame0_hash == ""
    assert result.scale == 0.01


def test_find_matching_no_match_returns_none(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))

    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
        video_frame0_hash="some_hash",
    )
    store.save("other.mp4", cal)

    video_path = _make_test_video(tmp_path, "unrelated.mp4")

    result = store.find_matching(str(video_path))
    assert result is None


def test_list_available_empty(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))
    assert store.list_available() == []


def test_list_available_with_entries(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
    )
    store.save("video.mp4", cal)

    entries = store.list_available()
    assert len(entries) == 1
    assert entries[0]["video_filename"] == "video.mp4"
    assert "timestamp" in entries[0]
    assert "filename" in entries[0]


def test_delete_existing(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.01,
    )
    saved_path = store.save("video.mp4", cal)
    cal_id = Path(saved_path).stem

    assert store.delete(cal_id) is True
    assert list(tmp_path.glob("*.json")) == []


def test_delete_nonexistent(tmp_path):
    store = CalibrationStore(directory=str(tmp_path))
    assert store.delete("nonexistent") is False
