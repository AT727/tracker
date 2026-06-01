from __future__ import annotations

from PyQt5.QtCore import Qt

from tracker.app.autoclicker import AutoClickerConfigDialog, AutoClickerController
from tracker.app.main_window import MainWindow


def test_controller_hold_emits_clicks_and_release_stops(qtbot) -> None:
    controller = AutoClickerController()
    controller.set_mapping({Qt.Key_1: 20})
    controller.set_enabled(True)

    ticks: list[int] = []
    controller.click_requested.connect(lambda: ticks.append(1))
    controller.handle_key_press(Qt.Key_1, is_auto_repeat=False)

    qtbot.wait(140)
    assert len(ticks) >= 2

    clicks_on_release = len(ticks)
    controller.handle_key_release(Qt.Key_1, is_auto_repeat=False)
    qtbot.wait(90)
    assert len(ticks) == clicks_on_release


def test_controller_disable_stops_active_clicks(qtbot) -> None:
    controller = AutoClickerController()
    controller.set_mapping({Qt.Key_2: 25})
    controller.set_enabled(True)

    ticks: list[int] = []
    controller.click_requested.connect(lambda: ticks.append(1))
    controller.handle_key_press(Qt.Key_2, is_auto_repeat=False)
    qtbot.wait(110)
    assert ticks

    prior = len(ticks)
    controller.set_enabled(False)
    qtbot.wait(100)
    assert len(ticks) == prior


def test_config_dialog_rejects_duplicate_keys() -> None:
    dialog = AutoClickerConfigDialog({Qt.Key_1: 5, Qt.Key_2: 10})
    assert len(dialog._rows) == 2  # noqa: SLF001 - test-only introspection

    row_a = dialog._rows[0]  # noqa: SLF001 - test-only introspection
    row_b = dialog._rows[1]  # noqa: SLF001 - test-only introspection
    row_b.key_combo.setCurrentIndex(row_b.key_combo.findData(Qt.Key_1))

    assert dialog.mapping() is None


def test_main_window_menu_toggle_updates_autoclicker(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert not window._autoclicker.enabled  # noqa: SLF001 - verification of wiring
    assert window._autoclicker_enabled_action is not None  # noqa: SLF001

    window._autoclicker_enabled_action.setChecked(True)  # noqa: SLF001
    assert window._autoclicker.enabled  # noqa: SLF001

    window._autoclicker_enabled_action.setChecked(False)  # noqa: SLF001
    assert not window._autoclicker.enabled  # noqa: SLF001
