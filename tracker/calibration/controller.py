"""Calibration finite state machine."""

from __future__ import annotations

from enum import Enum, auto
from typing import Callable

from PyQt5.QtWidgets import QInputDialog

from tracker.calibration.data import CalibrationData


class CalibrationMode(Enum):
    NONE = auto()
    STICK_A = auto()
    STICK_B = auto()
    SET_ORIGIN = auto()


class CalibrationController:
    """FSM: NONE → STICK_A → STICK_B → SET_ORIGIN → NONE."""
    def __init__(
        self,
        on_changed: Callable[[CalibrationData], None] | None = None,
        on_mode_changed: Callable[[CalibrationMode], None] | None = None,
    ) -> None:
        self._data = CalibrationData()
        self._mode = CalibrationMode.NONE
        self._on_changed = on_changed
        self._on_mode_changed = on_mode_changed
        self._draft: tuple[float, float] | None = None
        self._dragging = False

    @property
    def data(self) -> CalibrationData:
        return self._data

    @property
    def mode(self) -> CalibrationMode:
        return self._mode

    @property
    def draft(self) -> tuple[float, float] | None:
        return self._draft

    @property
    def is_dragging(self) -> bool:
        return self._dragging

    def set_data(self, data: CalibrationData) -> None:
        self._data = data
        self._draft = None
        self._dragging = False
        self._notify_changed()

    def start_stick_calibration(self) -> None:
        self._data.stick_a_px = None
        self._data.stick_b_px = None
        self._draft = None
        self._dragging = False
        self._set_mode(CalibrationMode.STICK_A)

    def start_origin_calibration(self) -> None:
        self._draft = None
        self._dragging = False
        self._set_mode(CalibrationMode.SET_ORIGIN)

    def cancel(self) -> None:
        self._draft = None
        self._dragging = False
        self._set_mode(CalibrationMode.NONE)

    def begin_point(self) -> bool:
        """Start placing a calibration point. Returns True if consumed."""
        if self._mode == CalibrationMode.NONE:
            return False
        self._dragging = True
        self._draft = None
        return True

    def update_draft(self, px: float, py: float) -> bool:
        """Update draft position while dragging. Returns True if consumed."""
        if not self._dragging or self._mode == CalibrationMode.NONE:
            return False
        self._draft = (px, py)
        self._notify_changed()
        return True

    def commit_point(self, px: float, py: float, parent_widget=None) -> bool:
        """Commit calibration point on release. Returns True if consumed.

        Note: The QInputDialog.getDouble call for length (STICK_B path) is a
        synchronous modal dialog. Qt re-enters the event loop while it is
        shown, so mouse-release processing pauses but the UI stays responsive.
        This is acceptable for the current drag-and-drop calibration flow.
        """
        if self._mode == CalibrationMode.NONE:
            return False
        self._dragging = False
        self._draft = None

        if self._mode == CalibrationMode.STICK_A:
            self._data.stick_a_px = (px, py)
            self._set_mode(CalibrationMode.STICK_B)
            self._notify_changed()
            return True
        if self._mode == CalibrationMode.STICK_B:
            self._data.stick_b_px = (px, py)
            self._notify_changed()
            length, ok = QInputDialog.getDouble(
                parent_widget,
                "Known Length",
                "Tape measure length (cm):",
                10.0,
                0.01,
                10000.0,
                2,
            )
            if not ok:
                self._data.stick_b_px = None
                self._set_mode(CalibrationMode.STICK_A)
                self._notify_changed()
                return True
            self._data.known_length_cm = length
            self._data.compute_scale()
            self._set_mode(CalibrationMode.SET_ORIGIN)
            self._notify_changed()
            return True
        if self._mode == CalibrationMode.SET_ORIGIN:
            self._data.origin_px = (px, py)
            self._set_mode(CalibrationMode.NONE)
            self._notify_changed()
            return True
        return False

    def handle_click(self, px: float, py: float, parent_widget=None) -> bool:
        """Legacy single-click path; delegates to commit for compatibility."""
        if self._mode == CalibrationMode.NONE:
            return False
        return self.commit_point(px, py, parent_widget)

    def _set_mode(self, mode: CalibrationMode) -> None:
        self._mode = mode
        if self._on_mode_changed:
            self._on_mode_changed(mode)

    def _notify_changed(self) -> None:
        if self._on_changed:
            self._on_changed(self._data)
