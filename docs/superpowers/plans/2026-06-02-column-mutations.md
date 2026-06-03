# Column Mutations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user-defined computed columns ("mutations") with basic arithmetic that appear in the data table and CSV export, with definitions persisted globally.

**Architecture:** Safe AST-based formula evaluator (no `eval()`). Mutation definitions stored in `~/.tracker/mutations.json`. A `MutationManagerDialog` provides add/edit/remove UI. Modified `DataTablePanel.refresh()` and `export_csv()` accept mutation list and append computed columns.

**Tech Stack:** Python 3.10+, PyQt5, ast, pytest, pytest-qt

---

### Task 1: Data Model + Safe Formula Evaluator

**Files:**
- Create: `tracker/mutations/__init__.py`
- Create: `tracker/mutations/models.py`
- Create: `tracker/mutations/eval.py`
- Test: `tests/test_mutations.py`

- [ ] **Step 1: Create the mutations package**

Create `tracker/mutations/__init__.py`:
```python
from tracker.mutations.models import ColumnMutation
from tracker.mutations.eval import eval_formula

__all__ = ["ColumnMutation", "eval_formula"]
```

Create `tracker/mutations/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ColumnMutation:
    name: str
    formula: str
```

- [ ] **Step 2: Write failing tests for the evaluator**

Create `tests/test_mutations.py`:
```python
import pytest
from tracker.mutations.eval import eval_formula


class TestEvalFormula:
    def test_addition(self):
        assert eval_formula("x + y", {"x": 3.0, "y": 4.0}) == 7.0

    def test_subtraction(self):
        assert eval_formula("x - y", {"x": 10.0, "y": 3.0}) == 7.0

    def test_multiplication(self):
        assert eval_formula("x * 2", {"x": 5.0}) == 10.0

    def test_division(self):
        assert eval_formula("x / 2", {"x": 10.0}) == 5.0

    def test_parentheses_grouping(self):
        assert eval_formula("(x + y) * 2", {"x": 3.0, "y": 4.0}) == 14.0

    def test_unary_minus(self):
        assert eval_formula("-x", {"x": 5.0}) == -5.0

    def test_multiple_variables(self):
        assert eval_formula("x + y + t + frame", {"x": 1.0, "y": 2.0, "t": 3.0, "frame": 4.0}) == 10.0

    def test_division_by_zero_returns_inf(self):
        result = eval_formula("x / 0", {"x": 5.0})
        import math
        assert math.isinf(result)

    def test_invalid_syntax_raises(self):
        with pytest.raises(ValueError, match="Invalid expression"):
            eval_formula("x ++ y", {"x": 1.0, "y": 2.0})

    def test_undefined_variable_raises(self):
        with pytest.raises(ValueError, match="Unknown variable"):
            eval_formula("x + z", {"x": 1.0})

    def test_function_calls_rejected(self):
        with pytest.raises(ValueError, match="not allowed"):
            eval_formula("abs(x)", {"x": -5.0})

    def test_constant_expression(self):
        assert eval_formula("42", {}) == 42.0

    def test_complex_expression(self):
        assert eval_formula("(x * y + t) / (frame + 1)", {"x": 10.0, "y": 2.0, "t": 5.0, "frame": 4.0}) == 5.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_mutations.py -v`
Expected: FAIL (7 failed, 4 errors — module/function not found)

- [ ] **Step 4: Write the safe formula evaluator**

Create `tracker/mutations/eval.py`:
```python
from __future__ import annotations

import ast
import operator
from typing import Any

_ALLOWED_VARIABLES = frozenset({"x", "y", "t", "frame"})

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

_UNARY_OPS = {
    ast.USub: operator.neg,
}


class _EvalVisitor(ast.NodeVisitor):
    def __init__(self, vars: dict[str, float]) -> None:
        self._vars = vars

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Invalid constant: {node.value}")
        return float(node.value)

    def visit_Name(self, node: ast.Name) -> float:
        if node.id not in _ALLOWED_VARIABLES:
            raise ValueError(f"Unknown variable: {node.id}")
        if node.id not in self._vars:
            raise ValueError(f"Variable not provided: {node.id}")
        return self._vars[node.id]

    def visit_BinOp(self, node: ast.BinOp) -> float:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_func = _BINARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
        try:
            return op_func(left, right)
        except ZeroDivisionError:
            return float("inf")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        operand = self.visit(node.operand)
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
        return op_func(operand)

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Expression construct not allowed: {type(node).__name__}")


def eval_formula(expr: str, vars: dict[str, float]) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression: {e}")
    visitor = _EvalVisitor(vars)
    return visitor.visit(tree)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_mutations.py -v`
