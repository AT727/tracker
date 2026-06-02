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
            eval_formula("x +* y", {"x": 1.0, "y": 2.0})

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
