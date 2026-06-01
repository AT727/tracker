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


def test_from_endpoints_zero_length_raises():
    import pytest
    with pytest.raises(ValueError, match="identical"):
        CalibrationData.from_endpoints(
            endpoint_a=(100.0, 300.0),
            endpoint_b=(100.0, 300.0),
            known_length=0.1,
        )


def test_to_dict_from_dict_roundtrip():
    data = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(10.0, 20.0),
        axis_rotation_deg=45.0,
        pixel_distance=100.0,
        scale=0.01,
        video_frame0_hash="abc123",
    )
    d = data.to_dict()
    restored = CalibrationData.from_dict(d)
    assert restored.stick_endpoint_a_px == data.stick_endpoint_a_px
    assert restored.stick_endpoint_b_px == data.stick_endpoint_b_px
    assert restored.known_length == data.known_length
    assert restored.known_unit == data.known_unit
    assert restored.origin_px == data.origin_px
    assert restored.axis_rotation_deg == data.axis_rotation_deg
    assert restored.pixel_distance == data.pixel_distance
    assert restored.scale == data.scale
    assert restored.video_frame0_hash == data.video_frame0_hash


def test_is_valid_returns_false_for_zero_scale():
    data = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0,
        known_unit="m",
        origin_px=(0.0, 0.0),
        axis_rotation_deg=0.0,
        pixel_distance=100.0,
        scale=0.0,
    )
    assert not data.is_valid


def test_app_mode_values():
    assert AppMode.IDLE.value == "idle"
    assert AppMode.TRACKING.value == "tracking"
    assert AppMode.CALIBRATING_A.value == "calibrating_a"
    assert AppMode.CALIBRATING_B.value == "calibrating_b"
    assert AppMode.SETTING_ORIGIN.value == "setting_origin"
    assert AppMode.EDITING.value == "editing"


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
