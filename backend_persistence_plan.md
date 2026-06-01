# 聊天系统后端持久化与登录验证方案书

## 1. 方案概述

### 1.1 背景

当前聊天系统采用内存存储用户状态和聊天历史，存在以下问题：
- 服务重启后数据丢失
- 不支持多实例部署
- 缺少用户身份认证
- 数据无持久化备份

### 1.2 目标

- 实现用户登录验证（用户名 + 密码）
- 使用 MySQL 持久化存储用户信息和聊天记录
- 支持多实例部署
- 保证数据安全性和一致性

### 1.3 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| 数据库 | MySQL 8.0+ | 关系型数据库，支持事务 |
| ORM | SQLAlchemy 2.0+ | Python ORM 框架 |
| 驱动 | mysql-connector-python | MySQL 官方驱动 |
| 密码哈希 | bcrypt | 安全的密码哈希算法 |
| 会话管理 | JWT (JSON Web Token) | 无状态会话管理 |
| 连接池 | SQLAlchemy Pooling | 数据库连接池 |

---

## 2. 数据库设计

### 2.1 ER 图

```
+----------------+         +----------------+         +----------------+
|    users       |         |   sessions     |         |   messages     |
+----------------+         +----------------+         +----------------+
| id (PK)        |<--------| user_id (FK)   |<--------| session_id (FK)|
| username (UK)  |         | id (PK)        |         | id (PK)        |
| password_hash  |         | title          |         | sender_type    |
| nickname       |         | created_at     |         | sender_id      |
| avatar         |         | updated_at     |         | content        |
| status         |         | is_active      |         | message_type   |
| created_at     |         +----------------+         | created_at     |
| updated_at     |                                    +----------------+
+----------------+
```

### 2.2 表结构设计

#### 2.2.1 users 表（用户表）