Expected: PASS (14 passed)

- [ ] **Step 6: Commit**

```
git add tests/test_mutations.py tracker/mutations/__init__.py tracker/mutations/models.py tracker/mutations/eval.py
git commit -m "feat: add ColumnMutation model and safe AST-based formula evaluator"
```

---

### Task 2: Mutation Persistence

**Files:**
- Create: `tracker/mutations/persistence.py`
- Test: `tests/test_mutations.py`

- [ ] **Step 1: Write failing persistence tests**

Append to `tests/test_mutations.py`:
```python
import json
from pathlib import Path
from tracker.mutations.models import ColumnMutation
from tracker.mutations.persistence import MutationStore


class TestMutationStore:
    def test_load_nonexistent_returns_empty(self, tmp_path):
        store = MutationStore(tmp_path / "nonexistent.json")
        assert store.load() == []

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "mutations.json"
        store = MutationStore(path)
        mutations = [
            ColumnMutation(name="norm_x", formula="x * 2"),
            ColumnMutation(name="offset_y", formula="y + 5.0"),
        ]
        store.save(mutations)
        loaded = store.load()
        assert len(loaded) == 2
        assert loaded[0].name == "norm_x"
        assert loaded[0].formula == "x * 2"
        assert loaded[1].name == "offset_y"
        assert loaded[1].formula == "y + 5.0"

    def test_load_corrupt_returns_empty(self, tmp_path):
        path = tmp_path / "mutations.json"
        path.write_text("{bad json", encoding="utf-8")
        store = MutationStore(path)
        assert store.load() == []

    def test_save_creates_parent_dir(self, tmp_path):
        path = tmp_path / "subdir" / "mutations.json"
        store = MutationStore(path)
        store.save([ColumnMutation(name="a", formula="x + 1")])
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data == {"mutations": [{"name": "a", "formula": "x + 1"}]}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mutations.py -v`
Expected: 4 new FAILED tests (import errors for persistence module)

- [ ] **Step 3: Write persistence module**

Create `tracker/mutations/persistence.py`:
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from tracker.mutations.models import ColumnMutation


class MutationStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = Path.home() / ".tracker" / "mutations.json"
        self._path = path

    def load(self) -> list[ColumnMutation]:
        if not self._path.is_file():
            return []
        try:
            with self._path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        mutations = []
        for item in data.get("mutations", []):
            mutations.append(ColumnMutation(name=item["name"], formula=item["formula"]))
        return mutations

    def save(self, mutations: list[ColumnMutation]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mutations": [
                {"name": m.name, "formula": m.formula}
                for m in mutations
            ]
        }
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    @property
    def path(self) -> Path:
        return self._path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mutations.py -v`
Expected: PASS (18 passed)

- [ ] **Step 5: Commit**

```
git add tests/test_mutations.py tracker/mutations/persistence.py
git commit -m "feat: add MutationStore for load/save of mutation definitions"
```

---

### Task 3: Column Manager Dialog

**Files:**
- Create: `tracker/mutations/dialog.py`
- Test: `tests/test_mutations_dialog.py`

- [ ] **Step 1: Write failing dialog tests**

Create `tests/test_mutations_dialog.py`:
```python
import pytest
from PyQt5.QtWidgets import QDialog, QLineEdit, QListWidget, QPushButton
from tracker.mutations.models import ColumnMutation
from tracker.mutations.dialog import MutationManagerDialog, MutationEditDialog


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
        ok_btn = dialog.button(QDialog.ButtonBox.Ok)
        assert ok_btn is not None
        ok_btn.click()
        assert dialog.name() == "norm_x"
        assert dialog.formula() == "x * 2"

    def test_rejects_empty_name(self, qtbot):
        dialog = MutationEditDialog()
        qtbot.addWidget(dialog)
        ok_btn = dialog.button(QDialog.ButtonBox.Ok)
        assert ok_btn is not None
        with qtbot.assertNotEmitted(dialog.accepted):
            ok_btn.click()

    def test_rejects_empty_formula(self, qtbot):
        dialog = MutationEditDialog()
        qtbot.addWidget(dialog)
        name_edit = dialog.findChild(QLineEdit, "name_edit")
        assert name_edit is not None
        qtbot.keyClicks(name_edit, "my_col")
        ok_btn = dialog.button(QDialog.ButtonBox.Ok)
        assert ok_btn is not None
        with qtbot.assertNotEmitted(dialog.accepted):
            ok_btn.click()

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

    def test_add_button_opens_edit_dialog(self, qtbot, monkeypatch):
        from tracker.mutations.dialog import MutationEditDialog

        def fake_exec(self):
            self._name = "new_col"
            self._formula = "x + y"
            return QDialog.Accepted
        monkeypatch.setattr(MutationEditDialog, "exec_", fake_exec)

        dialog = MutationManagerDialog(mutations=[])
        qtbot.addWidget(dialog)
        add_btn = dialog.findChild(QPushButton, "add_btn")
        assert add_btn is not None
        add_btn.click()
        assert len(dialog.mutations()) == 1
        assert dialog.mutations()[0].name == "new_col"

    def test_remove_button_removes_selected(self, qtbot):
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mutations_dialog.py -v`
Expected: FAIL (import error — dialog module not found)

- [ ] **Step 3: Write the dialogs**

Create `tracker/mutations/dialog.py`:
```python
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
    QWidget,
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mutations_dialog.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```
git add tests/test_mutations_dialog.py tracker/mutations/dialog.py
git commit -m "feat: add MutationManagerDialog and MutationEditDialog for column management"
```

