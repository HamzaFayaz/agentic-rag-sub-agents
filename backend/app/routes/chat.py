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
            async for stream_event in service.stream_turn(
                body.thread_id,
                user_id,
                body.content,
                user_jwt=access_token,
            ):
                if stream_event.event == "sources":
                    yield {
                        "event": "sources",
                        "data": json.dumps(stream_event.data["sources"]),
                    }
                elif stream_event.event == "tool_start":
                    yield {
                        "event": "tool_start",
                        "data": json.dumps(stream_event.data),
                    }
                elif stream_event.event == "tool_end":
                    yield {
                        "event": "tool_end",
                        "data": json.dumps(stream_event.data),
                    }
                elif stream_event.event == "token":
                    yield {
                        "event": "token",
                        "data": json.dumps(stream_event.data),
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
