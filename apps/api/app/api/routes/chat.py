from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Repository
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import answer_question

router = APIRouter(prefix="/repositories/{repo_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(repo_id: str, payload: ChatRequest, db: Session = Depends(get_db)):
    repo = db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.status != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Repository is not ready for chat (status: {repo.status})",
        )
    result = answer_question(repo_id, payload.question, top_k=payload.top_k)
    return ChatResponse(
        answer=result.answer,
        citations=[c.__dict__ for c in result.citations],
        provider=result.provider,
    )
