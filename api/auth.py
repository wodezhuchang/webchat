from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database.connection import get_db
from database import crud
from auth.password import verify_password
from auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_token,
    get_token_expires_in,
    is_token_valid
)
from models import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthLoginResponse,
    AuthRefreshResponse,
    AuthLogoutResponse,
    ApiResponse
)
from database.models import User

router = APIRouter(prefix="/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token"
        )
    
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请使用 Access Token"
        )
    
    if crud.is_token_blacklisted(db, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已失效"
        )
    
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return user


@router.post("/register", response_model=AuthLoginResponse)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次密码输入不一致"
        )
    
    existing_user = crud.get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    user = crud.create_user(
        db, request.username, request.password, request.nickname)
    
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "username": user.username})
    expires_in = get_token_expires_in(access_token)
    
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        status=user.status,
        created_at=user.created_at
    )
    
    return AuthLoginResponse(
        success=True,
        message="注册成功",
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user_response
    )


@router.post("/login", response_model=AuthLoginResponse)
def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "username": user.username})
    expires_in = get_token_expires_in(access_token)
    
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        status=user.status,
        created_at=user.created_at
    )
    
    return AuthLoginResponse(
        success=True,
        message="登录成功",
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user_response
    )


@router.post("/refresh", response_model=AuthRefreshResponse)
def refresh_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    if not is_token_valid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token"
        )
    
    if crud.is_token_blacklisted(db, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已失效"
        )
    
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请使用 Refresh Token"
        )
    
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token"
        )
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    new_access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
    new_expires_in = get_token_expires_in(new_access_token)
    
    return AuthRefreshResponse(
        success=True,
        access_token=new_access_token,
        token_type="bearer",
        expires_in=new_expires_in
    )


@router.post("/logout", response_model=AuthLogoutResponse)
def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payload = decode_token(token)
    
    if payload:
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            crud.add_token_to_blacklist(db, token, expires_at)
    
    return AuthLogoutResponse(
        success=True,
        message="登出成功"
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        avatar=current_user.avatar,
        status=current_user.status,
        created_at=current_user.created_at
    )
