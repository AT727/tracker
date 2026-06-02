import csv
import io

import pytest

from tracker.calibration.data import CalibrationData
from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.export.csv_writer import export_csv
from tracker.mutations.models import ColumnMutation
from tracker.tracking.collector import TrackingCollector


def _calibrated_pipeline() -> CoordinatePipeline:
    cal = CalibrationData(
        stick_a_px=(0.0, 100.0),
        stick_b_px=(100.0, 100.0),
        known_length_cm=50.0,
        origin_px=(50.0, 50.0),
        scale_cm_per_px=0.5,
    )
    pipeline = CoordinatePipeline(cal)
    return pipeline


def _collector_with_marks() -> TrackingCollector:
    c = TrackingCollector()
    c.upsert_mark(0, 0.0, 10.0, 10.0)
    c.upsert_mark(1, 1.0, 20.0, 30.0)
    return c


def test_export_csv_without_mutations(tmp_path):
    path = tmp_path / "out.csv"
    collector = _collector_with_marks()
    pipeline = _calibrated_pipeline()

    export_csv(path, collector, pipeline)

    lines = path.read_text(encoding="utf-8").splitlines()
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)
    assert rows[0] == ["frame", "t (s)", "x (cm)", "y (cm)"]
    assert rows[1][0] == "1"
    assert rows[2][0] == "2"


def test_export_csv_appends_mutation_columns(tmp_path):
    path = tmp_path / "out.csv"
    collector = _collector_with_marks()
    pipeline = _calibrated_pipeline()

    mutations = [
        ColumnMutation("norm_x", "x * 2"),
        ColumnMutation("offset_y", "y + 1"),
    ]
    export_csv(path, collector, pipeline, mutations=mutations)

    lines = path.read_text(encoding="utf-8").splitlines()
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)
    assert rows[0] == ["frame", "t (s)", "x (cm)", "y (cm)", "norm_x", "offset_y"]


def test_export_csv_computes_mutation_values(tmp_path):
    path = tmp_path / "out.csv"
    collector = _collector_with_marks()
    pipeline = _calibrated_pipeline()

    mutations = [
        ColumnMutation("sum", "x + y"),
    ]
    export_csv(path, collector, pipeline, mutations=mutations)

    lines = path.read_text(encoding="utf-8").splitlines()
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)

    mark1 = collector.marks[0]
    w1 = pipeline.pixel_to_world(mark1.px, mark1.py)
    expected1 = w1.x + w1.y
    assert float(rows[1][4]) == pytest.approx(expected1)

    mark2 = collector.marks[1]
    w2 = pipeline.pixel_to_world(mark2.px, mark2.py)
    expected2 = w2.x + w2.y
    assert float(rows[2][4]) == pytest.approx(expected2)