---

### Task 4: Data Table Integration

**Files:**
- Modify: `tracker/panels/data_table.py`
- Test: `tests/test_data_table.py`

- [ ] **Step 1: Write failing test for mutation columns in data table**

Append to `tests/test_data_table.py`:
```python
from tracker.mutations.models import ColumnMutation
from tracker.mutations.eval import eval_formula


def test_refresh_renders_mutation_columns(qtbot):
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 10.0, 10.0)
    collector.upsert_mark(1, 0.1, 20.0, 20.0)
    mutations = [ColumnMutation(name="norm_x", formula="x * 2")]
    panel.refresh(
        collector,
        CoordinatePipeline(),
        series_id=collector.active_series_id,
        gap_after_frames=set(),
        mutations=mutations,
    )
    assert panel.columnCount() == 5
    # Header should include mutation name
    header = panel.horizontalHeaderItem(4)
    assert header is not None
    assert header.text() == "norm_x"
    # First row: x=10 (uncalibrated px), so norm_x = 20
    assert panel.item(0, 4) is not None
    assert panel.item(0, 4).text() == "20.000"


def test_refresh_shows_err_for_invalid_formula(qtbot):
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 10.0, 10.0)
    mutations = [ColumnMutation(name="bad", formula="x + unknown_var")]
    panel.refresh(
        collector,
        CoordinatePipeline(),
        series_id=collector.active_series_id,
        gap_after_frames=set(),
        mutations=mutations,
    )
    assert panel.item(0, 4) is not None
    assert panel.item(0, 4).text() == "ERR"


def test_refresh_works_without_mutations(qtbot):
    panel = DataTablePanel()
    qtbot.addWidget(panel)
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 10.0, 10.0)
    panel.refresh(
        collector,
        CoordinatePipeline(),
        series_id=collector.active_series_id,
        gap_after_frames=set(),
    )
    assert panel.columnCount() == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_data_table.py -v`