```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希值',
    nickname VARCHAR(50) COMMENT '昵称',
    avatar VARCHAR(255) COMMENT '头像URL',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-正常, 0-禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

#### 2.2.2 sessions 表（会话表）

```sql
CREATE TABLE sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会话ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    title VARCHAR(100) DEFAULT '新对话' COMMENT '会话标题',
    session_type TINYINT DEFAULT 1 COMMENT '会话类型: 1-AI对话, 2-私聊',
    target_user_id BIGINT COMMENT '私聊目标用户ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_active TINYINT DEFAULT 1 COMMENT '是否活跃: 1-活跃, 0-已结束',
    INDEX idx_user_id (user_id),
    INDEX idx_target_user (target_user_id),
    INDEX idx_updated_at (updated_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (target_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='会话表';
```

#### 2.2.3 messages 表（消息表）

```sql
CREATE TABLE messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
    session_id BIGINT NOT NULL COMMENT '会话ID',
    sender_type TINYINT NOT NULL COMMENT '发送者类型: 1-用户, 2-AI, 3-系统',
    sender_id BIGINT COMMENT '发送者用户ID(AI/系统时为NULL)',
    content TEXT NOT NULL COMMENT '消息内容',
    message_type TINYINT DEFAULT 1 COMMENT '消息类型: 1-文本, 2-图片, 3-文件',
    media_url VARCHAR(500) COMMENT '媒体文件URL',
    status TINYINT DEFAULT 1 COMMENT '消息状态: 1-正常, 2-已撤回',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_session_id (session_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息表';
```

#### 2.2.4 tokens 表（Token 黑名单）

```sql
CREATE TABLE token_blacklist (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    token VARCHAR(500) NOT NULL UNIQUE COMMENT 'JWT Token',
    expires_at DATETIME NOT NULL COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token (token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Token黑名单';
```

---

## 3. 登录验证方案

### 3.1 认证流程

```
用户输入 → 验证用户名密码 → 生成JWT → 返回Token → 后续请求携带Token
```

### 3.2 密码安全

**密码哈希方案：bcrypt**

```python
import bcrypt

# 注册时：生成密码哈希
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

# 登录时：验证密码
def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
```

### 3.3 JWT Token 设计

**Token 结构：**

```json
{
  "sub": "user_id",
  "username": "username",
  "type": "access" | "refresh",
  "iat": 1234567890,
  "exp": 1234571490
}
```

**Token 类型：**

| 类型 | 有效期 | 用途 |
|------|--------|------|
| Access Token | 30 分钟 | 访问 API |
| Refresh Token | 7 天 | 刷新 Access Token |

### 3.4 认证接口设计

#### 3.4.1 注册接口

```
POST /api/auth/register
```

**请求体：**
```json
{
  "username": "testuser",
  "password": "password123",
  "nickname": "测试用户",
  "confirm_password": "password123"
}
```

**响应：**
```json
{
  "success": true,
  "message": "注册成功",
  "data": {
    "user_id": 1,
    "username": "testuser",
    "nickname": "测试用户"
  }
}
```

#### 3.4.2 登录接口

```
POST /api/auth/login
```

**请求体：**
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**响应：**
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": 1,
      "username": "testuser",
      "nickname": "测试用户",
      "avatar": "https://...",
      "status": 1
    }
  }
}
```

#### 3.4.3 刷新 Token 接口

```
POST /api/auth/refresh
```

**请求头：**
```
Authorization: Bearer <refresh_token>
```

**响应：**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 1800
  }
}
```

#### 3.4.4 登出接口

```
POST /api/auth/logout
```

**请求头：**
```
Authorization: Bearer <access_token>
```

**响应：**
```json
{
  "success": true,
  "message": "登出成功"
}
```

### 3.5 WebSocket 认证

**连接参数认证：**
```
ws://localhost:8000/ws?token=<access_token>
```

**或连接后发送认证消息：**
```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

## 4. 聊天持久化方案

### 4.1 数据写入流程

```
接收消息 → 写入数据库 → 广播消息 → 返回确认
```

### 4.2 会话管理

#### 4.2.1 创建会话

```python
# 创建新的 AI 对话会话
session = Session(
    user_id=current_user.id,
    title=title or "新对话",
    session_type=1  # AI 对话
)
db.add(session)
db.commit()
```

#### 4.2.2 获取会话列表

```python
sessions = db.query(Session).filter(
    Session.user_id == current_user.id,
    Session.is_active == True
).order_by(Session.updated_at.desc()).all()
```

### 4.3 消息存储

#### 4.3.1 写入 AI 对话消息

```python
# 用户消息
user_msg = Message(
    session_id=session_id,
    sender_type=1,  # 用户
    sender_id=current_user.id,
    content=user_content,
    message_type=1  # 文本
)
db.add(user_msg)

# AI 回复
ai_msg = Message(
    session_id=session_id,
    sender_type=2,  # AI
    content=ai_content,
    message_type=1
)
db.add(ai_msg)

db.commit()
```

#### 4.3.2 写入私聊消息

```python
message = Message(
    session_id=private_session_id,
    sender_type=1,
    sender_id=from_user.id,
    content=content,
    message_type=1
)
db.add(message)
db.commit()
```

### 4.4 历史消息查询

#### 4.4.1 分页查询

```python
messages = db.query(Message).filter(
    Message.session_id == session_id,
    Message.status == 1
).order_by(Message.created_at.desc()).limit(limit).offset(offset).all()
```

#### 4.4.2 按时间范围查询

```python
messages = db.query(Message).filter(
    Message.session_id == session_id,
    Message.created_at.between(start_time, end_time)
).all()
```

---

## 5. 新增 API 接口

### 5.1 认证相关

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | ❌ |
| POST | `/api/auth/login` | 用户登录 | ❌ |
| POST | `/api/auth/refresh` | 刷新 Token | ❌ (需要 Refresh Token) |
| POST | `/api/auth/logout` | 用户登出 | ✅ |
| GET | `/api/auth/me` | 获取当前用户 | ✅ |

### 5.2 用户相关

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| PUT | `/api/users/profile` | 更新用户资料 | ✅ |
| PUT | `/api/users/password` | 修改密码 | ✅ |
| POST | `/api/users/avatar` | 上传头像 | ✅ |

### 5.3 会话相关

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/sessions` | 获取会话列表 | ✅ |
| POST | `/api/sessions` | 创建会话 | ✅ |
| PUT | `/api/sessions/{id}` | 更新会话标题 | ✅ |
| DELETE | `/api/sessions/{id}` | 删除会话 | ✅ |
| GET | `/api/sessions/{id}/messages` | 获取会话消息 | ✅ |

### 5.4 消息相关

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| DELETE | `/api/messages/{id}` | 撤回消息 | ✅ |

---

## 6. 项目文件结构调整

```
backend/webchat/
├── main.py                      # FastAPI 主应用
├── config.py                    # 配置管理
├── models.py                    # Pydantic 数据模型（请求/响应）
├── routes.py                    # API 路由（原有）
├── utils.py                     # 工具函数（原有）
├── requirements.txt             # 依赖清单
├── .env.example                 # 环境变量示例
│
├── database/                    # 数据库相关
│   ├── __init__.py
│   ├── connection.py            # 数据库连接配置
│   ├── models.py                # SQLAlchemy ORM 模型
│   └── crud.py                  # 数据库操作封装
│
├── auth/                        # 认证相关
│   ├── __init__.py
│   ├── jwt.py                   # JWT 工具
│   ├── password.py              # 密码哈希
│   └── middleware.py            # 认证中间件
│
├── api/                         # API 路由（新增）
│   ├── __init__.py
│   ├── auth.py                  # 认证接口
│   ├── users.py                 # 用户接口
│   ├── sessions.py              # 会话接口
│   └── messages.py              # 消息接口
│
└── config/
    ├── server_config.json
    └── client_config.json
```

---

## 7. 新增依赖

**requirements.txt 新增：**

```
# 数据库
sqlalchemy>=2.0.23
mysql-connector-python>=8.2.0
pymysql>=1.1.0

# 认证
bcrypt>=4.0.1
pyjwt>=2.8.0
python-jose[cryptography]>=3.3.0

# 数据验证
pydantic>=2.5.2
```

---

## 8. 配置项

### 8.1 .env 文件

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=chat_system
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# JWT 配置
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 密码哈希
BCRYPT_ROUNDS=12
```

### 8.2 数据库连接池配置

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db_name}",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## 9. 安全考虑

### 9.1 密码安全

- 使用 bcrypt 哈希（加盐）
- 密码长度限制：8-50 字符
- 禁止在日志中打印密码
- 定期提醒用户修改密码

### 9.2 Token 安全

- 使用 HTTPS 传输
- 短期 Access Token + 长期 Refresh Token
- Token 黑名单机制
- 敏感操作需要重新验证密码

### 9.3 数据库安全

- 使用参数化查询，防止 SQL 注入
- 最小权限原则的数据库用户
- 定期备份数据
- 敏感字段加密存储

### 9.4 消息安全

- 私聊消息仅限双方查看
- 支持消息撤回（有限时间内）
- 内容安全检测（可选）

---

## 10. 测试计划

### 10.1 单元测试

- [ ] 密码哈希和验证
- [ ] JWT 生成和验证
- [ ] 数据库 CRUD 操作
- [ ] 数据模型验证

### 10.2 集成测试

- [ ] 用户注册流程
- [ ] 用户登录流程
- [ ] Token 刷新机制
- [ ] 登出和 Token 失效
- [ ] 会话创建和消息存储
- [ ] 历史消息查询

### 10.3 性能测试

- [ ] 并发登录测试
- [ ] 高并发消息写入测试
- [ ] 连接池压力测试
- [ ] 大数据量查询测试

---

## 11. 部署说明

### 11.1 数据库初始化

```sql
-- 创建数据库
CREATE DATABASE chat_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户
CREATE USER 'chat_user'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON chat_system.* TO 'chat_user'@'%';
FLUSH PRIVILEGES;
```

### 11.2 应用启动顺序

1. 启动 MySQL 数据库
2. 执行数据库迁移（创建表）
3. 配置 .env 文件
4. 启动 FastAPI 服务

### 11.3 多实例部署

- 共享 MySQL 数据库
- 使用 Redis 管理在线用户状态（可选）
- 负载均衡器分发 WebSocket 连接

---

## 12. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据库连接池耗尽 | 服务不可用 | 监控连接数，动态调整池大小 |
| SQL 注入 | 数据泄露 | 使用参数化查询，输入验证 |
| Token 泄露 | 账号被盗 | HTTPS，短期 Token，黑名单机制 |
| 数据丢失 | 历史消息丢失 | 定期备份，主从复制 |
| 并发写入冲突 | 数据不一致 | 事务管理，乐观锁 |

---

**文档版本**: v1.0  
**创建日期**: 2026-06-01  
**适用项目**: 聊天系统后端