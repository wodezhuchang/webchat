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
    
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_username", "username"),
        Index("idx_status", "status"),
    )


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="会话ID")
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    title = Column(String(100), default="新对话", comment="会话标题")
    session_type = Column(SmallInteger, default=1, comment="类型: 1-AI对话, 2-私聊")
    target_user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="私聊目标用户ID"
    )
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    is_active = Column(SmallInteger, default=1, comment="是否活跃: 1-活跃, 0-已结束")
    
    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_target_user", "target_user_id"),
        Index("idx_updated_at", "updated_at"),
    )


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="消息ID")
    session_id = Column(BigInteger, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, comment="会话ID")
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
    
    session = relationship("Session", back_populates="messages")
    
    __table_args__ = (
        Index("idx_session_id", "session_id"),
        Index("idx_sender_id", "sender_id"),
        Index("idx_created_at", "created_at"),
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
