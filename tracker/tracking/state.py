from enum import Enum


class AppMode(Enum):
    IDLE = "idle"
    CALIBRATING_A = "calibrating_a"
    CALIBRATING_B = "calibrating_b"
    SETTING_ORIGIN = "setting_origin"
    TRACKING = "tracking"
    EDITING = "editing"
