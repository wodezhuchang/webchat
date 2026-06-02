# 私聊功能重新设计方案

## 一、问题分析

### 1.1 当前存在的问题

| 问题 | 描述 | 影响 |
|------|------|------|
| 会话设计缺陷 | Session 表只有一条记录，user_id 和 target_user_id 是单向的 | 用户 A 删除会话后，用户 B 也看不到 |
| 消息归属不明确 | 消息只属于一个 session_id | 删除会话时消息一起被删除 |
| 前端逻辑混乱 | AI 对话和私聊使用不同的状态管理（sessionStore vs chatStore） | 代码难以维护 |
| 在线用户列表显示问题 | 只显示在线用户，不显示有历史聊天记录的用户 | 无法查看离线用户的历史记录 |
| 删除会话问题 | 直接删除 session，级联删除 messages | 影响对话双方 |

### 1.2 具体问题举例

**当前数据库示例：**
```
sessions 表:
- id=3, user_id=3 (yangxiaobao), target_user_id=2 (yangdabao), 类型=私聊

如果 yangdabao 删除 session=3:
- sessions 表中该记录被删除
- messages 表中 session_id=3 的所有消息被级联删除
- yangxiaobao 也看不到这些消息了 ❌
```

---

## 二、数据库重新设计

### 2.1 新的表结构设计

#### 2.1.1 新增表：conversations（会话）

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会话ID',
    type SMALLINT NOT NULL DEFAULT 1 COMMENT '类型: 1-AI对话, 2-私聊',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_type (type),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话主表';
```

#### 2.1.2 新增表：conversation_participants（会话参与者）

```sql
CREATE TABLE IF NOT EXISTS conversation_participants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    conversation_id BIGINT NOT NULL COMMENT '会话ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    is_ai SMALLINT DEFAULT 0 COMMENT '是否AI: 0-用户, 1-AI',
    title VARCHAR(100) DEFAULT '新对话' COMMENT '用户自定义会话标题',
    is_hidden SMALLINT DEFAULT 0 COMMENT '是否隐藏: 0-显示, 1-隐藏',
    is_deleted SMALLINT DEFAULT 0 COMMENT '是否删除: 0-未删除, 1-已删除',
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
    last_read_message_id BIGINT DEFAULT NULL COMMENT '最后已读消息ID',
    
    PRIMARY KEY (id),
    UNIQUE KEY uk_conversation_user (conversation_id, user_id),
    INDEX idx_user_id (user_id),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_is_deleted (is_deleted),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话参与者';
```

#### 2.1.3 新增表：messages（消息，保留但改进）

```sql
CREATE TABLE IF NOT EXISTS messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
    conversation_id BIGINT NOT NULL COMMENT '会话ID',
    sender_type SMALLINT NOT NULL COMMENT '发送者类型: 1-用户, 2-AI, 3-系统',
    sender_id BIGINT COMMENT '发送者用户ID',
    content TEXT NOT NULL COMMENT '消息内容',
    message_type SMALLINT DEFAULT 1 COMMENT '消息类型: 1-文本, 2-图片, 3-文件',
    media_url VARCHAR(500) COMMENT '媒体文件URL',
    status SMALLINT DEFAULT 1 COMMENT '状态: 1-正常, 2-已撤回',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';