Expected: 3 new FAILED tests (DataTablePanel.refresh doesn't accept `mutations` param)

- [ ] **Step 3: Modify DataTablePanel to support mutation columns**

Edit `tracker/panels/data_table.py`. Change `HEADERS` from a class constant to dynamic, and update `refresh()`:

```python
"""Live data table."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QHeaderView, QMenu, QTableWidget, QTableWidgetItem

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.mutations.eval import eval_formula
from tracker.mutations.models import ColumnMutation
from tracker.tracking.collector import TrackingCollector


class DataTablePanel(QTableWidget):
    go_to_frame_requested = pyqtSignal(int)

    BASE_HEADERS = ["frame", "t (s)", "x (cm)", "y (cm)"]
    _SCROLL_THRESHOLD = 5
    _FRAME_ROLE = Qt.UserRole + 1
    _SEPARATOR_BG = QColor("#2f0f0f")
    _SEPARATOR_FG = QColor("#ff6b6b")
    _SEPARATOR_HEIGHT = 8

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self.BASE_HEADERS), parent)
        self.setHorizontalHeaderLabels(self.BASE_HEADERS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def refresh(
        self,
        collector: TrackingCollector,
        pipeline: CoordinatePipeline,
        series_id: str | None = None,
        gap_after_frames: set[int] | None = None,
        mutations: list[ColumnMutation] | None = None,
    ) -> None:
        mutations = mutations or []
        marks = (
            collector.marks_for_series(series_id)
            if series_id
            else collector.marks
        )
        marks = sorted(marks, key=lambda m: m.frame)
        gap_after_frames = gap_after_frames or set()
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - self._SCROLL_THRESHOLD
        row_count = len(marks) + sum(1 for mark in marks if mark.frame in gap_after_frames)
        self.setRowCount(row_count)

        headers = self.BASE_HEADERS + [m.name for m in mutations]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        row = 0
        for mark in marks:
            world = pipeline.pixel_to_world(mark.px, mark.py)
            values = [
                str(mark.frame + 1),
                f"{mark.timestamp_s:.4f}",
                f"{world.x:.3f}",
                f"{world.y:.3f}",
            ]
            for mutation in mutations:
                try:
                    result = eval_formula(mutation.formula, {
                        "x": world.x,
                        "y": world.y,
                        "t": mark.timestamp_s,
                        "frame": float(mark.frame),
                    })
                    values.append(f"{result:.3f}")
                except ValueError:
                    values.append("ERR")
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setData(self._FRAME_ROLE, mark.frame)
                self.setItem(row, col, item)
            row += 1
            if mark.frame in gap_after_frames:
                self._insert_gap_row(row)
                row += 1
        if marks and (at_bottom or len(marks) == 1):
            target_row = self._last_data_row()
            if target_row is not None:
                self.scrollToItem(self.item(target_row, 0))

    def _insert_gap_row(self, row: int) -> None:
        col_count = self.columnCount()
        values = [""] * col_count
        if col_count >= 2:
            values[1] = "missing frame(s)"
        for col, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setBackground(self._SEPARATOR_BG)
            item.setForeground(self._SEPARATOR_FG)
            self.setItem(row, col, item)
        self.setRowHeight(row, self._SEPARATOR_HEIGHT)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_data_table.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```
git add tracker/panels/data_table.py tests/test_data_table.py
git commit -m "feat: add mutation column support to DataTablePanel"
```

---

### Task 5: CSV Export Integration

**Files:**
- Modify: `tracker/export/csv_writer.py`
- Create: `tests/test_csv_writer.py`

- [ ] **Step 1: Write failing CSV export tests**

Create `tests/test_csv_writer.py`:
```python
import csv
import io

import pytest

from tracker.calibration.data import CalibrationData
from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.export.csv_writer import export_csv
from tracker.mutations.models import ColumnMutation
from tracker.tracking.collector import TrackingCollector


def _make_calibrated_pipeline():
    cal = CalibrationData(
        stick_a_px=(0.0, 0.0),
        stick_b_px=(100.0, 0.0),
        known_length_cm=50.0,
        origin_px=(0.0, 0.0),
    )
    cal.compute_scale()
    return CoordinatePipeline(calibration=cal)


def test_export_with_mutations(tmp_path):
    path = tmp_path / "out.csv"
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 10.0, 10.0)
    collector.upsert_mark(1, 0.033, 20.0, 20.0)
    pipeline = _make_calibrated_pipeline()
    mutations = [ColumnMutation(name="norm_x", formula="x * 2")]
    export_csv(path, collector, pipeline, mutations=mutations)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # header + 2 data rows
    reader = csv.reader(io.StringIO(path.read_text(encoding="utf-8")))
    rows = list(reader)
    assert rows[0] == ["frame", "t (s)", "x (cm)", "y (cm)", "norm_x"]
    # x = (10 - 0) * 0.5 = 5.0, norm_x = 10.0
    assert float(rows[1][4]) == pytest.approx(10.0)


