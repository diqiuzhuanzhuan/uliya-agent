from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str = Field(min_length=1)


class AgentConfig(BaseModel):
    use_real_deepagents: bool = False
    deepagents_model: str = "gpt-4.1-mini"
    selected_tools: list[str] = Field(default_factory=list)
    memory_enabled: bool = True
    retrieval_enabled: bool = True
    skills_prompt: str | None = None


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    config: AgentConfig = Field(default_factory=AgentConfig)


class MemoryItem(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    trace: list[dict[str, Any]]
    memories: list[MemoryItem]


class ThreadSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class TraceItem(BaseModel):
    id: int
    thread_id: str
    run_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime


class UploadItem(BaseModel):
    id: int
    thread_id: str | None
    filename: str
    stored_path: str
    preview: str
    created_at: datetime


class CreateThreadRequest(BaseModel):
    title: str | None = None
