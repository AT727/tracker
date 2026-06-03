# Column Mutations — Design Spec

## Summary

Add user-defined computed columns ("mutations") that derive new values from existing data using basic arithmetic. Mutations appear in the data table and CSV export. Mutation definitions auto-save globally and restore on app start.

## Data Model — `tracker/mutations/models.py`

```python
@dataclass
class ColumnMutation:
    name: str       # column header text, e.g. "norm_x", "radial_dist"
    formula: str    # expression string, e.g. "x * 2 + y / (frame + 1)"
```

Built-in variables available in formulas: `x`, `y`, `t`, `frame`
- `x`, `y` — world coordinates (cm) from `CoordinatePipeline.pixel_to_world()`
- `t` — timestamp in seconds (`mark.timestamp_s`)
- `frame` — 0-based frame index (`mark.frame`)

## Safe Formula Evaluation — `tracker/mutations/eval.py`

Parse expression via `ast.parse()`, walk the tree with an allowed-node whitelist:

### Allowed AST nodes
- `ast.Expression` — root
- `ast.Add`, `ast.Sub`, `ast.Mult`, `ast.Div` — binary arithmetic
- `ast.USub` — unary negation
- `ast.Name` — variable reference (must be in allowed set: x, y, t, frame)
- `ast.Constant` — numeric literals (int / float)

### Rejected (raises ValueError with message)
- Function calls (`ast.Call`)
- Attribute access (`ast.Attribute`)
- Subscripts, slices, comprehensions, lambdas
- Any other AST node type

### Evaluation
```python
def eval_formula(expr: str, vars: dict[str, float]) -> float
```
Returns float. Raises `ValueError` for invalid expressions or undefined variables.

### AST caching
Parse formula once per refresh cycle, re-use node tree across all rows.

## Persistence — `tracker/mutations/persistence.py`

- **File:** `~/.tracker/mutations.json`
- **Format:** `{"mutations": [{"name": "norm_x", "formula": "x * 2"}, ...]}`
- **Interface:**
  - `MutationStore.load() -> list[ColumnMutation]` — returns empty list if file missing or corrupt
  - `MutationStore.save(mutations: list[ColumnMutation])` — overwrites file
- **Global scope:** Same mutations apply across all videos (like calibration preset)
- **Auto-save:** Triggered on every add/edit/remove in the dialog
- **Auto-load:** On app startup in `MainWindow.__init__`

## UI — Column Manager Dialog — `tracker/mutations/dialog.py`

### Trigger
- Toolbar button or menu item "Columns > Column Manager..."

### Dialog Layout
A `QDialog` with:
- **List widget** showing each mutation as `"{name}   =   {formula}"`
  - Each item has inline **Edit** button
- **[+ Add Column]** button → opens Add/Edit sub-dialog
- **[Remove]** button → removes selected mutation with confirmation
- **[Close]** button → accepts dialog

### Add/Edit Sub-dialog
Small `QDialog` with:
- **Column name:** `QLineEdit` (required, unique)
- **Formula:** `QLineEdit` (required, validated)
- **Validate:** evaluates formula against sample values `{x: 0, y: 0, t: 0, frame: 0}` and shows error/success
- **[OK]** / **[Cancel]**

## Data Table Integration — `tracker/panels/data_table.py`

### Headers
- 4 hardcoded headers: `frame`, `t (s)`, `x (cm)`, `y (cm)`
- Append one column per mutation using `mutation.name`

### Row refresh
For each mark:
1. Compute world coords via pipeline (existing)
2. Set frame, t, x, y (existing)
3. For each mutation: build vars dict, call `eval_formula()`, set cell text or `"ERR"`

## CSV Export — `tracker/export/csv_writer.py`

### Signature
```python
def export_csv(path, collector, pipeline, mutations=None)
```
`mutations` defaults to `[]`.

### Output
`frame, t (s), x (cm), y (cm), {mut[0].name}, {mut[1].name}, ...`

Rows computed same as data table.

## MainWindow Wiring — `tracker/app/main_window.py`

1. **`__init__`:** `self._mutations = MutationStore.load()`
2. **Menu/toolbar:** "Column Manager..." action → opens dialog → on accept: update, save, refresh
3. **Table refresh:** Pass `self._mutations` to `DataTablePanel.refresh()`
4. **CSV export:** Pass `self._mutations` to `export_csv()`

## Files

| File | Action |
|------|--------|
| `tracker/mutations/__init__.py` | Create |
| `tracker/mutations/models.py` | Create |
| `tracker/mutations/eval.py` | Create |
| `tracker/mutations/persistence.py` | Create |
| `tracker/mutations/dialog.py` | Create |
| `tracker/panels/data_table.py` | Modify |
| `tracker/export/csv_writer.py` | Modify |
| `tracker/app/main_window.py` | Modify |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Mutations file missing | Load returns empty list |
| Mutations file corrupt | Load returns empty list |
| Invalid formula syntax | "ERR" in table cell |
| Variable name typo | "ERR" in table cell |
| Division by zero | "ERR" in table cell |
| Dialog validation | Sample eval before accept; show error |
| Empty name | Reject |
| Duplicate name | Reject |

## Out of Scope
- Plot panel integration
- Series-aware computations
- Calibration variable access
- Chained mutations
- Per-video mutation sets
- Undo/redo for mutation edits
