"""In-window autoclicker runtime and configuration dialog."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


DEFAULT_KEY_CPS: dict[int, int] = {
    Qt.Key_1: 5,
    Qt.Key_2: 10,
    Qt.Key_3: 30,
}

_KEY_OPTIONS: list[tuple[str, int]] = [
    ("1", Qt.Key_1),
    ("2", Qt.Key_2),
    ("3", Qt.Key_3),
    ("4", Qt.Key_4),
    ("5", Qt.Key_5),
    ("6", Qt.Key_6),
    ("7", Qt.Key_7),
    ("8", Qt.Key_8),
    ("9", Qt.Key_9),
    ("0", Qt.Key_0),
    ("A", Qt.Key_A),
    ("B", Qt.Key_B),
    ("C", Qt.Key_C),
    ("D", Qt.Key_D),
    ("E", Qt.Key_E),
    ("F", Qt.Key_F),
    ("G", Qt.Key_G),
    ("H", Qt.Key_H),
    ("I", Qt.Key_I),
    ("J", Qt.Key_J),
    ("K", Qt.Key_K),
    ("L", Qt.Key_L),
    ("M", Qt.Key_M),
    ("N", Qt.Key_N),
    ("O", Qt.Key_O),
    ("P", Qt.Key_P),
    ("Q", Qt.Key_Q),
    ("R", Qt.Key_R),
    ("S", Qt.Key_S),
    ("T", Qt.Key_T),
    ("U", Qt.Key_U),
    ("V", Qt.Key_V),
    ("W", Qt.Key_W),
    ("X", Qt.Key_X),
    ("Y", Qt.Key_Y),
    ("Z", Qt.Key_Z),
]

KEY_LABELS: dict[int, str] = {code: label for label, code in _KEY_OPTIONS}


class AutoClickerController(QObject):
    """Tracks held keys and emits click ticks at configured CPS."""

    click_requested = pyqtSignal()
    enabled_changed = pyqtSignal(bool)
    mapping_changed = pyqtSignal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._enabled = True
        self._mapping: dict[int, int] = dict(DEFAULT_KEY_CPS)
        self._timers: dict[int, QTimer] = {}
        self._held_keys: set[int] = set()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def mapping(self) -> dict[int, int]:
        return dict(self._mapping)

    def set_enabled(self, enabled: bool) -> None:
        if self._enabled == enabled:
            return
        self._enabled = enabled
        if not enabled:
            self.release_all_keys()
        else:
            for key in list(self._held_keys):
                self._start_timer_for_key(key)
        self.enabled_changed.emit(enabled)

    def set_mapping(self, mapping: dict[int, int]) -> None:
        cleaned: dict[int, int] = {}
        for key, cps in mapping.items():
            if cps > 0:
                cleaned[int(key)] = int(cps)
        self._mapping = cleaned
        for key in list(self._timers):
            self._stop_timer_for_key(key)
        if self._enabled:
            for key in list(self._held_keys):
                self._start_timer_for_key(key)
        self.mapping_changed.emit(self.mapping)

    def handle_key_press(self, key: int, is_auto_repeat: bool = False) -> None:
        if is_auto_repeat:
            return
        self._held_keys.add(key)
        if self._enabled:
            self._start_timer_for_key(key)

    def handle_key_release(self, key: int, is_auto_repeat: bool = False) -> None:
        if is_auto_repeat:
            return
        self._held_keys.discard(key)
        self._stop_timer_for_key(key)

    def release_all_keys(self) -> None:
        self._held_keys.clear()
        for key in list(self._timers):
            self._stop_timer_for_key(key)

    def _start_timer_for_key(self, key: int) -> None:
        cps = self._mapping.get(key)
        if cps is None:
            return
        timer = self._timers.get(key)
        if timer is None:
            timer = QTimer(self)
            timer.setTimerType(Qt.PreciseTimer)
            timer.timeout.connect(self.click_requested.emit)
            self._timers[key] = timer
        interval_ms = max(1, int(round(1000.0 / float(cps))))
        timer.setInterval(interval_ms)
        if not timer.isActive():
            timer.start()

    def _stop_timer_for_key(self, key: int) -> None:
        timer = self._timers.pop(key, None)
        if timer is None:
            return
        timer.stop()
        timer.deleteLater()


@dataclass(frozen=True)
class _MappingRow:
    container: QWidget
    key_combo: QComboBox
    cps_spin: QSpinBox
    remove_btn: QPushButton


class AutoClickerConfigDialog(QDialog):
    """Simple key/CPS editor for autoclicker mappings."""

    def __init__(self, mapping: dict[int, int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Autoclicker Configuration")
        self.resize(420, 220)
        self._rows: list[_MappingRow] = []

        self._layout = QVBoxLayout(self)
        self._rows_widget = QWidget(self)
        self._rows_layout = QFormLayout(self._rows_widget)
        self._layout.addWidget(self._rows_widget)

        controls = QHBoxLayout()
        self._add_btn = QPushButton("Add Key")
        self._add_btn.clicked.connect(self._add_row)
        controls.addWidget(self._add_btn)
        controls.addStretch()
        self._layout.addLayout(controls)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        self._layout.addWidget(self._buttons)

        self._error_label = QPushButton("")
        self._error_label.setFlat(True)
        self._error_label.setEnabled(False)
        self._layout.addWidget(self._error_label)

        if mapping:
            for key, cps in mapping.items():
                self._add_row(key=key, cps=cps)
        else:
            self._add_row()
        self._refresh_remove_buttons()

    def mapping(self) -> dict[int, int] | None:
        result: dict[int, int] = {}
        for row in self._rows:
            key = int(row.key_combo.currentData())
            cps = int(row.cps_spin.value())
            if key in result:
                return None
            result[key] = cps
        return result

    def accept(self) -> None:
        mapping = self.mapping()
        if not mapping:
            self._error_label.setText("Add at least one unique key.")
            return
        self._error_label.setText("")
        super().accept()

    def _add_row(self, key: int | None = None, cps: int = 10) -> None:
        row_widget = QWidget(self)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        key_combo = QComboBox(row_widget)
        for label, key_code in _KEY_OPTIONS:
            key_combo.addItem(label, key_code)
        if key is not None:
            index = key_combo.findData(key)
            if index >= 0:
                key_combo.setCurrentIndex(index)

        cps_spin = QSpinBox(row_widget)
        cps_spin.setMinimum(1)
        cps_spin.setMaximum(100)
        cps_spin.setValue(max(1, min(100, int(cps))))
        cps_spin.setSuffix(" CPS")

        remove_btn = QPushButton("Remove", row_widget)
        remove_btn.clicked.connect(lambda: self._remove_row(row))

        row_layout.addWidget(key_combo, stretch=2)
        row_layout.addWidget(cps_spin, stretch=1)
        row_layout.addWidget(remove_btn)
        self._rows_layout.addRow("Key Mapping", row_widget)

        row = _MappingRow(
            container=row_widget,
            key_combo=key_combo,
            cps_spin=cps_spin,
            remove_btn=remove_btn,
        )
        self._rows.append(row)
        self._refresh_remove_buttons()

    def _remove_row(self, row: _MappingRow) -> None:
        if row not in self._rows:
            return
        self._rows.remove(row)
        self._rows_layout.removeWidget(row.container)
        row.container.deleteLater()
        self._refresh_remove_buttons()

    def _refresh_remove_buttons(self) -> None:
        allow_remove = len(self._rows) > 1
        for row in self._rows:
            row.remove_btn.setEnabled(allow_remove)


def format_mapping_summary(mapping: dict[int, int]) -> str:
    if not mapping:
        return "none"
    parts = []
    for key_code, cps in sorted(mapping.items(), key=lambda item: item[0]):
        key_label = KEY_LABELS.get(key_code, f"Key({key_code})")
        parts.append(f"{key_label}:{cps}cps")
    return ", ".join(parts)
