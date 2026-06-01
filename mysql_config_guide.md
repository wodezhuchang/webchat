# MySQL 8.0.12 数据库配置流程指南

## 1. 环境要求

| 软件 | 版本 | 说明 |
|------|------|------|
| MySQL | 8.0.12+ | 关系型数据库 |
| Python | 3.8+ | 后端运行环境 |
| pip | - | Python 包管理器 |

---

## 2. MySQL 安装与配置

### 2.1 MySQL 8.0.12 安装

#### Windows 系统安装

1. **下载 MySQL Installer**
   - 访问：https://dev.mysql.com/downloads/mysql/
   - 选择版本：MySQL 8.0.12
   - 下载 `Windows (x86, 32-bit), MSI Installer`

2. **安装步骤**
   - 运行安装程序
   - 选择 "Developer Default" 安装类型
   - 点击 "Execute" 开始安装
   - 安装完成后点击 "Next" 进入配置

3. **配置 MySQL**
   - **Type and Networking**:
     - Config Type: `Development Computer`
     - TCP/IP Port: `3306`（默认）
   - **Authentication Method**:
     - 选择 `Use Legacy Authentication Method`（推荐，兼容性更好）
     - 或选择 `Use Strong Password Encryption`（更安全）
   - **Accounts and Roles**:
     - 设置 root 密码（请牢记此密码）
   - **Windows Service**:
     - Service Name: `MySQL80`（默认）
     - 勾选 "Configure MySQL Server as a Windows Service"
   - 点击 "Execute" 完成配置

#### 验证安装

```powershell
# 检查 MySQL 服务状态
Get-Service -Name "*MySQL*"

# 或使用命令行登录
mysql -u root -p
# 输入设置的 root 密码
```

### 2.2 MySQL 基础配置

#### 查看并修改配置文件

MySQL 配置文件位置（Windows）：
```
C:\ProgramData\MySQL\MySQL Server 8.0\my.ini
```

**建议的配置项**：
```ini
[mysqld]
# 端口
port=3306

# 字符集（重要，支持中文）
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci

# 最大连接数
max_connections=200

# 时区设置
default-time-zone='+08:00'

# 日志（可选）
log-error="your_computer_name.err"
general-log=0
general_log_file="your_computer_name.log"

[client]
default-character-set=utf8mb4

[mysql]
default-character-set=utf8mb4
```

**修改配置后重启服务**：
```powershell
# 以管理员身份运行 PowerShell
net stop MySQL80
net start MySQL80
```

---

## 3. 创建数据库和表结构

### 3.1 登录 MySQL

```powershell
# 使用 root 用户登录
mysql -u root -p
# 输入密码
```

### 3.2 创建数据库

```sql
-- 创建数据库，使用 utf8mb4 字符集
CREATE DATABASE IF NOT EXISTS chat_system 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

-- 查看数据库
SHOW DATABASES;

-- 切换到 chat_system 数据库
USE chat_system;
```

### 3.3 创建数据库用户（推荐）

**不建议直接使用 root 用户连接应用**，创建专用用户：

```sql
-- 创建专用用户
CREATE USER 'chat_user'@'localhost' IDENTIFIED BY 'Chat@2026!';
CREATE USER 'chat_user'@'%' IDENTIFIED BY 'Chat@2026!';

-- 授权（仅授予 chat_system 数据库权限）
GRANT ALL PRIVILEGES ON chat_system.* TO 'chat_user'@'localhost';
GRANT ALL PRIVILEGES ON chat_system.* TO 'chat_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 验证用户权限
SHOW GRANTS FOR 'chat_user'@'localhost';
```

**密码强度要求**（MySQL 8.0.12 默认）：
- 至少 8 个字符
- 包含大小写字母
- 包含数字
- 包含特殊字符

### 3.4 完整的建表 SQL

将以下 SQL 保存为 `chat_schema.sql` 文件：

