from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.events import sse_pack
from app.db.database import get_session
from app.db.repository import AgentRepository
from app.models.schemas import AgentConfig, ChatRequest, CreateThreadRequest
from app.services.chat_service import ChatService


router = APIRouter()
service = ChatService()
repository = AgentRepository()
settings = get_settings()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config")
async def get_agent_config() -> JSONResponse:
    return JSONResponse(
        {
            "appName": settings.app_name,
            "defaultConfig": AgentConfig(
                use_real_deepagents=settings.use_real_deepagents,
                deepagents_model=settings.openai_model,
                selected_tools=["calculator", "web_search_mock", "file_reader_mock"],
                memory_enabled=True,
                retrieval_enabled=True,
                skills_prompt="Future entry point for prompt packs, RAG policies, and reusable workflows.",
            ).model_dump(mode="json"),
        }
    )


@router.get("/threads")
async def list_threads(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    return JSONResponse(
        {"items": [item.model_dump(mode="json") for item in await repository.list_threads(session)]}
    )


@router.post("/threads")
async def create_thread(
    payload: CreateThreadRequest,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    thread = await repository.create_thread(session, payload.title)
    return JSONResponse(thread.model_dump(mode="json"))


@router.get("/threads/{thread_id}/messages")
async def list_thread_messages(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    items = await repository.list_recent_messages(session, thread_id, limit=40)
    return JSONResponse({"items": [item.model_dump(mode="json") for item in items]})


@router.get("/threads/{thread_id}/traces")
async def list_thread_traces(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    items = await repository.list_traces(session, thread_id)
    return JSONResponse({"items": [item.model_dump(mode="json") for item in items]})


@router.get("/uploads")
async def list_uploads(
    thread_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    items = await repository.list_uploads(session, thread_id)
    return JSONResponse({"items": [item.model_dump(mode="json") for item in items]})


@router.post("/uploads")
async def upload_file(
    file: UploadFile = File(...),
    thread_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    item = await service.save_upload(session, file, thread_id)
    return JSONResponse(item.model_dump(mode="json"))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    async def event_generator():
        async for event in service.stream_chat(request, session):
            yield sse_pack("agent_event", event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
