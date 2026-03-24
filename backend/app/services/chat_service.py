import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deep_agent import DeepAgentRuntime
from app.core.config import BACKEND_DIR
from app.db.repository import AgentRepository
from app.models.schemas import ChatRequest


class ChatService:
    """Application service that combines runtime execution with persistence."""

    def __init__(self) -> None:
        self.runtime = DeepAgentRuntime()
        self.repository = AgentRepository()
        self.upload_dir = BACKEND_DIR / "data" / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def stream_chat(
        self,
        request: ChatRequest,
        session: AsyncSession,
    ) -> AsyncIterator[dict]:
        run_id = str(uuid.uuid4())
        await self.repository.ensure_thread(
            session,
            request.thread_id,
            title=request.message[:60],
        )

        async for event in self.runtime.stream(request, session):
            event_with_run = {
                **event,
                "run_id": run_id,
            }
            await self.repository.append_trace(
                session,
                thread_id=request.thread_id,
                run_id=run_id,
                event_type=event["type"],
                payload=event_with_run,
            )
            yield event_with_run

    async def save_upload(
        self,
        session: AsyncSession,
        upload: UploadFile,
        thread_id: str | None,
    ):
        suffix = Path(upload.filename or "upload.txt").suffix or ".txt"
        target = self.upload_dir / f"{uuid.uuid4()}{suffix}"
        content = await upload.read()
        target.write_bytes(content)
        preview = content.decode("utf-8", errors="ignore")[:1200]
        return await self.repository.save_upload(
            session,
            filename=upload.filename or target.name,
            stored_path=target,
            preview=preview,
            thread_id=thread_id,
        )
