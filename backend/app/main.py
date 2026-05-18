from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps import get_current_user_id
from app.routes import chat

api_router = APIRouter(prefix="/api")
api_router.include_router(chat.router)


def create_app() -> FastAPI:
    app = FastAPI(title="agentic-rag-sub-agents", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @api_router.get("/me")
    async def me(user_id: str = Depends(get_current_user_id)):
        return {"user_id": user_id}

    app.include_router(api_router)
    return app


app = create_app()
