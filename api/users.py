from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from database.connection import get_db
from database import crud
from api.auth import get_current_user
from database.models import User
from models import UserResponse, ApiResponse

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        avatar=current_user.avatar,
        status=current_user.status,
        created_at=current_user.created_at
    )


@router.get("/{username}", response_model=UserResponse)
def get_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = crud.get_user_by_username(db, username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        status=user.status,
        created_at=user.created_at
    )


@router.get("/id/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = crud.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        status=user.status,
        created_at=user.created_at
    )


@router.get("", response_model=List[UserResponse])
def search_users(
    username: Optional[str] = Query(None, description="用户名搜索"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = crud.search_users(
        db=db,
        username=username,
        exclude_user_id=current_user.id
    )

    return [
        UserResponse(
            id=u.id,
            username=u.username,
            nickname=u.nickname,
            avatar=u.avatar,
            status=u.status,
            created_at=u.created_at
        ) for u in users
    ]
