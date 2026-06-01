import csv
from pathlib import Path
import pytest
from tracker.export.csv_writer import CsvExporter
from tracker.tracking.collector import TrackingCollector
from tracker.calibration.data import CalibrationData

SAMPLE_COLS = ["frame", "timestamp", "x_pixel", "y_pixel", "x_world", "y_world", "track_id", "is_interpolated"]

def make_collector():
    c = TrackingCollector()
    c.record(0, 0.0, 1.0, 2.0, 100.0, 200.0)
    c.record(2, 0.016, 3.0, 4.0, 150.0, 250.0)
    return c

def test_standard_csv_contains_tracked_only(tmp_path):
    collector = make_collector()
    exporter = CsvExporter("video.mp4", 128.0, 10, collector=collector)
    out = tmp_path / "output.csv"
    exporter.write_standard(str(out))
    lines = out.read_text().splitlines()
    data_lines = [l for l in lines if not l.startswith("#")]
    assert len(data_lines) == 3  # header + 2 data rows

def test_full_csv_contains_all_frames(tmp_path):
    collector = make_collector()
    exporter = CsvExporter("video.mp4", 128.0, 10, collector=collector)
    out = tmp_path / "output.csv"
    exporter.write_full(str(out))
    lines = out.read_text().splitlines()
    data_lines = [l for l in lines if not l.startswith("#")]
    assert len(data_lines) == 11  # header + 10 data rows

def test_metadata_contains_video_info(tmp_path):
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0,0.0), stick_endpoint_b_px=(100.0,0.0),
        known_length=1.0, known_unit="m",
        origin_px=(0.0,0.0), axis_rotation_deg=0.0,
        pixel_distance=100.0, scale=0.01,
    )
    exporter = CsvExporter("test.mp4", 128.0, 100, calibration=cal)
    out = tmp_path / "output.csv"
    exporter.write_standard(str(out))
    text = out.read_text()
    assert "Video: test.mp4" in text
    assert "scale=0.01" in text

def test_standard_csv_empty_collector(tmp_path):
    exporter = CsvExporter("video.mp4", 128.0, 10)
    out = tmp_path / "output.csv"
    exporter.write_standard(str(out))
    lines = out.read_text().splitlines()
    assert len([l for l in lines if not l.startswith("#")]) == 1  # header only
