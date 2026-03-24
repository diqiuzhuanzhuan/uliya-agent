import ast
import operator as op

from app.tools.base import BaseTool, ToolContext, ToolResult


ALLOWED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.Mod: op.mod,
}


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Safely evaluate a simple arithmetic expression."

    def _eval(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[type(node.op)](
                self._eval(node.left),
                self._eval(node.right),
            )
        if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
            return ALLOWED_OPERATORS[type(node.op)](self._eval(node.operand))
        raise ValueError("Unsupported expression")

    async def run(self, arguments: dict[str, str], context: ToolContext) -> ToolResult:
        expression = arguments.get("expression", "")
        tree = ast.parse(expression, mode="eval")
        value = self._eval(tree.body)
        return ToolResult(
            name=self.name,
            arguments={"expression": expression},
            output=f"{expression} = {value:g}",
        )