```

#### 2.1.4 新增表：message_visibility（消息可见性）

```sql
CREATE TABLE IF NOT EXISTS message_visibility (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    message_id BIGINT NOT NULL COMMENT '消息ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    is_hidden SMALLINT DEFAULT 0 COMMENT '是否隐藏: 0-可见, 1-隐藏',
    is_deleted SMALLINT DEFAULT 0 COMMENT '是否删除: 0-未删除, 1-已删除',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_message_user (message_id, user_id),
    INDEX idx_user_id (user_id),
    INDEX idx_message_id (message_id),
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息可见性';
```

### 2.2 新旧表对比

| 特性 | 旧设计 | 新设计 |
|------|--------|--------|
| 会话归属 | 单向（user_id -> target_user_id） | 双向（participants 表） |
| 删除会话 | 直接删除 session，消息级联删除 | 仅删除参与者的 is_deleted 标记 |
| 会话标题 | 统一 title | 每个用户可自定义 title |
| 消息删除 | 直接删除 message | 消息可见性表控制 |
| 未读消息 | 无 | 支持 last_read_message_id |

### 2.3 数据迁移 SQL

```sql
-- 创建新表
-- ... (上面的建表 SQL)

-- 迁移 AI 对话数据
INSERT INTO conversations (id, type, created_at, updated_at)
SELECT id, 1, created_at, updated_at FROM sessions WHERE session_type = 1;

INSERT INTO conversation_participants (conversation_id, user_id, is_ai, title, is_hidden, is_deleted, joined_at)
SELECT 
    s.id, 
    s.user_id, 
    0, 
    s.title, 
    0, 
    0,
    s.created_at
FROM sessions s WHERE s.session_type = 1;

INSERT INTO conversation_participants (conversation_id, user_id, is_ai, title, is_hidden, is_deleted, joined_at)
SELECT 
    s.id, 
    0, 
    1, 
    'AI助手', 
    0, 
    0,
    s.created_at
FROM sessions s WHERE s.session_type = 1;

-- 迁移私聊数据
INSERT INTO conversations (id, type, created_at, updated_at)
SELECT id, 2, created_at, updated_at FROM sessions WHERE session_type = 2;

-- 为私聊会话添加两个参与者
INSERT INTO conversation_participants (conversation_id, user_id, is_ai, title, is_hidden, is_deleted, joined_at)
SELECT 
    s.id, 
    s.user_id, 
    0, 
    CONCAT('与 ', u.nickname, ' 的对话'), 
    0, 
    0,
    s.created_at
FROM sessions s 
JOIN users u ON s.target_user_id = u.id
WHERE s.session_type = 2;

INSERT INTO conversation_participants (conversation_id, user_id, is_ai, title, is_hidden, is_deleted, joined_at)
SELECT 
    s.id, 
    s.target_user_id, 
    0, 
    CONCAT('与 ', u.nickname, ' 的对话'), 
    0, 
    0,
    s.created_at
FROM sessions s 
JOIN users u ON s.user_id = u.id
WHERE s.session_type = 2;

-- 迁移消息数据
INSERT INTO messages (id, conversation_id, sender_type, sender_id, content, message_type, media_url, status, created_at)
SELECT id, session_id, sender_type, sender_id, content, message_type, media_url, status, created_at
FROM messages;

-- 为每条消息创建可见性记录（私聊消息双方都可见，AI消息只有用户可见）
INSERT INTO message_visibility (message_id, user_id, is_hidden, is_deleted)
SELECT 
    m.id,
    cp.user_id,
    0,
    0
FROM messages m
JOIN conversation_participants cp ON m.conversation_id = cp.conversation_id
WHERE cp.is_ai = 0;
```

---

## 三、后端修改建议

### 3.1 新增 ORM 模型

#### database/models.py 新增

```python
class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    type = Column(SmallInteger, default=1, comment="类型: 1-AI对话, 2-私聊")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    participants = relationship("ConversationParticipant", back_populates="conversation")
    messages = relationship("Message", back_populates="conversation")


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    is_ai = Column(SmallInteger, default=0)
    title = Column(String(100), default="新对话")
    is_hidden = Column(SmallInteger, default=0)
    is_deleted = Column(SmallInteger, default=0)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_message_id = Column(BigInteger, nullable=True)
    
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(SmallInteger, nullable=False)
    sender_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    message_type = Column(SmallInteger, default=1)
    media_url = Column(String(500), nullable=True)
    status = Column(SmallInteger, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")
    visibility = relationship("MessageVisibility", back_populates="message")


class MessageVisibility(Base):
    __tablename__ = "message_visibility"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, ForeignKey("messages.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    is_hidden = Column(SmallInteger, default=0)
    is_deleted = Column(SmallInteger, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    message = relationship("Message", back_populates="visibility")
    user = relationship("User")
```

### 3.2 新增 CRUD 函数

#### database/crud.py 新增函数

```python
# ============================================
# Conversation 相关
# ============================================

def create_conversation(
    db: Session,
    conv_type: int
) -> Conversation:
    """创建新会话"""
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
    """添加参与者"""
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
    """获取用户的所有会话（包括 AI 和私聊）"""
    from sqlalchemy import and_
    
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


def get_or_create_private_conversation(
    db: Session,
    user_id: int,
    target_user_id: int
) -> Tuple[Conversation, bool]:
    """获取或创建私聊会话"""
    from sqlalchemy import and_, or_
    
    existing = (
        db.query(Conversation)
        .join(ConversationParticipant, Conversation.id == ConversationParticipant.conversation_id)
        .filter(
            Conversation.type == 2,
            or_(
                and_(
                    ConversationParticipant.user_id == user_id,
                    ConversationParticipant.is_deleted == 0
                ),
                and_(
                    ConversationParticipant.user_id == target_user_id,
                    ConversationParticipant.is_deleted == 0
                )
            )
        )
        .group_by(Conversation.id)
        .having(func.count(DISTINCT ConversationParticipant.user_id) == 2)
        .first()
    )
    
    if existing:
        return existing, False
    
    conv = create_conversation(db, conv_type=2)
    
    user = get_user_by_id(db, user_id)
    target_user = get_user_by_id(db, target_user_id)
    
    add_participant(db, conv.id, user_id, title=f"与 {target_user.nickname or target_user.username} 的对话")
    add_participant(db, conv.id, target_user_id, title=f"与 {user.nickname or user.username} 的对话")
    
    return conv, True


def delete_conversation_for_user(
    db: Session,
    conversation_id: int,
    user_id: int
) -> bool:
    """为用户删除会话（软删除，不影响对方）"""
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id
        )
        .first()
    )
    
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
    """更新用户的会话标题"""
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id
        )
        .first()
    )
    
    if not participant:
        return None
    
    participant.title = title
    db.commit()
    db.refresh(participant)
    
    return participant


