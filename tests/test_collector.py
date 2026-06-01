import pytest

from tracker.tracking.collector import TrackingCollector


def test_append_mark_uses_active_series():
    collector = TrackingCollector()
    mark = collector.append_mark(0, 0.0, 10.0, 20.0)
    assert mark.series_id == collector.active_series_id
    assert len(collector.marks) == 1


def test_multiple_series():
    collector = TrackingCollector()
    s2 = collector.add_series("B")
    collector.append_mark(0, 0.0, 1.0, 2.0, series_id=s2.id)
    assert len(collector.marks_for_series(s2.id)) == 1


def test_recompute_after_calibration_change():
    from tracker.calibration.data import CalibrationData
    from tracker.coordinates.pipeline import CoordinatePipeline

    collector = TrackingCollector()
    collector.append_mark(0, 0.0, 100.0, 50.0)
    pipeline = CoordinatePipeline()
    w1 = pipeline.pixel_to_world(100.0, 50.0)
    assert w1.x == 100.0

    cal = CalibrationData(
        stick_a_px=(0.0, 0.0),
        stick_b_px=(100.0, 0.0),
        known_length_cm=10.0,
        origin_px=(0.0, 0.0),
        scale_cm_per_px=0.1,
    )
    pipeline.set_calibration(cal)
    w2 = pipeline.pixel_to_world(100.0, 50.0)
    assert w2.x == pytest.approx(10.0)
    assert w2.y == pytest.approx(-5.0)
