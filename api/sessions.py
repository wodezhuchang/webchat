from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from database.connection import get_db
from database import crud
from api.auth import get_current_user
from database.models import User
from models import (
    SessionCreateRequest,
    SessionUpdateRequest,
    SessionResponse,
    SessionListResponse,
    ApiResponse
)

router = APIRouter(prefix="/sessions", tags=["会话管理"])


@router.post("", response_model=SessionResponse)
def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if request.session_type == 2 and request.target_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="私聊会话必须指定目标用户"
        )
    
    if request.session_type == 2:
        target_user = crud.get_user_by_id(db, request.target_user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标用户不存在"
            )
    
    session = crud.create_session(
        db=db,
        user_id=current_user.id,
        title=request.title,
        session_type=request.session_type,
        target_user_id=request.target_user_id
    )
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        session_type=session.session_type,
        target_user_id=session.target_user_id,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.get("", response_model=SessionListResponse)
def get_sessions(
    is_active: Optional[int] = Query(None, description="是否活跃: 1-活跃, 0-已结束"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = crud.get_user_sessions(db, current_user.id, is_active)
    
    session_responses = [
        SessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            session_type=s.session_type,
            target_user_id=s.target_user_id,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at
        ) for s in sessions
    ]
    
    return SessionListResponse(
        success=True,
        sessions=session_responses
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
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
            detail="无权访问此会话"
        )
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        session_type=session.session_type,
        target_user_id=session.target_user_id,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.put("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: int,
    request: SessionUpdateRequest,
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
            detail="无权修改此会话"
        )
    
    if request.title is not None:
        session = crud.update_session_title(db, session_id, request.title)
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        session_type=session.session_type,
        target_user_id=session.target_user_id,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.delete("/{session_id}", response_model=ApiResponse)
def delete_session(
    session_id: int,
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
            detail="无权删除此会话"
        )
    
    success = crud.delete_session(db, session_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除会话失败"
        )
    
    return ApiResponse(
        success=True,
        message="会话已删除"
    )