# ============================================
# Message 相关
# ============================================

def create_message_with_visibility(
    db: Session,
    conversation_id: int,
    sender_type: int,
    content: str,
    sender_id: Optional[int] = None
) -> Message:
    """创建消息并设置可见性"""
    message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content
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
    
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
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
    """获取用户可见的会话消息"""
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


def delete_message_for_user(
    db: Session,
    message_id: int,
    user_id: int
) -> bool:
    """为用户删除消息（软删除，不影响对方）"""
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
```

### 3.3 新增/修改 API 接口

#### api/conversations.py（新建）

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from database.connection import get_db
from database import crud
from database.models import User
from auth.jwt import get_current_user

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


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的所有会话列表（AI + 私聊）"""
    from database.models import Conversation, ConversationParticipant, Message
    
    conversations_data = []
    
    participants = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.is_deleted == 0
        )
        .all()
    )
    
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
                    ConversationParticipant.user_id != current_user.id
                )
                .first()
            )
            if other_participant:
                target_user = crud.get_user_by_id(db, other_participant.user_id)
                if target_user:
                    from main import online_users
                    is_online = target_user.username in online_users
        
        # 获取最后一条消息
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        if last_msg:
            last_message = last_msg.content[:50] + "..." if len(last_msg.content) > 50 else last_msg.content
            last_message_time = last_msg.created_at.isoformat()
        
        # 计算未读消息数
        if p.last_read_message_id:
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


@router.post("/private/{target_user_id}")
def get_or_create_private_conversation_api(
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取或创建私聊会话"""
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
    
    return {
        "success": True,
        "conversation_id": conv.id,
        "title": f"与 {target_user.nickname or target_user.username} 的对话",
        "is_new": is_new
    }


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除会话（仅对当前用户）"""
    success = crud.delete_conversation_for_user(db, conversation_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权限"
        )
    
    return {"success": True, "message": "会话已删除"}


@router.put("/{conversation_id}/title")
def update_conversation_title(
    conversation_id: int,
    title: str = Query(..., description="新标题"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新会话标题"""
    participant = crud.update_participant_title(db, conversation_id, current_user.id, title)
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    return {"success": True, "title": title}
```

