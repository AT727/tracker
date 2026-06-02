from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ColumnMutation:
    name: str
    formula: str
