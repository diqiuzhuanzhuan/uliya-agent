from app.tools.base import BaseTool, ToolContext, ToolResult


class WebSearchMockTool(BaseTool):
    name = "web_search_mock"
    description = "Return a deterministic mocked web search result for UI and agent flow demos."

    async def run(self, arguments: dict[str, str], context: ToolContext) -> ToolResult:
        query = arguments.get("query", context.user_message)
        output = "\n".join(
            [
                f"Search query: {query}",
                "1. Deep Agents overview - planning, tools, memory, streaming.",
                "2. FastAPI SSE pattern - use StreamingResponse with text/event-stream.",
                "3. Next.js streaming client - parse SSE chunks over fetch().",
            ]
        )
        return ToolResult(
            name=self.name,
            arguments={"query": query},
            output=output,
        )