#### api/messages.py 修改

```python
# 新增：删除消息（软删除，只对当前用户）
@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除消息（仅对当前用户）"""
    success = crud.delete_message_for_user(db, message_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在或无权限"
        )
    
    return {"success": True, "message": "消息已删除"}
```

### 3.4 WebSocket 路由修改

#### main.py 中的 WebSocket 路由

```python
# 私聊消息处理
elif message_type == "user":
    to_user = data.get("to")
    conversation_id = data.get("conversation_id")
    
    db = SessionLocal()
    try:
        current_user_id = crud.get_user_id_by_username(db, username)
        target_user = crud.get_user_by_username(db, to_user)
        
        if not target_user:
            await websocket.send_json({"type": "error", "content": f"用户 {to_user} 不存在"})
            continue
        
        # 获取或创建会话
        if conversation_id:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conv:
                await websocket.send_json({"type": "error", "content": "会话不存在"})
                continue
        else:
            conv, _ = crud.get_or_create_private_conversation(
                db=db,
                user_id=current_user_id,
                target_user_id=target_user.id
            )
            conversation_id = conv.id
        
        # 创建消息
        message = crud.create_message_with_visibility(
            db=db,
            conversation_id=conversation_id,
            sender_type=1,
            content=content,
            sender_id=current_user_id
        )
        
        # 推送给目标用户
        if to_user in online_users:
            target_ws = online_users[to_user]
            await target_ws.send_json({
                "type": "private",
                "from": username,
                "from_id": current_user_id,
                "content": content,
                "conversation_id": conversation_id,
                "message_id": message.id,
                "timestamp": message.created_at.isoformat()
            })
            await websocket.send_json({
                "type": "info",
                "content": f"已发送给 {to_user}",
                "conversation_id": conversation_id,
                "message_id": message.id,
                "timestamp": message.created_at.isoformat()
            })
        else:
            await websocket.send_json({
                "type": "info",
                "content": f"用户 {to_user} 不在线，消息已留存",
                "conversation_id": conversation_id,
                "message_id": message.id,
                "timestamp": message.created_at.isoformat()
            })
    
    finally:
        db.close()
```

---

## 四、前端修改建议

### 4.1 统一状态管理

#### stores/conversation.ts（新建）

