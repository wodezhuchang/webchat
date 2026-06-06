from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from database.connection import get_db
from database import crud
from database.models import (
    User,
    Conversation,
    ConversationParticipant,
    Message
)
from api.auth import get_current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    id: int
    type: int
    title: str
    target_user_id: Optional[int] = None
    target_username: Optional[str] = None
    target_nickname: Optional[str] = None
    is_online: bool = False
    last_message: Optional[str] = None
    last_message_time: Optional[str] = None
    unread_count: int = 0
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    success: bool = True
    conversations: List[ConversationResponse]


def get_online_users():
    try:
        from main import online_users
        return online_users
    except Exception:
        return {}


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversations_data = []
    
    participants = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.is_deleted == 0
        )
        .all()
    )
    
    online_users = get_online_users()
    
    for p in participants:
        conv = p.conversation
        
        target_user = None
        is_online = False
        last_message = None
        last_message_time = None
        unread_count = 0
        
        if conv.type == 2:
            other_participant = (
                db.query(ConversationParticipant)
                .filter(
                    ConversationParticipant.conversation_id == conv.id,
                    ConversationParticipant.user_id != current_user.id,
                    ConversationParticipant.is_ai == 0
                )
                .first()
            )
            if other_participant:
                target_user = crud.get_user_by_id(db, other_participant.user_id)
                if target_user:
                    is_online = target_user.username in online_users
        
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        if last_msg:
            last_message = last_msg.content[:50] + "..." if len(last_msg.content) > 50 else last_msg.content
            last_message_time = last_msg.created_at.isoformat()
        
        unread_count = 0
        if p.last_read_message_id:
            from database.models import MessageVisibility
            unread_count = (
                db.query(Message)
                .join(MessageVisibility, Message.id == MessageVisibility.message_id)
                .filter(
                    Message.conversation_id == conv.id,
                    Message.id > p.last_read_message_id,
                    MessageVisibility.user_id == current_user.id,
                    MessageVisibility.is_deleted == 0
                )
                .count()
            )
        else:
            from database.models import MessageVisibility
            unread_count = (
                db.query(Message)
                .join(MessageVisibility, Message.id == MessageVisibility.message_id)
                .filter(
                    Message.conversation_id == conv.id,
                    MessageVisibility.user_id == current_user.id,
                    MessageVisibility.is_deleted == 0
                )
                .count()
            )
        
        conversations_data.append(ConversationResponse(
            id=conv.id,
            type=conv.type,
            title=p.title,
            target_user_id=target_user.id if target_user else None,
            target_username=target_user.username if target_user else None,
            target_nickname=target_user.nickname if target_user else None,
            is_online=is_online,
            last_message=last_message,
            last_message_time=last_message_time,
            unread_count=unread_count,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat()
        ))
    
    conversations_data.sort(key=lambda x: x.updated_at, reverse=True)
    
    return ConversationListResponse(conversations=conversations_data)


@router.post("/ai")
def create_ai_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = crud.create_ai_conversation(db, current_user.id)
    
    participant = crud.get_participant_by_user(db, conv.id, current_user.id)
    
    return {
        "success": True,
        "id": conv.id,
        "title": participant.title if participant else "新对话",
        "type": conv.type,
        "is_new": True
    }


@router.post("/private/{target_user_id}")
def get_or_create_private_conversation(
    target_user_id: int,
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
    
    conv, is_new = crud.get_or_create_private_conversation(
        db=db,
        user_id=current_user.id,
        target_user_id=target_user_id
    )
    
    participant = crud.get_participant_by_user(db, conv.id, current_user.id)
    
    return {
        "success": True,
        "id": conv.id,
        "title": participant.title if participant else f"与 {target_user.nickname or target_user.username} 的对话",
        "type": conv.type,
        "is_new": is_new,
        "target_user_id": target_user_id,
        "target_username": target_user.username,
        "target_nickname": target_user.nickname
    }


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = crud.get_participant_by_user(db, conversation_id, current_user.id)
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权限"
        )
    
    success = crud.delete_conversation_for_user(db, conversation_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除失败"
        )
    
    return {"success": True, "message": "会话已删除"}


@router.put("/{conversation_id}/title")
def update_conversation_title(
    conversation_id: int,
    title: str = Query(..., description="新标题"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = crud.update_participant_title(db, conversation_id, current_user.id, title)
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    return {"success": True, "title": title}


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    participant = crud.get_participant_by_user(db, conversation_id, current_user.id)
    
    if not participant or participant.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权限"
        )
    
    conv = participant.conversation
    target_user = None
    is_online = False
    online_users = get_online_users()
    
    if conv.type == 2:
        other_participant = (
            db.query(ConversationParticipant)
            .filter(
                ConversationParticipant.conversation_id == conv.id,
                ConversationParticipant.user_id != current_user.id,
                ConversationParticipant.is_ai == 0
            )
            .first()
        )
        if other_participant:
            target_user = crud.get_user_by_id(db, other_participant.user_id)
            if target_user:
                is_online = target_user.username in online_users
    
    return {
        "success": True,
        "conversation": {
            "id": conv.id,
            "type": conv.type,
            "title": participant.title,
            "target_user_id": target_user.id if target_user else None,
            "target_username": target_user.username if target_user else None,
            "target_nickname": target_user.nickname if target_user else None,
            "is_online": is_online,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat()
        }
    }
