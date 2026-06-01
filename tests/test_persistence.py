import json
from unittest.mock import patch

from tracker.calibration.data import CalibrationData
from tracker.calibration.persistence import (
    CalibrationStore,
    preset_path,
    sidecar_path_for_video,
)


def test_sidecar_path():
    assert sidecar_path_for_video("/videos/run.mp4").name == "run.json"


def test_preset_path():
    p = preset_path()
    assert p.name == "calibration_preset.json"
    assert ".tracker" in p.parts


def test_preset_save_load_clear(tmp_path):
    cal = CalibrationData(
        stick_a_px=(1.0, 2.0),
        stick_b_px=(3.0, 4.0),
        known_length_cm=10.0,
        origin_px=(5.0, 6.0),
        scale_cm_per_px=0.05,
    )
    with patch("tracker.calibration.persistence.preset_path", return_value=tmp_path / "preset.json"):
        assert CalibrationStore.load_preset() is None
        CalibrationStore.save_preset(cal)
        loaded = CalibrationStore.load_preset()
        assert loaded is not None
        assert loaded.stick_a_px == (1.0, 2.0)
        assert loaded.scale_cm_per_px == 0.05
        CalibrationStore.clear_preset()
        assert CalibrationStore.load_preset() is None


def test_round_trip(tmp_path):
    path = tmp_path / "experiment.json"
    cal = CalibrationData(
        stick_a_px=(1.0, 2.0),
        stick_b_px=(3.0, 4.0),
        known_length_cm=10.0,
        origin_px=(5.0, 6.0),
        scale_cm_per_px=0.05,
    )
    CalibrationStore.save(path, cal)
    loaded = CalibrationStore.load(path)
    assert loaded is not None
    assert loaded.stick_a_px == (1.0, 2.0)
    assert loaded.origin_px == (5.0, 6.0)
    assert loaded.scale_cm_per_px == 0.05

    with path.open() as f:
        data = json.load(f)
    assert "stick_a_px" in data
