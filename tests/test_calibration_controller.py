import pytest
from PyQt5.QtCore import QPointF
from tracker.calibration.controller import CalibrationController
from tracker.calibration.data import CalibrationData
from tracker.tracking.state import AppMode


def test_controller_starts_idle():
    ctrl = CalibrationController()
    assert ctrl.mode == AppMode.IDLE


def test_click_in_calibrating_a_sets_endpoint(qtbot):
    ctrl = CalibrationController()
    with qtbot.waitSignal(ctrl.endpoint_a_selected, timeout=500):
        ctrl.set_mode_transition(AppMode.CALIBRATING_A)
        ctrl.on_canvas_click(QPointF(100.0, 200.0))
    assert ctrl.mode == AppMode.CALIBRATING_B


def test_click_in_calibrating_b_sets_endpoint(qtbot):
    ctrl = CalibrationController()
    ctrl.set_mode_transition(AppMode.CALIBRATING_A)
    ctrl.on_canvas_click(QPointF(100.0, 200.0))
    with qtbot.waitSignal(ctrl.endpoint_b_selected, timeout=500):
        ctrl.on_canvas_click(QPointF(200.0, 100.0))


def test_set_known_length_creates_calibration(qtbot):
    ctrl = CalibrationController()
    ctrl.set_mode_transition(AppMode.CALIBRATING_A)
    ctrl.on_canvas_click(QPointF(0.0, 0.0))
    ctrl.on_canvas_click(QPointF(100.0, 0.0))
    with qtbot.waitSignal(ctrl.calibration_complete, timeout=500):
        ctrl.on_set_known_length(1.0, "m")
    assert ctrl._calibration is not None
    assert ctrl._calibration.scale == pytest.approx(0.01)


def test_set_known_length_rejects_zero(qtbot):
    ctrl = CalibrationController()
    ctrl.set_mode_transition(AppMode.CALIBRATING_A)
    ctrl.on_canvas_click(QPointF(0.0, 0.0))
    ctrl.on_canvas_click(QPointF(100.0, 0.0))
    ctrl.on_set_known_length(0.0, "m")
    assert ctrl._calibration is None


def test_set_known_length_rejects_identical_points(qtbot):
    ctrl = CalibrationController()
    ctrl.set_mode_transition(AppMode.CALIBRATING_A)
    ctrl.on_canvas_click(QPointF(100.0, 200.0))
    ctrl.on_canvas_click(QPointF(100.0, 200.0))
    assert ctrl.mode == AppMode.CALIBRATING_B


def test_set_origin_transitions_to_tracking(qtbot):
    ctrl = CalibrationController()
    ctrl.set_mode_transition(AppMode.CALIBRATING_A)
    ctrl.on_canvas_click(QPointF(0.0, 0.0))
    ctrl.on_canvas_click(QPointF(100.0, 0.0))
    ctrl.on_set_known_length(1.0, "m")
    with qtbot.waitSignal(ctrl.origin_set, timeout=500):
        ctrl.on_canvas_click(QPointF(50.0, 0.0))
    assert ctrl.mode == AppMode.TRACKING


def test_reset_returns_to_idle():
    ctrl = CalibrationController()
    ctrl.set_mode_transition(AppMode.CALIBRATING_A)
    ctrl.set_mode_transition(AppMode.IDLE)
    assert ctrl.mode == AppMode.IDLE
    assert ctrl._endpoint_a is None


def test_load_calibration(qtbot):
    ctrl = CalibrationController()
    cal = CalibrationData(
        stick_endpoint_a_px=(0.0, 0.0),
        stick_endpoint_b_px=(100.0, 0.0),
        known_length=1.0, known_unit="m",
        origin_px=(0.0, 0.0), axis_rotation_deg=0.0,
        pixel_distance=100.0, scale=0.01,
    )
    ctrl.load_calibration(cal, "video.mp4")
    assert ctrl._calibration is not None
    assert ctrl.mode == AppMode.SETTING_ORIGIN
