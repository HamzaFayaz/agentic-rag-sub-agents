from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.deps import get_access_token, get_current_user_id
from app.services.ingestion import IngestionService
from app.services.supabase_client import SupabaseRepository

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    user_id: Annotated[str, Depends(get_current_user_id)],
    access_token: Annotated[str, Depends(get_access_token)],
):
    repo = SupabaseRepository(access_token)
    return repo.list_documents(user_id)


@router.post("/upload")
async def upload_document(
    file: Annotated[UploadFile, File()],
    user_id: Annotated[str, Depends(get_current_user_id)],
    access_token: Annotated[str, Depends(get_access_token)],
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing filename",
        )

    content = await file.read()
    repo = SupabaseRepository(access_token)
    service = IngestionService(repo)
    doc = await service.ingest_upload(user_id, file.filename, content)
    return {
        "id": doc["id"],
        "filename": doc["filename"],
        "status": doc["status"],
        "byte_size": doc["byte_size"],
        "error_message": doc.get("error_message"),
        "created_at": doc["created_at"],
    }


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user_id: Annotated[str, Depends(get_current_user_id)],
    access_token: Annotated[str, Depends(get_access_token)],
):
    repo = SupabaseRepository(access_token)
    doc = repo.get_document(document_id, user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    repo.delete_document(document_id, user_id)
