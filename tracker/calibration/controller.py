from dataclasses import replace
from typing import Optional

import numpy as np
from PyQt5.QtCore import QObject, QPointF, pyqtSignal

from tracker.calibration.data import CalibrationData
from tracker.calibration.persistence import CalibrationStore
from tracker.tracking.state import AppMode


class CalibrationController(QObject):
    mode_changed = pyqtSignal(AppMode)
    endpoint_a_selected = pyqtSignal(object)
    endpoint_b_selected = pyqtSignal(object)
    calibration_complete = pyqtSignal(CalibrationData)
    origin_set = pyqtSignal(object)
    status_message = pyqtSignal(str)

    def __init__(self, store: Optional[CalibrationStore] = None, parent=None):
        super().__init__(parent)
        self._mode = AppMode.IDLE
        self._endpoint_a: Optional[QPointF] = None
        self._endpoint_b: Optional[QPointF] = None
        self._scale: Optional[float] = None
        self._use_stored_calibration = False
        self._store = store or CalibrationStore()
        self._calibration: Optional[CalibrationData] = None

    @property
    def mode(self) -> AppMode:
        return self._mode

    def set_mode_transition(self, new_mode: AppMode):
        if new_mode == AppMode.IDLE:
            self._reset()
        self._mode = new_mode
        self.mode_changed.emit(new_mode)

    def on_canvas_click(self, scene_pos):
        x, y = scene_pos.x(), scene_pos.y()

        if self._mode == AppMode.CALIBRATING_A:
            self._endpoint_a = QPointF(x, y)
            self.set_mode_transition(AppMode.CALIBRATING_B)
            self.endpoint_a_selected.emit(self._endpoint_a)
            self.status_message.emit("Point A set. Click to set point B.")

        elif self._mode == AppMode.CALIBRATING_B:
            if self._endpoint_a and QPointF(x, y) == self._endpoint_a:
                self.status_message.emit("Point B must differ from point A.")
                return
            self._endpoint_b = QPointF(x, y)
            self.endpoint_b_selected.emit(self._endpoint_b)
            pixel_dist = np.sqrt(
                (x - self._endpoint_a.x()) ** 2 + (y - self._endpoint_a.y()) ** 2
            )
            self._pixel_distance = pixel_dist
            self.status_message.emit(f"Points set. Distance: {pixel_dist:.1f} px. Enter known length.")

        elif self._mode == AppMode.SETTING_ORIGIN:
            self._origin = QPointF(x, y)
            self.origin_set.emit(self._origin)
            if self._calibration is not None:
                self._calibration = replace(self._calibration, origin_px=(x, y))
            self.set_mode_transition(AppMode.TRACKING)
            self.status_message.emit("Origin set. Ready to track.")

    def on_set_known_length(self, length: float, unit: str = "m"):
        if self._mode != AppMode.CALIBRATING_B:
            return
        if length <= 0:
            self.status_message.emit("Length must be positive.")
            return
        if self._endpoint_a is None or self._endpoint_b is None:
            return

        try:
            calibration = CalibrationData.from_endpoints(
                endpoint_a=(self._endpoint_a.x(), self._endpoint_a.y()),
                endpoint_b=(self._endpoint_b.x(), self._endpoint_b.y()),
                known_length=length,
                unit=unit,
            )
        except (ValueError, ZeroDivisionError) as e:
            self.status_message.emit(str(e))
            return

        self._calibration = calibration
        self.calibration_complete.emit(calibration)
        self.set_mode_transition(AppMode.SETTING_ORIGIN)
        self.status_message.emit(
            f"Calibration: {calibration.scale:.6f} {unit}/px. "
            f"Click to set origin."
        )

    def load_calibration(self, calibration: CalibrationData, video_path: str):
        self._calibration = calibration
        self._use_stored_calibration = True
        self.calibration_complete.emit(calibration)
        self.set_mode_transition(AppMode.SETTING_ORIGIN)
        self.status_message.emit(
            f"Loaded calibration (scale: {calibration.scale:.6f}). Click to set origin."
        )

    def save_current(self, video_path: str) -> Optional[str]:
        if self._calibration is None:
            self.status_message.emit("No calibration to save.")
            return None
        path = self._store.save(video_path, self._calibration)
        self.status_message.emit(f"Calibration saved: {path}")
        return path

    def try_auto_load(self, video_path: str) -> bool:
        cal = self._store.find_matching(video_path)
        if cal is not None:
            self.load_calibration(cal, video_path)
            return True
        return False

    def _reset(self):
        self._endpoint_a = None
        self._endpoint_b = None
        self._calibration = None
        self._use_stored_calibration = False
        self._mode = AppMode.IDLE
