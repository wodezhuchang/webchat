# 前后端对接问题分析与解决方案

## 1. 问题现象

前端页面显示"未连接"状态，浏览器控制台报错：

```
[error] ✗ WebSocket error: WebSocket connection failed. Please check if the backend server is running at ws://localhost:8000/ws
```

## 2. 后端状态检查

### 2.1 服务状态确认

**检查后端服务是否运行：**

```powershell
# 检查端口监听状态
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

# 测试健康检查接口
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
```

**正常响应示例：**

```json
{"status":"healthy"}
```

### 2.2 后端服务状态

✅ **服务已确认运行**：
- 端口：`http://0.0.0.0:8000`
- 健康检查：通过
- WebSocket端点：`ws://localhost:8000/ws/{username}`

## 3. 问题分析

### 3.1 WebSocket 连接失败原因

根据错误日志分析，可能的原因：

| 序号 | 问题原因 | 描述 |
|------|----------|------|
| 1 | URL格式错误 | WebSocket URL缺少用户名参数 |
| 2 | 连接顺序错误 | 未先登录直接连接WebSocket |
| 3 | 配置错误 | 前端环境变量配置不正确 |
| 4 | 跨域问题 | CORS配置限制 |
| 5 | 端口冲突 | 8000端口被占用 |

### 3.2 WebSocket URL 格式要求

**错误格式：**
```
ws://localhost:8000/ws          # 缺少用户名参数
```

**正确格式：**
```
ws://localhost:8000/ws/username  # 必须包含用户名
```

## 4. 解决方案

### 4.1 前端配置检查

确保 `.env` 文件配置正确：

```env
# 前端环境变量配置
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### 4.2 正确的连接流程

```
1. 用户输入用户名
2. 调用 POST /api/login 登录
3. 登录成功后连接 WebSocket：ws://localhost:8000/ws/{username}
4. 发送消息进行聊天
```

### 4.3 前端代码建议

**WebSocket连接示例：**

```typescript
const connectWebSocket = (username: string) => {
  const ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/${username}`);
  
  ws.onopen = () => {
    console.log('✅ WebSocket 连接成功');
    // 发送心跳
    ws.send(JSON.stringify({ type: 'ping' }));
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('📨 收到消息:', data);
  };
  
  ws.onerror = (error) => {
    console.error('❌ WebSocket 错误:', error);
  };
  
  ws.onclose = () => {
    console.log('🔌 WebSocket 连接关闭');
  };
  
  return ws;
};
```

### 4.4 浏览器控制台测试

在浏览器控制台执行以下代码测试连接：

```javascript
// 测试 WebSocket 连接（替换 yourname 为实际用户名）
const ws = new WebSocket('ws://localhost:8000/ws/yourname');

ws.onopen = () => {
  console.log('✅ 连接成功');
  ws.send(JSON.stringify({ type: 'ping' }));
  ws.send(JSON.stringify({ type: 'users' }));
};

ws.onmessage = (e) => console.log('📨:', JSON.parse(e.data));
ws.onerror = (e) => console.error('❌:', e);
ws.onclose = () => console.log('🔌 连接关闭');
```

## 5. 后端支持的消息类型

| 类型 | 方向 | 说明 | 数据结构 |
|------|------|------|----------|
| `ping` | 前端→后端 | 心跳请求 | `{"type": "ping"}` |
| `pong` | 后端→前端 | 心跳响应 | `{"type": "pong"}` |
| `users` | 双向 | 获取在线用户 | `{"type": "users"}` |
| `ai` | 双向 | AI对话 | `{"type": "ai", "content": "消息"}` |
| `user` | 前端→后端 | 私聊请求 | `{"type": "user", "to": "user2", "content": "消息"}` |
| `private` | 后端→前端 | 私聊消息 | `{"type": "private", "from": "user1", "content": "消息"}` |
| `info` | 后端→前端 | 系统信息 | `{"type": "info", "content": "消息"}` |
| `error` | 后端→前端 | 错误信息 | `{"type": "error", "content": "消息"}` |

## 6. 常见问题排查

### 6.1 CORS 问题

**问题**：前端请求后端时出现 CORS 错误

**解决**：后端已配置允许所有来源：

```python
# main.py 第10-16行
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 6.2 WebSocket 连接失败

**问题**：WebSocket 无法建立连接

**解决步骤**：

1. ✅ 确认后端服务正在运行（端口8000）
2. ✅ 检查 URL 是否正确（必须包含用户名）
3. ✅ 确认没有防火墙阻止连接
4. ✅ 检查前端配置文件中的 WebSocket URL

### 6.3 消息发送失败

**问题**：消息发送后没有收到响应

**解决步骤**：

1. 检查网络连接
2. 检查后端日志
3. 确认用户已登录且在线
4. 使用浏览器开发者工具查看网络请求

### 6.4 服务启动问题

**问题**：启动时报错 `ModuleNotFoundError`

**原因**：使用了系统 Python 而不是虚拟环境

**解决**：

```powershell
# 使用虚拟环境中的 Python
.venv\Scripts\python.exe main.py

# 或先激活虚拟环境
.venv\Scripts\Activate.ps1
python main.py
```

## 7. 测试验证步骤

### 7.1 后端测试

```powershell
# 1. 启动后端服务
cd backend/webchat
.venv\Scripts\python.exe main.py

# 2. 测试 REST API
Invoke-WebRequest -Uri "http://localhost:8000/api/users" -UseBasicParsing

# 3. 测试登录
$body = '{"username": "testuser"}'
Invoke-WebRequest -Uri "http://localhost:8000/api/login" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
```

### 7.2 前端测试

1. 启动前端服务：`npm run dev`
2. 访问：`http://localhost:5173`
3. 输入用户名登录
4. 观察浏览器控制台输出

## 8. 技术支持

如果问题仍未解决，请提供以下信息：

1. 后端服务日志
2. 浏览器控制台截图
3. 前端配置文件内容
4. 网络请求截图（开发者工具 → Network）

---

**文档版本**: v1.0  
**创建日期**: 2026-05-28  
**适用项目**: 聊天系统前后端对接