from pathlib import Path

from app.core.config import ROOT_DIR
from app.tools.base import BaseTool, ToolContext, ToolResult


class FileReaderMockTool(BaseTool):
    name = "file_reader_mock"
    description = "Read a local file preview in a safe, capped way for agent demos."

    async def run(self, arguments: dict[str, str], context: ToolContext) -> ToolResult:
        relative_path = arguments.get("path", "README.md")
        target = (ROOT_DIR / relative_path).resolve()
        if not target.exists() or ROOT_DIR not in target.parents and target != ROOT_DIR:
            output = f"File not found or outside workspace: {relative_path}"
        else:
            output = target.read_text(encoding="utf-8")[:800]
        return ToolResult(
            name=self.name,
            arguments={"path": relative_path},
            output=output,
        )