```sql
-- ============================================
-- 聊天系统数据库表结构
-- MySQL 8.0.12
-- 创建日期: 2026-06-01
-- ============================================

-- 选择数据库
USE chat_system;

-- ============================================
-- 1. 用户表 (users)
-- ============================================
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS token_blacklist;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名（唯一）',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希值（bcrypt）',
    nickname VARCHAR(50) DEFAULT NULL COMMENT '用户昵称',
    avatar VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-正常, 0-禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX idx_username (username),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 2. 会话表 (sessions)
-- ============================================
CREATE TABLE sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会话ID',
    user_id BIGINT NOT NULL COMMENT '用户ID（外键）',
    title VARCHAR(100) DEFAULT '新对话' COMMENT '会话标题',
    session_type TINYINT DEFAULT 1 COMMENT '会话类型: 1-AI对话, 2-私聊',
    target_user_id BIGINT DEFAULT NULL COMMENT '私聊目标用户ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_active TINYINT DEFAULT 1 COMMENT '是否活跃: 1-活跃, 0-已结束',
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_target_user (target_user_id),
    INDEX idx_updated_at (updated_at),
    
    -- 外键约束
    FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    FOREIGN KEY (target_user_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';

-- ============================================
-- 3. 消息表 (messages)
-- ============================================
CREATE TABLE messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
    session_id BIGINT NOT NULL COMMENT '会话ID（外键）',
    sender_type TINYINT NOT NULL COMMENT '发送者类型: 1-用户, 2-AI, 3-系统',
    sender_id BIGINT DEFAULT NULL COMMENT '发送者用户ID（AI/系统时为NULL）',
    content TEXT NOT NULL COMMENT '消息内容',
    message_type TINYINT DEFAULT 1 COMMENT '消息类型: 1-文本, 2-图片, 3-文件',
    media_url VARCHAR(500) DEFAULT NULL COMMENT '媒体文件URL',
    status TINYINT DEFAULT 1 COMMENT '消息状态: 1-正常, 2-已撤回',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX idx_session_id (session_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_created_at (created_at),
    
    -- 外键约束
    FOREIGN KEY (session_id) 
        REFERENCES sessions(id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    
    FOREIGN KEY (sender_id) 
        REFERENCES users(id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';

-- ============================================
-- 4. Token 黑名单表 (token_blacklist)
-- ============================================
CREATE TABLE token_blacklist (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    token VARCHAR(500) NOT NULL UNIQUE COMMENT 'JWT Token',
    expires_at DATETIME NOT NULL COMMENT '过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX idx_token (token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Token黑名单';

-- ============================================
-- 5. 插入测试数据（可选）
-- ============================================

-- 插入测试用户（密码: Test@123456）
-- 密码哈希需要在 Python 中用 bcrypt 生成
-- 这里仅做演示，实际使用时请通过注册接口创建

-- ============================================
-- 6. 验证表结构
-- ============================================

-- 查看所有表
SHOW TABLES;

-- 查看各表结构
DESCRIBE users;
DESCRIBE sessions;
DESCRIBE messages;
DESCRIBE token_blacklist;

-- ============================================
-- 完成
-- ============================================
SELECT '数据库表结构创建完成！' AS status;
```

### 3.5 执行建表 SQL

#### 方式一：命令行执行

```powershell
# 登录 MySQL
mysql -u chat_user -p

# 执行 SQL 文件
mysql -u chat_user -p chat_system < chat_schema.sql
```

#### 方式二：在 MySQL 客户端中执行

```sql
-- 登录后执行
SOURCE C:\path\to\chat_schema.sql;
```

#### 方式三：使用 Navicat / DBeaver / MySQL Workbench

1. 连接数据库
2. 打开 SQL 文件
3. 执行 SQL 脚本

### 3.6 验证表结构

```sql
-- 查看所有表
SHOW TABLES;

-- 预期输出：
-- +------------------------+
-- | Tables_in_chat_system  |
-- +------------------------+
-- | messages               |
-- | sessions               |
-- | token_blacklist        |
-- | users                  |
-- +------------------------+

-- 查看各表详细结构
DESCRIBE users;
SHOW CREATE TABLE users;
```

