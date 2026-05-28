# 后端开发文档

## 1. 项目概述

本项目是基于 FastAPI 构建的聊天系统后端服务，提供 AI 对话、用户私聊、在线用户管理等功能。

### 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 编程语言 |
| FastAPI | 0.104.1 | Web 框架 |
| Uvicorn | 0.24.0 | ASGI 服务器 |
| Pydantic | 2.5.2 | 数据验证 |
| aiohttp | 3.9.1 | 异步 HTTP 客户端 |

## 2. 项目结构

```
backend/webchat/
├── main.py              # FastAPI 主应用入口
├── config.py            # 配置管理模块
├── models.py            # Pydantic 数据模型
├── routes.py            # API 路由定义
├── utils.py             # 工具函数
├── requirements.txt     # 依赖清单
└── config/
    ├── server_config.json   # 服务器配置文件
    └── client_config.json   # 客户端配置文件
```

## 3. 配置说明

### 3.1 server_config.json 配置项

```json
{
    "server": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "deepseek": {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "api_key": "your_api_key",
        "timeout": 30
    },
    "heartbeat": {
        "interval": 30,
        "timeout": 60
    },
    "cors": {
        "allow_origins": ["*"],
        "allow_methods": ["*"],
        "allow_headers": ["*"]
    }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| server.host | 服务绑定地址 | 0.0.0.0 |
| server.port | 服务端口 | 8000 |
| deepseek.api_url | DeepSeek API 地址 | - |
| deepseek.api_key | DeepSeek API 密钥 | - |
| deepseek.timeout | API 超时时间（秒） | 30 |
| heartbeat.interval | 心跳间隔（秒） | 30 |
| heartbeat.timeout | 心跳超时时间（秒） | 60 |

### 3.2 环境变量配置

支持通过环境变量覆盖配置：

| 环境变量 | 对应配置 |
|----------|----------|
| SERVER_HOST | server.host |
| SERVER_PORT | server.port |
| API_URL | deepseek.api_url |
| API_KEY | deepseek.api_key |
| API_TIMEOUT | deepseek.timeout |

## 4. API 接口文档

### 4.1 RESTful API

#### 4.1.1 健康检查

- **路径**: `/health`
- **方法**: GET
- **描述**: 检查服务健康状态

**响应**:
```json
{
    "status": "healthy"
}
```

#### 4.1.2 用户登录

- **路径**: `/api/login`
- **方法**: POST
- **描述**: 用户登录

**请求体**:
```json
{
    "username": "string"
}
```

**响应**:
```json
{
    "success": true,
    "message": "欢迎 username"
}
```

#### 4.1.3 AI 对话

- **路径**: `/api/chat`
- **方法**: POST
- **描述**: 与 AI 进行对话

**请求体**:
```json
{
    "message": "string",
    "username": "string"
}
```

**响应**:
```json
{
    "success": true,
    "content": "AI 回复内容",
    "error": ""
}
```

#### 4.1.4 获取在线用户

- **路径**: `/api/users`
- **方法**: GET
- **描述**: 获取当前在线用户列表

**响应**:
```json
{
    "success": true,
    "users": ["user1", "user2"]
}
```

#### 4.1.5 发送私聊消息

- **路径**: `/api/private`
- **方法**: POST
- **描述**: 向指定用户发送私聊消息

**请求体**:
```json
{
    "from_user": "string",
    "to_user": "string",
    "content": "string"
}
```

**响应**:
```json
{
    "success": true,
    "message": "已发送给 username"
}
```

#### 4.1.6 获取聊天历史

- **路径**: `/api/history/{username}`
- **方法**: GET
- **描述**: 获取指定用户的聊天历史

**响应**:
```json
{
    "success": true,
    "history": [
        {"role": "user", "content": "消息内容"},
        {"role": "assistant", "content": "回复内容"}
    ]
}
```

### 4.2 WebSocket 接口

#### 4.2.1 连接端点

- **路径**: `/ws/{username}`
- **协议**: WebSocket

#### 4.2.2 消息类型

| 类型 | 说明 | 数据结构 |
|------|------|----------|
| ai | AI 对话 | `{"type": "ai", "content": "消息"}` |
| user | 私聊 | `{"type": "user", "to": "username", "content": "消息"}` |
| users | 查询在线用户 | `{"type": "users"}` |
| ping | 心跳检测 | `{"type": "ping"}` |
| pong | 心跳响应 | `{"type": "pong"}` |
| private | 接收私聊 | `{"type": "private", "from": "username", "content": "消息"}` |
| info | 系统信息 | `{"type": "info", "content": "消息"}` |
| error | 错误信息 | `{"type": "error", "content": "消息"}` |

## 5. 数据模型

### 5.1 请求模型

```python
class ChatRequest(BaseModel):
    message: str       # 用户输入的消息
    username: str      # 用户名

class LoginRequest(BaseModel):
    username: str      # 用户名

class PrivateMessageRequest(BaseModel):
    from_user: str     # 发送方用户名
    to_user: str       # 接收方用户名
    content: str       # 消息内容
```

### 5.2 响应模型

```python
class ChatResponse(BaseModel):
    success: bool      # 请求是否成功
    content: str       # AI 回复内容
    error: str         # 错误信息

class OnlineUsersResponse(BaseModel):
    success: bool      # 请求是否成功
    users: List[str]   # 在线用户列表

class LoginResponse(BaseModel):
    success: bool      # 登录是否成功
    message: str       # 登录结果消息
```

## 6. 核心功能实现

### 6.1 AI 对话流程

```
用户消息 → 路由处理 → 添加到对话历史 → 调用 DeepSeek API → 返回结果
```

### 6.2 用户状态管理

后端维护两个全局字典：
- `online_users`: 在线用户 → WebSocket 连接映射
- `chat_histories`: 用户名 → 对话历史列表映射

### 6.3 心跳机制

- 客户端定期发送 `ping` 消息
- 服务端返回 `pong` 响应
- 超过超时时间未收到消息则断开连接

## 7. 部署说明

### 7.1 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python main.py
```

### 7.2 生产环境

```bash
# 使用 uvicorn 启动
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 或使用 gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 7.3 Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 8. API 文档

启动服务后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 9. 注意事项

1. **API 密钥安全**: DeepSeek API 密钥需妥善保管，建议通过环境变量配置
2. **会话管理**: 当前实现为内存存储，重启服务后会话数据会丢失
3. **并发限制**: 建议根据实际需求配置请求限流
4. **日志记录**: 生产环境建议添加完善的日志记录