def test_export_without_mutations(tmp_path):
    path = tmp_path / "out.csv"
    collector = TrackingCollector()
    collector.upsert_mark(0, 0.0, 10.0, 10.0)
    pipeline = _make_calibrated_pipeline()
    export_csv(path, collector, pipeline)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "norm_x" not in lines[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_csv_writer.py -v`
Expected: FAIL (export_csv doesn't accept mutations param)

- [ ] **Step 3: Modify export_csv**

Edit `tracker/export/csv_writer.py`:
```python
"""CSV export per spec."""

from __future__ import annotations

import csv
from pathlib import Path

from tracker.coordinates.pipeline import CoordinatePipeline
from tracker.mutations.eval import eval_formula
from tracker.mutations.models import ColumnMutation
from tracker.tracking.collector import TrackingCollector


def export_csv(
    path: str | Path,
    collector: TrackingCollector,
    pipeline: CoordinatePipeline,
    mutations: list[ColumnMutation] | None = None,
) -> None:
    mutations = mutations or []
    p = Path(path)
    if not pipeline.calibration.is_calibrated:
        raise ValueError("Calibration is required before exporting CSV data in centimeters.")

    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = ["frame", "t (s)", "x (cm)", "y (cm)"] + [m.name for m in mutations]
        writer.writerow(headers)
        for mark in collector.marks:
            world = pipeline.pixel_to_world(mark.px, mark.py)
            row = [
                mark.frame + 1,
                f"{mark.timestamp_s:.6f}",
                f"{world.x:.6f}",
                f"{world.y:.6f}",
            ]
            for mutation in mutations:
                try:
                    result = eval_formula(mutation.formula, {
                        "x": world.x,
                        "y": world.y,
                        "t": mark.timestamp_s,
                        "frame": float(mark.frame),
                    })
                    row.append(f"{result:.6f}")
                except ValueError:
                    row.append("ERR")
            writer.writerow(row)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_csv_writer.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```
git add tracker/export/csv_writer.py tests/test_csv_writer.py
git commit -m "feat: add mutation column support to CSV export"
```

---

### Task 6: MainWindow Wiring

**Files:**
- Modify: `tracker/app/main_window.py`
- Test: Ensure existing tests still pass

- [ ] **Step 1: Update MainWindow to load mutations on init and add column manager**

Edit `tracker/app/main_window.py`. Add three changes:

**a) Add imports at top:**
```python
from tracker.mutations.dialog import MutationManagerDialog
from tracker.mutations.models import ColumnMutation
from tracker.mutations.persistence import MutationStore
```

**b) In `__init__`, after the autoclicker init (line 75), add:**
```python
        self._mutation_store = MutationStore()
        self._mutations: list[ColumnMutation] = self._mutation_store.load()
```

**c) In `_build_menus`, after the Autoclicker menu (after line 248), add a Columns menu:**
```python
        col_menu = self.menuBar().addMenu("&Columns")
        manager_action = QAction("Column Manager...", self)
        manager_action.triggered.connect(self._open_column_manager)
        col_menu.addAction(manager_action)
```

**d) Add the handler method (after `_open_autoclicker_config` at line 268):**
```python
    def _open_column_manager(self) -> None:
        dialog = MutationManagerDialog(self._mutations, self)
        if dialog.exec_() != dialog.Accepted:
            return
        self._mutations = dialog.mutations()
        self._mutation_store.save(self._mutations)
        self._refresh_table()
```

**e) Update `_refresh_table` (around line 587) to pass mutations:**
```python
    def _refresh_table(self) -> None:
        active_series_id = self.collector.active_series_id
        skip_frames = self._find_skipped_frames(active_series_id)
        gap_after_frames = {start for start, _ in skip_frames}
        self._data_table.refresh(
            self.collector,
            self.pipeline,
            series_id=active_series_id,
            gap_after_frames=gap_after_frames,
            mutations=self._mutations,
        )
        self._update_skip_warning(skip_frames)
```

**f) Update `_export_csv` (around line 691) to pass mutations:**
```python
            export_csv(path, self.collector, self.pipeline, mutations=self._mutations)
```

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `pytest tests/ -v`
Expected: All existing tests PASS (plus new mutation tests)

- [ ] **Step 3: Manually verify the feature works end-to-end**

Run the app and test:
1. Open a video, click a few marks
2. Open "Columns > Column Manager"
3. Add a mutation: name="norm_x", formula="x * 2"
4. Confirm the data table shows a new "norm_x" column with computed values
5. Close and reopen the app → mutation column still appears
6. Export CSV → verify the mutation column is in the output file

- [ ] **Step 4: Commit**

```
git add tracker/app/main_window.py
git commit -m "feat: wire Column Manager dialog into MainWindow with persistence"
```

---

### Verification

Run full test suite:
```
pytest tests/ -v
```
Expected: All tests pass.

Run lint:
```
ruff check tracker/ tests/
```
Expected: No errors.
```
