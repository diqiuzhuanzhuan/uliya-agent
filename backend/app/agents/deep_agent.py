import ast
import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from deepagents import create_deep_agent
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.tools import tool

from app.core.config import ROOT_DIR, get_settings
from app.db.repository import AgentRepository
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import AgentConfig, ChatRequest
from app.tools.base import BaseTool, ToolContext, ToolResult
from app.tools.calculator import CalculatorTool
from app.tools.file_reader_mock import FileReaderMockTool
from app.tools.web_search_mock import WebSearchMockTool


def _extract_expression(message: str) -> str | None:
    candidates = re.findall(r"\d[\d\s\.\+\-\*\/\(\)%]*[\d\)%]", message)
    for candidate in candidates:
        expression = candidate.strip()
        if any(operator in expression for operator in ["+", "-", "*", "/", "%"]):
            return expression
    return None


def _extract_file_path(message: str) -> str | None:
    match = re.search(r"[\w./-]+\.\w+", message)
    return match.group(0) if match else None


class DeepAgentRuntime:
    """
    Stable runtime boundary for the web app.

    The MVP uses a deterministic orchestration loop that mirrors Deep Agents concepts
    such as planning, tools, streaming events, memory, and a future skills hook.
    If `USE_REAL_DEEPAGENTS=true` and the required model settings are present, this
    class can later swap to the official SDK without changing the API layer.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.repository = AgentRepository()
        self.available_tools: dict[str, BaseTool] = {
            "calculator": CalculatorTool(),
            "web_search_mock": WebSearchMockTool(),
            "file_reader_mock": FileReaderMockTool(),
        }

    async def stream(
        self,
        request: ChatRequest,
        session: AsyncSession,
    ) -> AsyncIterator[dict[str, Any]]:
        config = request.config
        context = ToolContext(thread_id=request.thread_id, user_message=request.message)
        memories = (
            await self.repository.list_recent_messages(session, request.thread_id)
            if config.memory_enabled
            else []
        )

        if self._should_use_real_deepagents(config):
            async for event in self._stream_with_deepagents(request, session, memories):
                yield event
            return

        yield {
            "type": "run_started",
            "thread_id": request.thread_id,
            "message": request.message,
        }
        await asyncio.sleep(0.05)

        plan = self._build_plan(request.message, config, memories)
        yield {"type": "plan_created", "plan": plan}
        await asyncio.sleep(0.05)

        if config.use_real_deepagents:
            yield {
                "type": "step_started",
                "step": {
                    "id": "deepagents-adapter",
                    "title": "Deep Agents SDK adapter check",
                    "kind": "reasoning",
                    "detail": "MVP keeps a stable adapter boundary and falls back to the local orchestrator until a real model runtime is configured.",
                },
            }

        yield {
            "type": "memory_snapshot",
            "items": [memory.model_dump(mode="json") for memory in memories],
        }
        if config.retrieval_enabled:
            upload_matches = await self.repository.search_uploads(session, request.message)
            if upload_matches:
                yield {
                    "type": "retrieval_result",
                    "items": [item.model_dump(mode="json") for item in upload_matches],
                }
        if config.memory_enabled:
            await self.repository.append_message(session, request.thread_id, "user", request.message)
        await asyncio.sleep(0.05)

        tool_results = []
        for step in plan:
            yield {"type": "step_started", "step": step}
            if step["kind"] == "tool":
                tool = self.available_tools[step["tool_name"]]
                yield {
                    "type": "tool_call",
                    "tool_name": tool.name,
                    "arguments": step["arguments"],
                }
                result = await tool.run(step["arguments"], context)
                tool_results.append(result)
                yield {
                    "type": "tool_result",
                    "tool_name": result.name,
                    "arguments": result.arguments,
                    "output": result.output,
                }
            await asyncio.sleep(0.08)
            yield {"type": "step_completed", "step": step}

        final_answer = self._compose_answer(request.message, memories, tool_results, config)
        for chunk in self._chunk_text(final_answer, size=20):
            yield {"type": "answer_delta", "delta": chunk}
            await asyncio.sleep(0.02)

        if config.memory_enabled:
            await self.repository.append_message(session, request.thread_id, "assistant", final_answer)
            latest_memories = await self.repository.list_recent_messages(session, request.thread_id)
        else:
            latest_memories = []
        yield {
            "type": "run_completed",
            "answer": final_answer,
            "memories": [memory.model_dump(mode="json") for memory in latest_memories],
        }

    def _build_plan(
        self,
        message: str,
        config: AgentConfig,
        memories: list[Any],
    ) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = [
            {
                "id": "analyze-request",
                "title": "Analyze user goal",
                "kind": "reasoning",
                "detail": "Interpret the request and decide whether tools are required.",
            },
            {
                "id": "review-memory",
                "title": "Review local memory",
                "kind": "reasoning",
                "detail": f"Load {len(memories)} recent messages from SQLite memory.",
            },
        ]

        selected_tools = (
            config.selected_tools or list(self.available_tools.keys())
        )
        expression = _extract_expression(message)
        file_path = _extract_file_path(message)

        if expression and "calculator" in selected_tools:
            plan.append(
                {
                    "id": "tool-calculator",
                    "title": "Run calculator tool",
                    "kind": "tool",
                    "tool_name": "calculator",
                    "arguments": {"expression": expression},
                }
            )
        if any(keyword in message.lower() for keyword in ["search", "查", "搜", "资料"]) and "web_search_mock" in selected_tools:
            plan.append(
                {
                    "id": "tool-search",
                    "title": "Run web search mock",
                    "kind": "tool",
                    "tool_name": "web_search_mock",
                    "arguments": {"query": message},
                }
            )
        if file_path and "file_reader_mock" in selected_tools:
            plan.append(
                {
                    "id": "tool-file",
                    "title": "Read related file preview",
                    "kind": "tool",
                    "tool_name": "file_reader_mock",
                    "arguments": {"path": file_path},
                }
            )

        plan.append(
            {
                "id": "finalize-answer",
                "title": "Compose final answer",
                "kind": "reasoning",
                "detail": "Merge planning, tool outputs, memory, and skills prompt into the final response.",
            }
        )
        return plan

    def _compose_answer(
        self,
        message: str,
        memories: list[Any],
        tool_results: list[ToolResult],
        config: AgentConfig,
    ) -> str:
        lines = [
            "I understood your request and produced a multi-step execution trace.",
            f"Current input: {message}",
        ]
        if config.use_real_deepagents:
            lines.append(
                "The Deep Agents adapter flag is enabled. This MVP currently preserves the adapter boundary while using the local orchestrator by default."
            )
        if memories:
            lines.append(f"Loaded {len(memories)} recent memory items from local SQLite.")
        elif not config.memory_enabled:
            lines.append("SQLite memory was disabled for this run.")
        if config.retrieval_enabled:
            lines.append("Retrieval hook is enabled for uploaded local documents.")
        if config.skills_prompt:
            lines.append(f"Skills hook active: {config.skills_prompt}")
        if tool_results:
            lines.append("Tool results:")
            for result in tool_results:
                lines.append(f"- {result.name}: {result.output}")
        else:
            lines.append("No tool invocation was required for this turn.")
        lines.append(
            "This runtime is intentionally modular so we can later swap in RAG, uploads, auth, and more tools."
        )
        return "\n".join(lines)

    def _chunk_text(self, text: str, size: int = 24) -> list[str]:
        return [text[index : index + size] for index in range(0, len(text), size)]

    def _should_use_real_deepagents(self, config: AgentConfig) -> bool:
        return bool(
            config.use_real_deepagents
            and self.settings.openai_api_key
            and config.deepagents_model
        )

    async def _stream_with_deepagents(
        self,
        request: ChatRequest,
        session: AsyncSession,
        memories: list[Any],
    ) -> AsyncIterator[dict[str, Any]]:
        agent = create_deep_agent(
            model=f"openai:{request.config.deepagents_model}",
            tools=self._build_deepagents_tools(),
            system_prompt=self._compose_real_system_prompt(request.config),
            name="uliya-real-deep-agent",
        )

        yield {
            "type": "run_started",
            "thread_id": request.thread_id,
            "message": request.message,
            "runtime": "deepagents",
        }
        yield {
            "type": "memory_snapshot",
            "items": [memory.model_dump(mode="json") for memory in memories],
        }
        if request.config.memory_enabled:
            await self.repository.append_message(session, request.thread_id, "user", request.message)

        answer_parts: list[str] = []
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": request.message}]},
            version="v2",
        ):
            mapped = self._map_deepagents_event(event)
            if mapped is not None:
                if mapped["type"] == "answer_delta":
                    answer_parts.append(mapped["delta"])
                yield mapped

        answer = "".join(answer_parts).strip() or "Deep Agents run completed."
        if request.config.memory_enabled:
            await self.repository.append_message(session, request.thread_id, "assistant", answer)
            latest_memories = await self.repository.list_recent_messages(session, request.thread_id)
        else:
            latest_memories = []
        yield {
            "type": "run_completed",
            "answer": answer,
            "memories": [memory.model_dump(mode="json") for memory in latest_memories],
            "runtime": "deepagents",
        }

    def _build_deepagents_tools(self) -> list[Any]:
        @tool
        def calculator(expression: str) -> str:
            """Safely evaluate an arithmetic expression."""

            tree = ast.parse(expression, mode="eval")
            value = CalculatorTool()._eval(tree.body)
            return f"{expression} = {value:g}"

        @tool
        def web_search_mock(query: str) -> str:
            """Mocked web search result used for demos and UI streaming."""

            return "\n".join(
                [
                    f"Search query: {query}",
                    "1. Deep Agents overview - planning, tools, memory, streaming.",
                    "2. FastAPI SSE pattern - use StreamingResponse with text/event-stream.",
                    "3. Next.js streaming client - parse SSE chunks over fetch().",
                ]
            )

        @tool
        def file_reader_mock(path: str = "README.md") -> str:
            """Read a short preview of a workspace file."""

            target = (ROOT_DIR / path).resolve()
            if not target.exists() or (ROOT_DIR not in target.parents and target != ROOT_DIR):
                return f"File not found or outside workspace: {path}"
            return target.read_text(encoding="utf-8")[:800]

        return [calculator, web_search_mock, file_reader_mock]

    def _compose_real_system_prompt(self, config: AgentConfig) -> str:
        parts = [
            "You are the real Deep Agents runtime behind Uliya Agent.",
            "Always think in steps and prefer using tools when they improve answer quality.",
            "Keep outputs concise and practical.",
        ]
        if config.skills_prompt:
            parts.append(f"Skills hint: {config.skills_prompt}")
        if config.retrieval_enabled:
            parts.append("The app may also surface uploaded file context outside the model.")
        return "\n".join(parts)

    def _map_deepagents_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        event_name = event.get("event", "")
        name = event.get("name", "")
        data = event.get("data", {})

        if event_name == "on_tool_start":
            return {
                "type": "tool_call",
                "tool_name": name,
                "arguments": data.get("input", {}),
            }
        if event_name == "on_tool_end":
            return {
                "type": "tool_result",
                "tool_name": name,
                "arguments": {},
                "output": self._normalize_text(data.get("output")),
            }
        if event_name == "on_chain_start" and name:
            return {
                "type": "step_started",
                "step": {
                    "id": name,
                    "title": name,
                    "kind": "reasoning",
                    "detail": self._normalize_text(data.get("input", {})),
                },
            }
        if event_name == "on_chain_end" and name:
            return {
                "type": "step_completed",
                "step": {
                    "id": name,
                    "title": name,
                    "kind": "reasoning",
                },
            }
        if event_name == "on_chat_model_stream":
            delta = self._extract_delta(data.get("chunk"))
            return {"type": "answer_delta", "delta": delta} if delta else None
        return None

    def _extract_delta(self, chunk: Any) -> str:
        if isinstance(chunk, AIMessageChunk):
            return self._normalize_text(chunk.content)
        return self._normalize_text(chunk)

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, BaseMessage):
            return self._normalize_text(value.content)
        if isinstance(value, list):
            return "".join(self._normalize_text(item) for item in value)
        if isinstance(value, dict):
            if "text" in value:
                return self._normalize_text(value["text"])
            if "content" in value:
                return self._normalize_text(value["content"])
            try:
                return json.dumps(value, ensure_ascii=False, default=str)
            except TypeError:
                return str(value)
        return str(value)
