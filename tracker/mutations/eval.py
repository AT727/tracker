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
    ast.UAdd: operator.pos,
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
