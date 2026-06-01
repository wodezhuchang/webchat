from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
from database.models import User, Session as DbSession, Message, TokenBlacklist
from auth.password import hash_password


def create_user(
    db: Session,
    username: str,
    password: str,
    nickname: Optional[str] = None
) -> User:
    password_hash = hash_password(password)
    
    user = User(
        username=username,
        password_hash=password_hash,
        nickname=nickname or username,
        status=1
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def update_user_profile(
    db: Session,
    user_id: int,
    nickname: Optional[str] = None,
    avatar: Optional[str] = None
) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    if nickname is not None:
        user.nickname = nickname
    if avatar is not None:
        user.avatar = avatar
    
    db.commit()
    db.refresh(user)
    
    return user


def create_session(
    db: Session,
    user_id: int,
    title: str = "新对话",
    session_type: int = 1,
    target_user_id: Optional[int] = None
) -> DbSession:
    session = DbSession(
        user_id=user_id,
        title=title,
        session_type=session_type,
        target_user_id=target_user_id,
        is_active=1
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


def get_user_sessions(
    db: Session,
    user_id: int,
    is_active: Optional[int] = None
) -> List[DbSession]:
    query = db.query(DbSession).filter(DbSession.user_id == user_id)
    
    if is_active is not None:
        query = query.filter(DbSession.is_active == is_active)
    
    return query.order_by(DbSession.updated_at.desc()).all()


def get_session_by_id(db: Session, session_id: int) -> Optional[DbSession]:
    return db.query(DbSession).filter(DbSession.id == session_id).first()


def update_session_title(
    db: Session,
    session_id: int,
    title: str
) -> Optional[DbSession]:
    session = get_session_by_id(db, session_id)
    if not session:
        return None
    
    session.title = title
    db.commit()
    db.refresh(session)
    
    return session


def deactivate_session(db: Session, session_id: int) -> Optional[DbSession]:
    session = get_session_by_id(db, session_id)
    if not session:
        return None
    
    session.is_active = 0
    db.commit()
    db.refresh(session)
    
    return session


def delete_session(db: Session, session_id: int) -> bool:
    session = get_session_by_id(db, session_id)
    if not session:
        return False
    
    db.delete(session)
    db.commit()
    
    return True


def create_message(
    db: Session,
    session_id: int,
    sender_type: int,
    content: str,
    sender_id: Optional[int] = None,
    message_type: int = 1,
    media_url: Optional[str] = None
) -> Message:
    message = Message(
        session_id=session_id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        media_url=media_url,
        status=1
    )
    
    db.add(message)
    
    session = get_session_by_id(db, session_id)
    if session:
        session.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    
    return message


def get_session_messages(
    db: Session,
    session_id: int,
    page: int = 1,
    limit: int = 20,
    status: Optional[int] = 1
) -> Tuple[List[Message], int]:
    query = db.query(Message).filter(Message.session_id == session_id)
    
    if status is not None:
        query = query.filter(Message.status == status)
    
    total = query.count()
    
    offset = (page - 1) * limit
    messages = (
        query.order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    messages.reverse()
    
    return messages, total


def recall_message(db: Session, message_id: int) -> Optional[Message]:
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        return None
    
    message.status = 2
    db.commit()
    db.refresh(message)
    
    return message


def add_token_to_blacklist(
    db: Session,
    token: str,
    expires_at: datetime
) -> TokenBlacklist:
    blacklisted = TokenBlacklist(
        token=token,
        expires_at=expires_at
    )
    
    db.add(blacklisted)
    db.commit()
    
    return blacklisted


def is_token_blacklisted(db: Session, token: str) -> bool:
    return (
        db.query(TokenBlacklist)
        .filter(TokenBlacklist.token == token)
        .first() is not None
    )
