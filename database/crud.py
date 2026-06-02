from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from datetime import datetime
from database.models import (
    User,
    Conversation,
    ConversationParticipant,
    Message,
    MessageVisibility,
    TokenBlacklist
)
from auth.password import hash_password


SENDER_TYPE_USER = 1
SENDER_TYPE_AI = 2
SENDER_TYPE_SYSTEM = 3

CONV_TYPE_AI = 1
CONV_TYPE_PRIVATE = 2


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


def search_users(
    db: Session,
    username: Optional[str] = None,
    exclude_user_id: Optional[int] = None
) -> List[User]:
    query = db.query(User).filter(User.status == 1)
    
    if username:
        query = query.filter(User.username.contains(username))
    
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    
    return query.order_by(User.username).all()


def create_conversation(
    db: Session,
    conv_type: int
) -> Conversation:
    conv = Conversation(type=conv_type)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def add_participant(
    db: Session,
    conversation_id: int,
    user_id: int,
    is_ai: int = 0,
    title: str = "新对话"
) -> ConversationParticipant:
    participant = ConversationParticipant(
        conversation_id=conversation_id,
        user_id=user_id,
        is_ai=is_ai,
        title=title
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def get_user_conversations(
    db: Session,
    user_id: int
) -> List[Tuple[Conversation, ConversationParticipant]]:
    result = (
        db.query(Conversation, ConversationParticipant)
        .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
        .filter(
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.is_deleted == 0
        )
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    
    return result


def get_conversation_by_id(db: Session, conv_id: int) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conv_id).first()


def get_participant_by_user(
    db: Session,
    conversation_id: int,
    user_id: int
) -> Optional[ConversationParticipant]:
    return (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id
        )
        .first()
    )


def get_or_create_ai_conversation(
    db: Session,
    user_id: int
) -> Tuple[Conversation, bool]:
    existing = (
        db.query(Conversation)
        .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
        .filter(
            Conversation.type == CONV_TYPE_AI,
            ConversationParticipant.user_id == user_id,
            ConversationParticipant.is_deleted == 0
        )
        .order_by(Conversation.updated_at.desc())
        .first()
    )
    
    if existing:
        return existing, False
    
    conv = create_conversation(db, CONV_TYPE_AI)
    
    user = get_user_by_id(db, user_id)
    title = f"{user.nickname or user.username} 的 AI 对话"
    
    add_participant(db, conv.id, user_id, is_ai=0, title=title)
    add_participant(db, conv.id, 0, is_ai=1, title="AI助手")
    
    return conv, True


def get_or_create_private_conversation(
    db: Session,
    user_id: int,
    target_user_id: int
) -> Tuple[Conversation, bool]:
    existing = (
        db.query(Conversation)
        .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
        .filter(
            Conversation.type == CONV_TYPE_PRIVATE,
            or_(
                ConversationParticipant.user_id == user_id,
                ConversationParticipant.user_id == target_user_id
            )
        )
        .group_by(Conversation.id)
        .having(func.count(func.distinct(ConversationParticipant.user_id)) == 2)
        .first()
    )
    
    if existing:
        return existing, False
    
    conv = create_conversation(db, CONV_TYPE_PRIVATE)
    
    user = get_user_by_id(db, user_id)
    target_user = get_user_by_id(db, target_user_id)
    
    add_participant(
        db, conv.id, user_id,
        title=f"与 {target_user.nickname or target_user.username} 的对话"
    )
    add_participant(
        db, conv.id, target_user_id,
        title=f"与 {user.nickname or user.username} 的对话"
    )
    
    return conv, True


def delete_conversation_for_user(
    db: Session,
    conversation_id: int,
    user_id: int
) -> bool:
    participant = get_participant_by_user(db, conversation_id, user_id)
    
    if not participant:
        return False
    
    participant.is_deleted = 1
    db.commit()
    
    return True


def update_participant_title(
    db: Session,
    conversation_id: int,
    user_id: int,
    title: str
) -> Optional[ConversationParticipant]:
    participant = get_participant_by_user(db, conversation_id, user_id)
    
    if not participant:
        return None
    
    participant.title = title
    db.commit()
    db.refresh(participant)
    
    return participant


def update_conversation_updated_at(
    db: Session,
    conversation_id: int
) -> Optional[Conversation]:
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        return None
    
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conv)
    
    return conv


def create_message_with_visibility(
    db: Session,
    conversation_id: int,
    sender_type: int,
    content: str,
    sender_id: Optional[int] = None,
    message_type: int = 1
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content,
        message_type=message_type
    )
    
    db.add(message)
    db.flush()
    
    participants = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.is_ai == 0
        )
        .all()
    )
    
    for p in participants:
        visibility = MessageVisibility(
            message_id=message.id,
            user_id=p.user_id
        )
        db.add(visibility)
    
    conv = get_conversation_by_id(db, conversation_id)
    if conv:
        conv.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    
    return message


def get_conversation_messages_for_user(
    db: Session,
    conversation_id: int,
    user_id: int,
    page: int = 1,
    limit: int = 50
) -> Tuple[List[Message], int]:
    query = (
        db.query(Message)
        .join(MessageVisibility, Message.id == MessageVisibility.message_id)
        .filter(
            Message.conversation_id == conversation_id,
            MessageVisibility.user_id == user_id,
            MessageVisibility.is_deleted == 0,
            Message.status == 1
        )
    )
    
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


def get_message_by_id(db: Session, message_id: int) -> Optional[Message]:
    return db.query(Message).filter(Message.id == message_id).first()


def delete_message_for_user(
    db: Session,
    message_id: int,
    user_id: int
) -> bool:
    visibility = (
        db.query(MessageVisibility)
        .filter(
            MessageVisibility.message_id == message_id,
            MessageVisibility.user_id == user_id
        )
        .first()
    )
    
    if not visibility:
        return False
    
    visibility.is_deleted = 1
    db.commit()
    
    return True


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


def get_user_id_by_username(db: Session, username: str) -> Optional[int]:
    user = get_user_by_username(db, username)
    return user.id if user else None
