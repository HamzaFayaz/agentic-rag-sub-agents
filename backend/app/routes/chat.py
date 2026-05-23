import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.deps import get_access_token, get_current_user_id
from app.services.chat import ChatService
from app.services.openai_client import OpenAIClient
from app.services.supabase_client import SupabaseRepository

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    thread_id: UUID
    content: str = Field(min_length=1)


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    access_token: Annotated[str, Depends(get_access_token)],
):
    repo = SupabaseRepository(access_token)
    service = ChatService(repo, OpenAIClient())

    async def event_generator():
        try:
            stream_result = await service.prepare_stream(
                body.thread_id, user_id, body.content
            )
            yield {
                "event": "sources",
                "data": json.dumps(
                    [source.to_dict() for source in stream_result.sources]
                ),
            }
            async for token in stream_result.token_iterator:
                yield {
                    "event": "token",
                    "data": json.dumps({"content": token}),
                }
            yield {"event": "done", "data": json.dumps({"status": "ok"})}
        except HTTPException as exc:
            yield {
                "event": "error",
                "data": json.dumps({"detail": exc.detail}),
            }
        except Exception as exc:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(exc)}),
            }

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
