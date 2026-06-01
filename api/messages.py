from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from database.connection import get_db
from database import crud
from api.auth import get_current_user
from database.models import User
from models import (
    MessageResponse,
    MessageListResponse,
    ApiResponse
)

router = APIRouter(prefix="/messages", tags=["消息管理"])


@router.get("/session/{session_id}", response_model=MessageListResponse)
def get_session_messages(
    session_id: int,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = crud.get_session_by_id(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话的消息"
        )
    
    messages, total = crud.get_session_messages(
        db, session_id, page, limit, status=1
    )
    
    has_more = (page * limit) < total
    
    message_responses = [
        MessageResponse(
            id=m.id,
            session_id=m.session_id,
            sender_type=m.sender_type,
            sender_id=m.sender_id,
            content=m.content,
            message_type=m.message_type,
            media_url=m.media_url,
            status=m.status,
            created_at=m.created_at
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
def recall_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from database.models import Message as DbMessage
    
    message = db.query(DbMessage).filter(DbMessage.id == message_id).first()
    
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