---

## 4. 后端项目对接配置

### 4.1 安装 MySQL 相关依赖

```powershell
# 进入项目目录
cd c:\Users\yangd\Desktop\Python\交互系统\backend\webchat

# 激活虚拟环境
.venv\Scripts\Activate.ps1

# 安装依赖
pip install sqlalchemy>=2.0.23
pip install mysql-connector-python>=8.2.0
pip install pymysql>=1.1.0
pip install cryptography>=41.0.0

# 或批量安装（推荐）
pip install sqlalchemy mysql-connector-python pymysql cryptography

# 保存到 requirements.txt
pip freeze >> requirements.txt
```

### 4.2 创建环境变量配置文件

在项目根目录创建 `.env` 文件：

```env
# ============================================
# 数据库配置
# ============================================

# MySQL 主机地址
DB_HOST=localhost

# MySQL 端口
DB_PORT=3306

# 数据库用户名
DB_USER=chat_user

# 数据库密码（请修改为实际密码）
DB_PASSWORD=Chat@2026!

# 数据库名称
DB_NAME=chat_system

# 连接池配置
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# ============================================
# JWT 配置
# ============================================

# JWT 密钥（请修改为随机字符串）
JWT_SECRET_KEY=change_this_to_your_secret_key_please_make_it_long_and_random

# JWT 算法
JWT_ALGORITHM=HS256

# Access Token 有效期（分钟）
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Refresh Token 有效期（天）
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================
# 密码哈希配置
# ============================================

# bcrypt 轮数（建议 12）
BCRYPT_ROUNDS=12
```

**重要提醒**：
- 请将 `JWT_SECRET_KEY` 修改为随机字符串
- 请将 `DB_PASSWORD` 修改为您设置的实际密码
- 不要将 `.env` 文件提交到版本控制

### 4.3 创建 .gitignore 配置

确保 `.env` 不被提交：

```
# .gitignore
.env
.env.local
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
*.log
```

### 4.4 数据库连接测试

创建测试脚本 `test_db_connection.py`：

```python
# test_db_connection.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 加载环境变量
load_dotenv()

# 获取配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "chat_system")

# 构建连接字符串
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"连接字符串: {DATABASE_URL.replace(DB_PASSWORD, '***')}")

try:
    # 创建引擎
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        echo=True  # 显示 SQL 日志，生产环境设为 False
    )
    
    # 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # 测试连接
    with SessionLocal() as session:
        result = session.execute(text("SELECT VERSION()"))
        version = result.scalar()
        print(f"\n✅ 数据库连接成功！")
        print(f"MySQL 版本: {version}")
        
        # 测试表
        result = session.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        print(f"数据库表: {tables}")
        
        print("\n✅ 所有测试通过！")
        
except Exception as e:
    print(f"\n❌ 连接失败: {e}")
    print(f"\n请检查:")
    print(f"1. MySQL 服务是否启动")
    print(f"2. 用户名和密码是否正确")
    print(f"3. 数据库是否已创建")
    print(f"4. 用户权限是否正确")
```

**运行测试**：
```powershell
# 安装 python-dotenv
pip install python-dotenv

# 运行测试
python test_db_connection.py
```

**预期输出**：
```
连接字符串: mysql+mysqlconnector://chat_user:***@localhost:3306/chat_system
...
✅ 数据库连接成功！
MySQL 版本: 8.0.12
数据库表: ['messages', 'sessions', 'token_blacklist', 'users']

✅ 所有测试通过！
```

---

## 5. 数据库连接代码示例

### 5.1 数据库连接模块

创建 `database/connection.py`：

