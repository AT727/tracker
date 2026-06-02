from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from tracker.mutations.eval import eval_formula
from tracker.mutations.models import ColumnMutation


class MutationEditDialog(QDialog):
    def __init__(self, parent=None, mutation: ColumnMutation | None = None) -> None:
        super().__init__(parent)
        self._mutation = mutation
        self._name = mutation.name if mutation else ""
        self._formula = mutation.formula if mutation else ""
        self._setup_ui()
        self.setWindowTitle("Edit Mutation" if mutation else "Add Mutation")

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        self._name_edit = QLineEdit(self._name)
        self._name_edit.setObjectName("name_edit")
        self._formula_edit = QLineEdit(self._formula)
        self._formula_edit.setObjectName("formula_edit")
        self._formula_edit.setPlaceholderText("e.g. x * 2 + y / (frame + 1)")
        layout.addRow("Column name:", self._name_edit)
        layout.addRow("Formula:", self._formula_edit)
        self._validate_label = QLabel("")
        self._validate_label.setStyleSheet("color: #ff6b6b")
        layout.addRow(self._validate_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        formula = self._formula_edit.text().strip()
        if not name:
            self._validate_label.setText("Column name is required")
            return
        if not formula:
            self._validate_label.setText("Formula is required")
            return
        try:
            eval_formula(formula, {"x": 0.0, "y": 0.0, "t": 0.0, "frame": 0.0})
        except ValueError as e:
            self._validate_label.setText(f"Formula error: {e}")
            return
        self._name = name
        self._formula = formula
        self.accept()

    def name(self) -> str:
        return self._name

    def formula(self) -> str:
        return self._formula


class MutationManagerDialog(QDialog):
    def __init__(self, mutations: list[ColumnMutation], parent=None) -> None:
        super().__init__(parent)
        self._mutations = list(mutations)
        self._setup_ui()
        self.setWindowTitle("Column Manager")
        self.resize(400, 300)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        self._list_widget = QListWidget()
        layout.addWidget(self._list_widget)
        for m in self._mutations:
            self._list_widget.addItem(f"{m.name}  =  {m.formula}")
        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("Add Column")
        self._add_btn.setObjectName("add_btn")
        self._add_btn.clicked.connect(self._on_add)
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.setObjectName("remove_btn")
        self._remove_btn.clicked.connect(self._on_remove)
        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        close_row = QHBoxLayout()
        close_row.addStretch()
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.accept)
        close_row.addWidget(self._close_btn)
        layout.addLayout(close_row)

    def _on_add(self) -> None:
        dialog = MutationEditDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        new_mut = ColumnMutation(name=dialog.name(), formula=dialog.formula())
        self._mutations.append(new_mut)
        self._list_widget.addItem(f"{new_mut.name}  =  {new_mut.formula}")

    def _on_remove(self) -> None:
        row = self._list_widget.currentRow()
        if row < 0:
            return
        self._list_widget.takeItem(row)
        self._mutations.pop(row)

    def mutations(self) -> list[ColumnMutation]:
        return list(self._mutations)