```typescript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Conversation, Message } from '@/types';
import { conversationApi } from '@/services/conversation';
import { messageApi } from '@/services/message';

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref<Conversation[]>([]);
  const currentConversationId = ref<number | null>(null);
  const currentConversation = ref<Conversation | null>(null);
  const messages = ref<Message[]>([]);
  const isLoading = ref<boolean>(false);
  const isLoadingMessages = ref<boolean>(false);
  const error = ref<string | null>(null);

  const aiConversations = computed(() =>
    conversations.value.filter(c => c.type === 1)
  );

  const privateConversations = computed(() =>
    conversations.value.filter(c => c.type === 2)
  );

  const loadConversations = async (): Promise<void> => {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await conversationApi.list();
      conversations.value = response.conversations;
    } catch (err: any) {
      error.value = err?.message || '加载会话失败';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const selectConversation = async (conversationId: number | null): Promise<void> => {
    currentConversationId.value = conversationId;

    if (conversationId === null) {
      currentConversation.value = null;
      messages.value = [];
      return;
    }

    const conv = conversations.value.find(c => c.id === conversationId);
    if (conv) {
      currentConversation.value = conv;
      await loadMessages(conversationId);
    }
  };

  const loadMessages = async (conversationId: number): Promise<void> => {
    isLoadingMessages.value = true;
    messages.value = [];

    try {
      const response = await messageApi.getByConversation(conversationId, {
        page: 1,
        limit: 50
      });
      messages.value = response.messages.map(msg => ({
        id: msg.id,
        role: msg.sender_type === 1 ? 'user' : (msg.sender_type === 2 ? 'assistant' : 'system'),
        content: msg.content,
        sender_id: msg.sender_id,
        timestamp: new Date(msg.created_at)
      }));
    } catch (err) {
      console.error('加载消息失败:', err);
    } finally {
      isLoadingMessages.value = false;
    }
  };

  const deleteConversation = async (conversationId: number): Promise<void> => {
    try {
      await conversationApi.delete(conversationId);
      conversations.value = conversations.value.filter(c => c.id !== conversationId);
      
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = null;
        currentConversation.value = null;
        messages.value = [];
      }
    } catch (err) {
      console.error('删除会话失败:', err);
      throw err;
    }
  };

  const deleteMessage = async (messageId: number): Promise<void> => {
    try {
      await messageApi.delete(messageId);
      messages.value = messages.value.filter(m => m.id !== messageId);
    } catch (err) {
      console.error('删除消息失败:', err);
      throw err;
    }
  };

  const getOrCreatePrivateConversation = async (
    targetUserId: number
  ): Promise<Conversation> => {
    const existing = conversations.value.find(
      c => c.type === 2 && c.target_user_id === targetUserId
    );

    if (existing) {
      return existing;
    }

    const response = await conversationApi.getOrCreatePrivate(targetUserId);
    const newConv: Conversation = {
      id: response.conversation_id,
      type: 2,
      title: response.title,
      target_user_id: targetUserId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    conversations.value.unshift(newConv);
    return newConv;
  };

  return {
    conversations,
    currentConversationId,
    currentConversation,
    messages,
    isLoading,
    isLoadingMessages,
    error,
    aiConversations,
    privateConversations,
    loadConversations,
    selectConversation,
    loadMessages,
    deleteConversation,
    deleteMessage,
    getOrCreatePrivateConversation
  };
});
```

### 4.2 新增服务层

#### services/conversation.ts（新建）

```typescript
import http from './http';

export interface ConversationListResponse {
  success: boolean;
  conversations: Conversation[];
}

export interface Conversation {
  id: number;
  type: number;
  title: string;
  target_user_id?: number;
  target_username?: string;
  target_nickname?: string;
  is_online?: boolean;
  last_message?: string;
  last_message_time?: string;
  unread_count?: number;
  created_at: string;
  updated_at: string;
}

export const conversationApi = {
  list: async (): Promise<ConversationListResponse> => {
    const response = await http.get<ConversationListResponse>('/conversations');
    return response.data;
  },

  getOrCreatePrivate: async (targetUserId: number): Promise<any> => {
    const response = await http.post(`/conversations/private/${targetUserId}`);
    return response.data;
  },

  delete: async (conversationId: number): Promise<any> => {
    const response = await http.delete(`/conversations/${conversationId}`);
    return response.data;
  },

  updateTitle: async (conversationId: number, title: string): Promise<any> => {
    const response = await http.put(`/conversations/${conversationId}/title`, null, {
      params: { title }
    });
    return response.data;
  }
};
```

#### services/message.ts 修改

```typescript
export const messageApi = {
  // ... 现有方法

  delete: async (messageId: number): Promise<any> => {
    const response = await http.delete(`/messages/${messageId}`);
    return response.data;
  }
};
```

### 4.3 组件重构

#### views/ChatView.vue 重构

**左侧栏设计：**

```
┌─────────────────────────────────────┐
│  [新建 AI 对话]                      │
├─────────────────────────────────────┤
│  全部会话 (按时间倒序，AI + 私聊)     │
│  ┌───────────────────────────────┐  │
│  │ 🟢 与 yangxiaobao 的对话      │  │
│  │   最新消息: 你好！(2分钟前)    │  │
│  ├───────────────────────────────┤  │
│  │   drgrf (AI)                 │  │
│  │   最新消息: API错误...        │  │
│  ├───────────────────────────────┤  │
│  │ 🔴 与 offline_user 的对话     │  │
│  │   最新消息: 再见 (昨天)       │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

**会话列表项：**
- 显示在线状态（绿色圆点）
- 显示会话标题
- 显示最后一条消息预览
- 显示未读消息数
- 显示最后消息时间
- 悬浮显示删除按钮

**消息项：**
- 自己的消息：右侧，悬浮显示删除按钮
- 对方的消息：左侧，不显示删除按钮（或也可删除自己看到的）

### 4.4 删除功能实现

```vue
<!-- 会话列表中的删除按钮 -->
<div 
  v-for="conv in conversations" 
  :key="conv.id"
  @click="selectConversation(conv.id)"
  class="group relative"