```python
# database/connection.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 加载环境变量
load_dotenv()

# 读取配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "chat_system")

# 连接池配置
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

# 构建连接字符串
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建 SQLAlchemy 引擎
engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    echo=False  # 生产环境设为 False
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 声明基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话（依赖注入用）
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 5.2 ORM 模型定义

创建 `database/models.py`：

```python
# database/models.py
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
    """用户表"""
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
    
    # 关系
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index("idx_username", "username"),
        Index("idx_status", "status"),
    )


class Session(Base):
    """会话表"""
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
    
    # 关系
    user = relationship("User", back_populates="sessions", foreign_keys=[user_id])
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_target_user", "target_user_id"),
        Index("idx_updated_at", "updated_at"),
    )


class Message(Base):
    """消息表"""
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
    
    # 关系
    session = relationship("Session", back_populates="messages")
    
    # 索引
    __table_args__ = (
        Index("idx_session_id", "session_id"),
        Index("idx_sender_id", "sender_id"),
        Index("idx_created_at", "created_at"),
    )


class TokenBlacklist(Base):
    """Token 黑名单"""
    __tablename__ = "token_blacklist"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token = Column(String(500), unique=True, nullable=False, comment="JWT Token")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 索引
    __table_args__ = (
        Index("idx_token", "token"),
        Index("idx_expires_at", "expires_at"),
    )
```

### 5.3 密码哈希工具

创建 `auth/password.py`：

```python
# auth/password.py
import bcrypt


def hash_password(password: str) -> str:
    """
    生成密码哈希
    
    Args:
        password: 原始密码
        
    Returns:
        bcrypt 哈希后的密码字符串
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码
    
    Args:
        password: 用户输入的原始密码
        password_hash: 数据库中存储的哈希密码
        
    Returns:
        是否匹配
    """
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False
```

### 5.4 JWT 工具

创建 `auth/jwt.py`：

```python
# auth/jwt.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 Access Token
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT Token 字符串
    """
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
    """
    创建 Refresh Token
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        
    Returns:
        JWT Token 字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    解码 Token
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        解码后的数据（无效则返回 None）
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_expires_in(token: str) -> int:
    """
    获取 Token 剩余有效期（秒）
    
    Args:
        token: JWT Token 字符串
        
    Returns:
        剩余秒数（过期返回 0）
    """
    payload = decode_token(token)
    if not payload:
        return 0
    
    exp = payload.get("exp")
    if not exp:
        return 0
    
    now = datetime.now(timezone.utc).timestamp()
    remaining = int(exp - now)
    
    return max(0, remaining)
```

---

## 6. 常见问题排查

### 6.1 连接失败

**错误信息**：
```
Can't connect to MySQL server on 'localhost:3306'
```

**解决方案**：
```powershell
# 检查 MySQL 服务状态
Get-Service -Name "MySQL80"

# 如果未启动，启动服务
net start MySQL80

# 检查端口占用
netstat -ano | findstr :3306
```

### 6.2 认证失败

**错误信息**：
```
Access denied for user 'chat_user'@'localhost'
```

**解决方案**：
```sql
-- 检查用户权限
SHOW GRANTS FOR 'chat_user'@'localhost';

-- 重新授权
GRANT ALL PRIVILEGES ON chat_system.* TO 'chat_user'@'localhost';
FLUSH PRIVILEGES;

-- 或者使用 root 用户创建用户
CREATE USER IF NOT EXISTS 'chat_user'@'localhost' IDENTIFIED BY 'Chat@2026!';
GRANT ALL PRIVILEGES ON chat_system.* TO 'chat_user'@'localhost';
FLUSH PRIVILEGES;
```

### 6.3 字符集问题

**问题**：中文乱码

**解决方案**：
```sql
-- 检查数据库字符集
SHOW CREATE DATABASE chat_system;

-- 如果不是 utf8mb4，修改数据库
ALTER DATABASE chat_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 检查表字符集
SHOW CREATE TABLE users;

-- 修改表字符集
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE sessions CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE messages CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE token_blacklist CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6.4 密码强度问题

**错误信息**：
```
Your password does not satisfy the current policy requirements
```

