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
