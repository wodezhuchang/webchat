from datetime import datetime
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    SmallInteger,
    DateTime,
    ForeignKey,
    Index
)
from sqlalchemy.orm import relationship
from database.connection import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    nickname = Column(String(50), nullable=True, comment="昵称")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    status = Column(SmallInteger, default=1, comment="状态: 1-正常, 0-禁用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    
    participants = relationship("ConversationParticipant", back_populates="user")
    
    __table_args__ = (
        Index("idx_username", "username"),
        Index("idx_status", "status"),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="会话ID")
    type = Column(SmallInteger, default=1, comment="类型: 1-AI对话, 2-私聊")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    
    participants = relationship("ConversationParticipant", back_populates="conversation")
    messages = relationship("Message", back_populates="conversation")
    
    __table_args__ = (
        Index("idx_type", "type"),
        Index("idx_updated_at", "updated_at"),
    )


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话ID"
    )
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID"
    )
    is_ai = Column(SmallInteger, default=0, comment="是否AI: 0-用户, 1-AI")
    title = Column(String(100), default="新对话", comment="用户自定义会话标题")
    is_hidden = Column(SmallInteger, default=0, comment="是否隐藏: 0-显示, 1-隐藏")
    is_deleted = Column(SmallInteger, default=0, comment="是否删除: 0-未删除, 1-已删除")
    joined_at = Column(DateTime, default=datetime.utcnow, comment="加入时间")
    last_read_message_id = Column(BigInteger, nullable=True, comment="最后已读消息ID")
    
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="participants")
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_conversation_id", "conversation_id"),
        Index("idx_is_deleted", "is_deleted"),
    )


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="消息ID")
    conversation_id = Column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="会话ID"
    )
    sender_type = Column(SmallInteger, nullable=False, comment="发送者类型: 1-用户, 2-AI, 3-系统")
    sender_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="发送者用户ID"
    )
    content = Column(Text, nullable=False, comment="消息内容")
    message_type = Column(SmallInteger, default=1, comment="消息类型: 1-文本, 2-图片, 3-文件")
    media_url = Column(String(500), nullable=True, comment="媒体文件URL")
    status = Column(SmallInteger, default=1, comment="状态: 1-正常, 2-已撤回")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    conversation = relationship("Conversation", back_populates="messages")
    visibility = relationship("MessageVisibility", back_populates="message")
    
    __table_args__ = (
        Index("idx_conversation_id", "conversation_id"),
        Index("idx_sender_id", "sender_id"),
        Index("idx_created_at", "created_at"),
    )


class MessageVisibility(Base):
    __tablename__ = "message_visibility"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        comment="消息ID"
    )
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户ID"
    )
    is_hidden = Column(SmallInteger, default=0, comment="是否隐藏: 0-可见, 1-隐藏")
    is_deleted = Column(SmallInteger, default=0, comment="是否删除: 0-未删除, 1-已删除")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    
    message = relationship("Message", back_populates="visibility")
    
    __table_args__ = (
        Index("idx_message_id", "message_id"),
        Index("idx_user_id", "user_id"),
    )


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token = Column(String(500), unique=True, nullable=False, comment="JWT Token")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    __table_args__ = (
        Index("idx_token", "token"),
        Index("idx_expires_at", "expires_at"),
    )
