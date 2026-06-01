import pytest
from PyQt5.QtCore import Qt
from tracker.app.main_window import MainWindow


def test_main_window_creation(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "Tracker"
    assert window._view is not None


def test_main_window_has_menu(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    menubar = window.menuBar()
    actions = [a.text() for a in menubar.actions()]
    assert any("File" in a for a in actions)
    assert any("View" in a for a in actions)


def test_main_window_initial_state(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window._current_frame == 0
    assert window._collector is not None
    assert window._data_table is not None
    assert window._plot_panel is not None


def test_main_window_keyboard_navigation_not_crash(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.keyPressEvent(
        type('evt', (), {'key': lambda self=0: Qt.Key_Right, 'isAccepted': lambda: False})()
    )
    assert True
