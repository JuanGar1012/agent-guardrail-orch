from __future__ import annotations

import ast
import operator
from pydantic import BaseModel, Field


class CalculatorInput(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Num):
        return float(node.n)
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported expression.")


async def run_calculator(data: CalculatorInput) -> dict[str, float | str]:
    tree = ast.parse(data.expression, mode="eval")
    result = _safe_eval(tree.body)
    return {"expression": data.expression, "result": result}
