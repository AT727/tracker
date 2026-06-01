import numpy as np
import pytest
from PyQt5.QtGui import QImage


@pytest.fixture
def sample_qimage():
    """A 640x480 test image with a gradient pattern."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    arr[:, :, 0] = np.linspace(0, 255, 640, dtype=np.uint8)
    arr[:, :, 1] = np.linspace(0, 255, 480, dtype=np.uint8)[:, np.newaxis]
    return QImage(arr.data, 640, 480, QImage.Format_RGB888)


@pytest.fixture
def sample_calibration_data():
    from tracker.calibration.data import CalibrationData
    return CalibrationData(
        stick_endpoint_a_px=(100.0, 300.0),
        stick_endpoint_b_px=(500.0, 300.0),
        known_length=0.1,
        known_unit="m",
        origin_px=(320.0, 240.0),
        axis_rotation_deg=0.0,
        pixel_distance=400.0,
        scale=0.00025,
    )
