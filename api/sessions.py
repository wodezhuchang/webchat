from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from database import crud
from api.auth import get_current_user
from database.models import (
    User,
    ConversationParticipant,
    Conversation
)

router = APIRouter(prefix="/api/sessions", tags=["sessions-legacy"])


class SessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    session_type: int
    target_user_id: Optional[int] = None
    is_active: int = 1
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    success: bool = True
    sessions: List[SessionResponse]


class ApiResponse(BaseModel):
    success: bool = True
    message: str = ""


def conv_to_session_response(conv: Conversation, participant: ConversationParticipant) -> SessionResponse:
    target_user_id = None
    for p in conv.participants:
        if p.user_id != participant.user_id and p.is_ai == 0:
            target_user_id = p.user_id
            break
    
    return SessionResponse(
        id=conv.id,
        user_id=participant.user_id,
        title=participant.title,
        session_type=conv.type,
        target_user_id=target_user_id,
        is_active=1 if not participant.is_deleted else 0,
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else ""
    )


@router.get("", response_model=SessionListResponse)
def list_sessions(
    is_active: Optional[int] = Query(None, description="是否活跃"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participants = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.is_deleted == 0
        )
        .all()
    )
    
    sessions = []
    for p in participants:
        sessions.append(conv_to_session_response(p.conversation, p))
    
    sessions.sort(key=lambda x: x.updated_at, reverse=True)
    
    return SessionListResponse(sessions=sessions)


@router.post("/ai")
def create_ai_session(
    title: str = Query("新对话", description="会话标题"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv, is_new = crud.get_or_create_ai_conversation(db, current_user.id)
    
    if title != "新对话" and is_new:
        crud.update_participant_title(db, conv.id, current_user.id, title)
    
    participant = crud.get_participant_by_user(db, conv.id, current_user.id)
    
    return conv_to_session_response(conv, participant)


@router.post("/private")
def get_or_create_private_session(
    target_user_id: int = Query(..., description="目标用户ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能与自己创建私聊会话"
        )
    
    target_user = crud.get_user_by_id(db, target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在"
        )
    
    conv, _ = crud.get_or_create_private_conversation(
        db=db,
        user_id=current_user.id,
        target_user_id=target_user_id
    )
    
    participant = crud.get_participant_by_user(db, conv.id, current_user.id)
    
    return conv_to_session_response(conv, participant)


@router.put("/{session_id}")
def update_session(
    session_id: int,
    title: str = Query(..., description="新标题"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = crud.get_participant_by_user(db, session_id, current_user.id)
    
    if not participant or participant.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权限"
        )
    
    crud.update_participant_title(db, session_id, current_user.id, title)
    
    participant = crud.get_participant_by_user(db, session_id, current_user.id)
    return conv_to_session_response(participant.conversation, participant)


@router.delete("/{session_id}", response_model=ApiResponse)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = crud.get_participant_by_user(db, session_id, current_user.id)
    
    if not participant or participant.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权限"
        )
    
    success = crud.delete_conversation_for_user(db, session_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除失败"
        )
    
    return ApiResponse(success=True, message="会话已删除")
