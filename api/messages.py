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
    Message as DbMessage,
    MessageVisibility,
    ConversationParticipant
)

router = APIRouter(prefix="/api/messages", tags=["messages"])


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_type: int
    sender_id: Optional[int] = None
    content: str
    message_type: int = 1
    media_url: Optional[str] = None
    status: int = 1
    created_at: str


class MessageListResponse(BaseModel):
    success: bool = True
    messages: List[MessageResponse]
    total: int = 0
    page: int = 1
    limit: int = 20
    has_more: bool = False


class ApiResponse(BaseModel):
    success: bool = True
    message: str = ""


@router.get("/conversation/{conversation_id}", response_model=MessageListResponse)
def get_conversation_messages(
    conversation_id: int,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = crud.get_participant_by_user(db, conversation_id, current_user.id)
    
    if not participant or participant.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权限"
        )
    
    messages, total = crud.get_conversation_messages_for_user(
        db, conversation_id, current_user.id, page, limit
    )
    
    has_more = (page * limit) < total
    
    message_responses = [
        MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            sender_type=m.sender_type,
            sender_id=m.sender_id,
            content=m.content,
            message_type=m.message_type,
            media_url=m.media_url,
            status=m.status,
            created_at=m.created_at.isoformat() if m.created_at else ""
        ) for m in messages
    ]
    
    return MessageListResponse(
        success=True,
        messages=message_responses,
        total=total,
        page=page,
        limit=limit,
        has_more=has_more
    )


@router.delete("/{message_id}", response_model=ApiResponse)
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    message = crud.get_message_by_id(db, message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    participant = crud.get_participant_by_user(db, message.conversation_id, current_user.id)
    
    if not participant or participant.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此消息"
        )
    
    success = crud.delete_message_for_user(db, message_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    return ApiResponse(
        success=True,
        message="消息已删除"
    )


@router.put("/{message_id}/recall", response_model=ApiResponse)
def recall_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    message = crud.get_message_by_id(db, message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    if message.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权撤回此消息"
        )
    
    if message.status == 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息已撤回"
        )
    
    recalled = crud.recall_message(db, message_id)
    
    if not recalled:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="撤回消息失败"
        )
    
    return ApiResponse(
        success=True,
        message="消息已撤回"
    )
