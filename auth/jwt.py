import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-please-change-this-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_expires_in(token: str) -> int:
    payload = decode_token(token)
    if not payload:
        return 0
    
    exp = payload.get("exp")
    if not exp:
        return 0
    
    now = datetime.now(timezone.utc).timestamp()
    remaining = int(exp - now)
    
    return max(0, remaining)


def is_token_valid(token: str) -> bool:
    payload = decode_token(token)
    return payload is not None


def get_user_id_from_token(token: str) -> Optional[int]:
    payload = decode_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return None
    return None


def get_username_from_token(token: str) -> Optional[str]:
    payload = decode_token(token)
    if not payload:
        return None
    
    return payload.get("username")


def get_token_type(token: str) -> Optional[str]:
    payload = decode_token(token)
    if not payload:
        return None
    
    return payload.get("type")
