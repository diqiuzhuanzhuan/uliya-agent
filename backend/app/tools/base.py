from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolContext:
    thread_id: str
    user_message: str


@dataclass(slots=True)
class ToolResult:
    name: str
    arguments: dict[str, Any]
    output: str


class BaseTool:
    name: str = ""
    description: str = ""

    async def run(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        raise NotImplementedError
