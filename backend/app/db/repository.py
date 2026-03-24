import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import MemoryRecord, ThreadRecord, TraceRecord, UploadRecord
from app.models.schemas import MemoryItem, ThreadSummary, TraceItem, UploadItem


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentRepository:
    """Persistence boundary for threads, messages, traces, and uploads."""

    async def ensure_thread(
        self,
        session: AsyncSession,
        thread_id: str,
        title: str | None = None,
    ) -> ThreadRecord:
        thread = await session.get(ThreadRecord, thread_id)
        if thread is None:
            thread = ThreadRecord(
                id=thread_id,
                title=title or "New agent thread",
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(thread)
            await session.commit()
            await session.refresh(thread)
        return thread

    async def create_thread(
        self,
        session: AsyncSession,
        title: str | None = None,
    ) -> ThreadSummary:
        thread_id = str(uuid.uuid4())
        thread = await self.ensure_thread(session, thread_id, title=title)
        return self._to_thread_summary(thread)

    async def touch_thread(
        self,
        session: AsyncSession,
        thread_id: str,
        title: str | None = None,
    ) -> None:
        thread = await self.ensure_thread(session, thread_id, title=title)
        if title and thread.title == "New agent thread":
            thread.title = title
        thread.updated_at = utc_now()
        await session.commit()

    async def list_threads(self, session: AsyncSession) -> list[ThreadSummary]:
        result = await session.execute(
            select(ThreadRecord).order_by(desc(ThreadRecord.updated_at))
        )
        return [self._to_thread_summary(row) for row in result.scalars().all()]

    async def list_recent_messages(
        self,
        session: AsyncSession,
        thread_id: str,
        limit: int = 20,
    ) -> list[MemoryItem]:
        result = await session.execute(
            select(MemoryRecord)
            .where(MemoryRecord.thread_id == thread_id)
            .order_by(MemoryRecord.id.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return [
            MemoryItem(
                role=row.role,
                content=row.content,
                created_at=datetime.fromisoformat(row.created_at),
            )
            for row in rows
        ]

    async def append_message(
        self,
        session: AsyncSession,
        thread_id: str,
        role: str,
        content: str,
    ) -> None:
        await self.ensure_thread(session, thread_id, title=content[:60])
        session.add(
            MemoryRecord(
                thread_id=thread_id,
                role=role,
                content=content,
                created_at=utc_now(),
            )
        )
        await self.touch_thread(session, thread_id, title=content[:60])

    async def append_trace(
        self,
        session: AsyncSession,
        thread_id: str,
        run_id: str,
        event_type: str,
        payload: dict,
    ) -> None:
        session.add(
            TraceRecord(
                thread_id=thread_id,
                run_id=run_id,
                event_type=event_type,
                payload=json.dumps(payload, ensure_ascii=False),
                created_at=utc_now(),
            )
        )
        await session.commit()

    async def list_traces(
        self,
        session: AsyncSession,
        thread_id: str,
        limit: int = 80,
    ) -> list[TraceItem]:
        result = await session.execute(
            select(TraceRecord)
            .where(TraceRecord.thread_id == thread_id)
            .order_by(TraceRecord.id.desc())
            .limit(limit)
        )
        return [
            TraceItem(
                id=row.id,
                thread_id=row.thread_id,
                run_id=row.run_id,
                event_type=row.event_type,
                payload=json.loads(row.payload),
                created_at=datetime.fromisoformat(row.created_at),
            )
            for row in result.scalars().all()
        ]

    async def save_upload(
        self,
        session: AsyncSession,
        *,
        filename: str,
        stored_path: Path,
        preview: str,
        thread_id: str | None = None,
    ) -> UploadItem:
        record = UploadRecord(
            thread_id=thread_id,
            filename=filename,
            stored_path=str(stored_path),
            preview=preview,
            created_at=utc_now(),
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return self._to_upload_item(record)

    async def list_uploads(
        self,
        session: AsyncSession,
        thread_id: str | None = None,
    ) -> list[UploadItem]:
        query = select(UploadRecord).order_by(desc(UploadRecord.id))
        if thread_id:
            query = query.where(UploadRecord.thread_id == thread_id)
        result = await session.execute(query)
        return [self._to_upload_item(row) for row in result.scalars().all()]

    async def search_uploads(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 3,
    ) -> list[UploadItem]:
        tokens = [token for token in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(token) >= 3]
        uploads = await self.list_uploads(session)
        scored_matches: list[tuple[int, UploadItem]] = []
        for item in uploads:
            haystack = f"{item.filename} {item.preview}".lower()
            score = sum(1 for token in tokens if token in haystack)
            if score > 0:
                scored_matches.append((score, item))
        scored_matches.sort(key=lambda pair: pair[0], reverse=True)
        matches = [item for _, item in scored_matches]
        return matches[:limit]

    def _to_thread_summary(self, row: ThreadRecord) -> ThreadSummary:
        return ThreadSummary(
            id=row.id,
            title=row.title,
            created_at=datetime.fromisoformat(row.created_at),
            updated_at=datetime.fromisoformat(row.updated_at),
        )

    def _to_upload_item(self, row: UploadRecord) -> UploadItem:
        return UploadItem(
            id=row.id,
            thread_id=row.thread_id,
            filename=row.filename,
            stored_path=row.stored_path,
            preview=row.preview,
            created_at=datetime.fromisoformat(row.created_at),
        )