**解决方案**：
```sql
-- 查看密码策略
SHOW VARIABLES LIKE 'validate_password%';

-- 临时降低策略（仅测试用）
SET GLOBAL validate_password.policy = LOW;
SET GLOBAL validate_password.length = 4;
SET GLOBAL validate_password.mixed_case_count = 0;
SET GLOBAL validate_password.number_count = 0;
SET GLOBAL validate_password.special_char_count = 0;

-- 创建用户（使用强密码推荐）
CREATE USER 'chat_user'@'localhost' IDENTIFIED BY 'StrongPassword123!';
```

### 6.5 连接池问题

**问题**：连接池耗尽

**解决方案**：
```python
# 调整连接池配置（在 .env 中）
DB_POOL_SIZE=30      # 增加连接池大小
DB_MAX_OVERFLOW=20   # 增加最大溢出连接数
DB_POOL_TIMEOUT=60   # 增加超时时间
```

### 6.6 时区问题

**问题**：时间显示不对

**解决方案**：
```sql
-- 设置 MySQL 时区
SET GLOBAL time_zone = '+08:00';
SET time_zone = '+08:00';

-- 查看时区
SHOW VARIABLES LIKE '%time_zone%';
```

---

## 7. 数据库维护

### 7.1 备份数据库

```powershell
# 备份整个数据库
mysqldump -u chat_user -p chat_system > chat_system_backup_20260601.sql

# 备份指定表
mysqldump -u chat_user -p chat_system users sessions messages > data_backup.sql

# 压缩备份
mysqldump -u chat_user -p chat_system | gzip > chat_system_backup.sql.gz
```

### 7.2 恢复数据库

```powershell
# 恢复数据库
mysql -u chat_user -p chat_system < chat_system_backup_20260601.sql

# 从压缩文件恢复
gunzip < chat_system_backup.sql.gz | mysql -u chat_user -p chat_system
```

### 7.3 清理过期 Token

```sql
-- 创建清理事件（需要 EVENT_SCHEDULER 开启）
SET GLOBAL event_scheduler = ON;

-- 创建每日清理事件
CREATE EVENT IF NOT EXISTS cleanup_expired_tokens
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
    DELETE FROM token_blacklist WHERE expires_at < NOW();
```

---

## 8. 快速启动清单

- [ ] 1. 安装 MySQL 8.0.12
- [ ] 2. 启动 MySQL 服务
- [ ] 3. 创建数据库 `chat_system`
- [ ] 4. 创建专用数据库用户
- [ ] 5. 执行建表 SQL
- [ ] 6. 创建 `.env` 配置文件
- [ ] 7. 安装 Python 依赖
- [ ] 8. 运行数据库连接测试
- [ ] 9. 启动后端服务验证

---

## 9. 附录

### 9.1 环境变量示例

```env
# .env.example - 模板文件，复制为 .env 后修改

DB_HOST=localhost
DB_PORT=3306
DB_USER=chat_user
DB_PASSWORD=your_password_here
DB_NAME=chat_system
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

JWT_SECRET_KEY=your_very_long_and_random_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

BCRYPT_ROUNDS=12
```

### 9.2 数据库用户权限确认 SQL

```sql
-- 1. 查看所有用户
SELECT User, Host FROM mysql.user;

-- 2. 查看当前用户权限
SHOW GRANTS FOR CURRENT_USER();

-- 3. 查看 chat_user 权限
SHOW GRANTS FOR 'chat_user'@'localhost';

-- 4. 测试用户连接（在 PowerShell 中）
-- mysql -u chat_user -p -e "SELECT 1"

-- 5. 查看数据库列表
SHOW DATABASES;

-- 6. 查看表列表
USE chat_system;
SHOW TABLES;

-- 7. 查看表结构
DESCRIBE users;
```

---

**文档版本**: v1.0  
**创建日期**: 2026-06-01  
**适用 MySQL 版本**: 8.0.12+  
**适用后端项目**: 聊天系统后端 (FastAPI)
