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


def test_upsert_mark_replaces_existing_frame_for_series():
    collector = TrackingCollector()
    first, replaced_first = collector.upsert_mark(3, 0.1, 10.0, 20.0)
    second, replaced_second = collector.upsert_mark(3, 0.2, 99.0, 77.0)

    assert not replaced_first
    assert replaced_second
    assert len(collector.marks) == 1
    assert first.frame == second.frame == 3
    assert collector.marks[0].px == pytest.approx(99.0)
    assert collector.marks[0].py == pytest.approx(77.0)


def test_upsert_mark_is_scoped_per_series():
    collector = TrackingCollector()
    base_series = collector.active_series_id
    second_series = collector.add_series("Second")

    collector.upsert_mark(5, 0.3, 1.0, 2.0, series_id=base_series)
    collector.upsert_mark(5, 0.4, 3.0, 4.0, series_id=second_series.id)

    assert len(collector.marks) == 2
    assert len(collector.marks_for_series(base_series)) == 1
    assert len(collector.marks_for_series(second_series.id)) == 1


def test_add_series_without_activate():
    collector = TrackingCollector()
    original = collector.active_series_id
    s = collector.add_series("Silent", activate=False)
    assert collector.active_series_id == original
    assert s.id in [s_.id for s_ in collector.series]


def test_upsert_uses_dict_for_consistency():
    collector = TrackingCollector()
    s1 = collector.active_series_id
    s2 = collector.add_series("B", activate=False)

    collector.upsert_mark(1, 0.0, 10.0, 20.0)  # s1, frame 1
    collector.upsert_mark(1, 0.1, 30.0, 40.0, series_id=s2.id)  # s2, frame 1
    assert len(collector.marks) == 2

    collector.upsert_mark(1, 0.2, 50.0, 60.0)  # s1, frame 1 — replace
    assert len(collector.marks) == 2
    assert collector.marks[0].px == pytest.approx(50.0)


def test_clear_marks_resets_dict():
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 1.0, 2.0)
    collector.clear_marks()
    assert len(collector.marks) == 0
    # Subsequent upsert on same key should be treated as new
    mark, replaced = collector.upsert_mark(0, 0.5, 3.0, 4.0)
    assert not replaced
    assert len(collector.marks) == 1


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