>
  <div class="flex items-center justify-between">
    <div>
      <span class="text-sm font-medium">{{ conv.title }}</span>
      <p class="text-xs text-gray-500 truncate">{{ conv.last_message }}</p>
    </div>
    <button
      v-if="conv.unread_count > 0"
      class="bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5"
    >
      {{ conv.unread_count }}
    </button>
    <button
      @click.stop="handleDeleteConversation(conv.id)"
      class="opacity-0 group-hover:opacity-100 p-1 text-red-500 hover:bg-red-50 rounded transition-all"
    >
      <svg ...></svg>
    </button>
  </div>
</div>

<!-- 消息的删除按钮 -->
<div 
  v-for="msg in messages" 
  :key="msg.id"
  class="group"
>
  <div :class="msg.is_own ? 'ml-auto' : ''">
    <div class="...">
      {{ msg.content }}
    </div>
    <button
      v-if="msg.is_own"
      @click="handleDeleteMessage(msg.id)"
      class="opacity-0 group-hover:opacity-100 text-xs text-red-500 hover:underline"
    >
      删除
    </button>
  </div>
</div>
```

### 4.5 点击在线用户的逻辑

```typescript
const handleUserClick = async (targetUserId: number, targetUsername: string) => {
  // 1. 获取或创建私聊会话
  const conversation = await conversationStore.getOrCreatePrivateConversation(
    targetUserId
  );

  // 2. 选中该会话
  await conversationStore.selectConversation(conversation.id);
};
```

---

## 五、实现步骤

### 步骤一：数据库迁移

1. 备份现有数据
2. 执行建表 SQL
3. 执行数据迁移 SQL
4. 验证数据完整性

### 步骤二：后端开发

1. 新增 ORM 模型
2. 新增 CRUD 函数
3. 新增 Conversations API
4. 修改 Messages API
5. 修改 WebSocket 路由
6. 测试所有接口

### 步骤三：前端开发

1. 新增 types 定义
2. 新增 conversationApi 服务
3. 重构 stores（统一 conversationStore）
4. 重构 ChatView.vue 组件
5. 实现删除功能
6. 测试所有功能

### 步骤四：测试验证

| 测试场景 | 预期结果 |
|----------|----------|
| 用户 A 私聊用户 B | 双方都能看到消息 |
| 用户 A 删除会话 | 用户 A 看不到，用户 B 仍能看到 |
| 用户 A 删除消息 | 用户 A 看不到，用户 B 仍能看到 |
| 点击在线用户 | 加载历史对话 |
| 点击离线用户的历史会话 | 也能加载历史对话 |
| 新建 AI 对话 | 正常创建 |
| 删除 AI 对话 | 仅对当前用户隐藏 |

---

## 六、总结

### 核心改进点

| 改进项 | 旧方案 | 新方案 |
|--------|--------|--------|
| 会话归属 | 单向 user_id -> target_user_id | 双向 participants 表 |
| 删除会话 | 级联删除消息 | 软删除，不影响对方 |
| 会话标题 | 统一 | 每个用户可自定义 |
| 消息删除 | 物理删除 | 可见性控制 |
| 会话列表 | AI 和私聊分开 | 统一列表，按时间排序 |
| 未读消息 | 不支持 | 支持 |
| 在线状态 | 单独请求 | 会话列表中直接显示 |

### 风险与注意事项

1. **数据迁移**：需要先备份数据，迁移时可能有锁表
2. **兼容性**：旧代码需要修改，新旧表结构不兼容
3. **WebSocket 消息格式**：需要同步修改消息格式
4. **前端状态管理**：需要重构，测试要充分
