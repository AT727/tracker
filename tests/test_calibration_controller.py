"""Tests for calibration controller draft/commit lifecycle."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tracker.calibration.controller import CalibrationController, CalibrationMode
from tracker.calibration.data import CalibrationData


@pytest.fixture
def controller() -> CalibrationController:
    return CalibrationController()


def test_draft_updates_do_not_advance_mode(controller: CalibrationController) -> None:
    controller.start_stick_calibration()
    assert controller.mode == CalibrationMode.STICK_A

    controller.begin_point()
    controller.update_draft(10.0, 20.0)
    assert controller.mode == CalibrationMode.STICK_A
    assert controller.draft == (10.0, 20.0)
    assert controller.data.stick_a_px is None


def test_commit_stick_a_advances_to_stick_b(controller: CalibrationController) -> None:
    controller.start_stick_calibration()
    controller.begin_point()
    controller.update_draft(10.0, 20.0)
    controller.commit_point(10.0, 20.0)

    assert controller.mode == CalibrationMode.STICK_B
    assert controller.data.stick_a_px == (10.0, 20.0)
    assert controller.draft is None


@patch("tracker.calibration.controller.QInputDialog.getDouble", return_value=(15.0, True))
def test_commit_stick_b_shows_dialog_and_advances(
    mock_dialog, controller: CalibrationController
) -> None:
    controller.start_stick_calibration()
    controller.commit_point(0.0, 0.0)
    controller.commit_point(100.0, 0.0)

    mock_dialog.assert_called_once()
    assert controller.mode == CalibrationMode.SET_ORIGIN
    assert controller.data.stick_b_px == (100.0, 0.0)
    assert controller.data.known_length_cm == 15.0


@patch("tracker.calibration.controller.QInputDialog.getDouble", return_value=(10.0, False))
def test_commit_stick_b_cancel_returns_to_stick_a(
    mock_dialog, controller: CalibrationController
) -> None:
    controller.start_stick_calibration()
    controller.commit_point(0.0, 0.0)
    controller.commit_point(100.0, 0.0)

    assert controller.mode == CalibrationMode.STICK_A
    assert controller.data.stick_b_px is None


def test_commit_origin_completes_calibration(controller: CalibrationController) -> None:
    data = CalibrationData(
        stick_a_px=(0.0, 0.0),
        stick_b_px=(100.0, 0.0),
        known_length_cm=10.0,
        scale_cm_per_px=0.1,
    )
    controller.set_data(data)
    controller.start_origin_calibration()
    controller.begin_point()
    controller.update_draft(50.0, 50.0)
    controller.commit_point(50.0, 50.0)

    assert controller.mode == CalibrationMode.NONE
    assert controller.data.origin_px == (50.0, 50.0)


def test_cancel_clears_draft(controller: CalibrationController) -> None:
    controller.start_stick_calibration()
    controller.begin_point()
    controller.update_draft(10.0, 20.0)
    controller.cancel()

    assert controller.mode == CalibrationMode.NONE
    assert controller.draft is None
    assert not controller.is_dragging
