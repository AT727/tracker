import pytest

from tracker.calibration.data import CalibrationData
from tracker.coordinates.pipeline import CoordinatePipeline


def test_uncalibrated_returns_pixels():
    pipeline = CoordinatePipeline()
    world = pipeline.pixel_to_world(100.0, 200.0)
    assert world.x == 100.0
    assert world.y == 200.0
    assert not world.calibrated
    assert pipeline.unit_suffix == "(px)"


def test_calibrated_origin_and_y_flip():
    cal = CalibrationData(
        stick_a_px=(0.0, 0.0),
        stick_b_px=(100.0, 0.0),
        known_length_cm=10.0,
        origin_px=(50.0, 50.0),
        scale_cm_per_px=0.1,
    )
    pipeline = CoordinatePipeline(cal)
    world = pipeline.pixel_to_world(60.0, 40.0)
    assert world.calibrated
    assert world.x == pytest.approx(1.0)
    assert world.y == pytest.approx(1.0)


def test_compute_scale_from_stick():
    cal = CalibrationData(
        stick_a_px=(0.0, 0.0),
        stick_b_px=(200.0, 0.0),
        known_length_cm=20.0,
        origin_px=(0.0, 0.0),
    )
    cal.compute_scale()
    assert cal.scale_cm_per_px == pytest.approx(0.1)
