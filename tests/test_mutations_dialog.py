import pytest
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLineEdit, QListWidget, QPushButton
from tracker.mutations.models import ColumnMutation
from tracker.mutations.dialog import MutationManagerDialog, MutationEditDialog


def _get_ok_btn(dialog):
    button_box = dialog.findChild(QDialogButtonBox)
    assert button_box is not None
    return button_box.button(QDialogButtonBox.Ok)


class TestMutationEditDialog:
    def test_accepts_valid_input(self, qtbot):
        dialog = MutationEditDialog()
        qtbot.addWidget(dialog)
        name_edit = dialog.findChild(QLineEdit, "name_edit")
        formula_edit = dialog.findChild(QLineEdit, "formula_edit")
        assert name_edit is not None
        assert formula_edit is not None
        qtbot.keyClicks(name_edit, "norm_x")
        qtbot.keyClicks(formula_edit, "x * 2")
        _get_ok_btn(dialog).click()
        assert dialog.name() == "norm_x"
        assert dialog.formula() == "x * 2"

    def test_rejects_empty_name(self, qtbot):
        dialog = MutationEditDialog()
        qtbot.addWidget(dialog)
        _get_ok_btn(dialog).click()
        assert dialog.result() != QDialog.Accepted

    def test_rejects_empty_formula(self, qtbot):
        dialog = MutationEditDialog()
        qtbot.addWidget(dialog)
        name_edit = dialog.findChild(QLineEdit, "name_edit")
        assert name_edit is not None
        qtbot.keyClicks(name_edit, "my_col")
        _get_ok_btn(dialog).click()
        assert dialog.result() != QDialog.Accepted

    def test_prefills_edit_mode(self, qtbot):
        dialog = MutationEditDialog(mutation=ColumnMutation(name="norm_x", formula="x * 2"))
        qtbot.addWidget(dialog)
        assert dialog.name() == "norm_x"
        assert dialog.formula() == "x * 2"


class TestMutationManagerDialog:
    def test_empty_dialog_has_no_rows(self, qtbot):
        dialog = MutationManagerDialog(mutations=[])
        qtbot.addWidget(dialog)
        list_widget = dialog.findChild(QListWidget)
        assert list_widget is not None
        assert list_widget.count() == 0

    def test_shows_existing_mutations(self, qtbot):
        mutations = [
            ColumnMutation(name="norm_x", formula="x * 2"),
            ColumnMutation(name="offset_y", formula="y + 5"),
        ]
        dialog = MutationManagerDialog(mutations=mutations)
        qtbot.addWidget(dialog)
        list_widget = dialog.findChild(QListWidget)
        assert list_widget is not None
        assert list_widget.count() == 2
        assert "norm_x" in list_widget.item(0).text()
        assert "offset_y" in list_widget.item(1).text()

    def test_add_opens_edit_dialog(self, qtbot, monkeypatch):
        dialog = MutationManagerDialog(mutations=[])
        qtbot.addWidget(dialog)

        def fake_exec(self):
            self._name = "new_col"
            self._formula = "x + y"
            return QDialog.Accepted
        monkeypatch.setattr(MutationEditDialog, "exec_", fake_exec)

        add_btn = dialog.findChild(QPushButton, "add_btn")
        assert add_btn is not None
        add_btn.click()
        assert len(dialog.mutations()) == 1
        assert dialog.mutations()[0].name == "new_col"

    def test_remove_removes_selected(self, qtbot):
        mutations = [ColumnMutation(name="norm_x", formula="x * 2")]
        dialog = MutationManagerDialog(mutations=mutations)
        qtbot.addWidget(dialog)
        list_widget = dialog.findChild(QListWidget)
        assert list_widget is not None
        list_widget.setCurrentRow(0)
        remove_btn = dialog.findChild(QPushButton, "remove_btn")
        assert remove_btn is not None
        remove_btn.click()
        assert dialog.mutations() == []

    def test_mutations_returns_copy(self, qtbot):
        mutations = [ColumnMutation(name="norm_x", formula="x * 2")]
        dialog = MutationManagerDialog(mutations=mutations)
        qtbot.addWidget(dialog)
        result = dialog.mutations()
        assert len(result) == 1
        assert result[0] == mutations[0]
