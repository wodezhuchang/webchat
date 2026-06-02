# 聊天记录留存改进方案

## 一、问题分析

### 1. 当前问题

#### 1.1 sessions 表无私聊记录

**问题原因：**

1. **WebSocket 私聊逻辑未创建会话**
   - 查看 [main.py](file:///c:/Users/yangd/Desktop/Python/交互系统/backend/webchat/main.py#L75-L86) 中的私聊处理：
   ```python
   elif message_type == "user":
       to_user = data.get("to")
       if to_user in online_users:
           target_ws = online_users[to_user]
           await target_ws.send_json({
               "type": "private",
               "from": username,
               "content": content
           })
           await websocket.send_json({"type": "info", "content": f"已发送给 {to_user}"})
       else:
           await websocket.send_json({"type": "error", "content": f"用户 {to_user} 不在线"})
   ```
   - 私聊消息只在内存中转发，**没有创建 Session 记录**，**没有写入数据库**

2. **前端私聊逻辑未关联会话**
   - 查看 [ChatView.vue](file:///c:/Users/yangd/Desktop/Python/交互系统/frontend/webchat-frontend/src/views/ChatView.vue#L318-L324)：
   ```typescript
   const handleUserSelect = (username: string): void => {
     chatStore.selectUser(username);
   };
   ```
   - 点击用户直接进入私聊模式，**没有查询/创建私聊会话**

3. **前端私聊消息只保存在内存**
   - 查看 [chat.ts](file:///c:/Users/yangd/Desktop/Python/交互系统/frontend/webchat-frontend/src/stores/chat.ts#L14-L29)：
   ```typescript
   const privateMessages = ref<PrivateChatHistory>({});  // 仅内存存储
   const messages = computed(() => {
     if (isPrivateMode.value && selectedUser.value) {
       return privateMessages.value[selectedUser.value] || [];
     }
     return aiMessages.value;
   });
   ```

#### 1.2 messages 表为空

**问题原因：**

1. **AI 对话消息未写入数据库**
   - 查看 [main.py](file:///c:/Users/yangd/Desktop/Python/交互系统/backend/webchat/main.py#L62-L73) 中的 AI 对话处理：
   ```python
   if message_type == "ai":
       history = chat_histories[username]
       history.append({"role": "user", "content": content})  # 仅内存
       answer = await asyncio.wait_for(call_deepseek_async(history), timeout=15)
       history.append({"role": "assistant", "content": answer})  # 仅内存
       await websocket.send_json({"type": "ai", "content": answer})
   ```
   - AI 对话消息只存在于内存字典 `chat_histories`，**没有写入数据库**

2. **后端 CRUD 函数存在但未调用**
   - `database/crud.py` 中已有 `create_session`、`create_message` 等函数
   - 但 WebSocket 路由完全没有调用这些持久化函数

### 2. 现有资源

#### 已实现但未使用的功能

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| 数据库连接 | [connection.py](file:///c:/Users/yangd/Desktop/Python/交互系统/backend/webchat/database/connection.py) | 连接池、SessionFactory | 可用 |
| ORM 模型 | [models.py](file:///c:/Users/yangd/Desktop/Python/交互系统/backend/webchat/database/models.py) | User/Session/Message 表 | 可用 |
| CRUD 操作 | [crud.py](file:///c:/Users/yangd/Desktop/Python/交互系统/backend/webchat/database/crud.py) | 创建/查询会话和消息 | 可用 |
| REST API | [api/sessions.py](file:///c:/Users/yangd/Desktop/Python/交互系统/backend/webchat/api/sessions.py) | 会话管理接口 | 可用 |
| REST API | [api/messages.py](file:///c:/Users/yangd/Desktop/Python/交互系统/backend/webchat/api/messages.py) | 消息管理接口 | 可用 |
| 前端 API 调用 | [session.ts](file:///c:/Users/yangd/Desktop/Python/交互系统/frontend/webchat-frontend/src/services/session.ts) | 会话 API 封装 | 可用 |
| 前端 API 调用 | [message.ts](file:///c:/Users/yangd/Desktop/Python/交互系统/frontend/webchat-frontend/src/services/message.ts) | 消息 API 封装 | 可用 |
| 前端状态管理 | [session.ts](file:///c:/Users/yangd/Desktop/Python/交互系统/frontend/webchat-frontend/src/stores/session.ts) | 会话 Store | 可用 |

---

## 二、后端改进方案

### 1. WebSocket 路由改造

#### 1.1 AI 对话持久化

**当前流程（问题）：**
```
用户发送 AI 消息 → WebSocket 接收 → 调用 DeepSeek AI → 返回回答 → 仅更新内存 chat_histories
                                                        ↓
                                                    数据库 ❌ 无记录
```

**改进流程：**
```
用户发送 AI 消息 → WebSocket 接收 → 检查/创建 Session → 保存用户消息到 DB
                                                          ↓
                                                    调用 DeepSeek AI
                                                          ↓
                                                    保存 AI 回复到 DB
                                                          ↓
                                                    返回回答给前端
                                                          ↓
                                                    数据库 ✅ 有记录
```

**改造要点：**

1. **获取当前用户信息**：从 JWT Token 或连接参数获取用户 ID
2. **会话管理**：
   - 首次 AI 对话：创建新 Session（session_type=1）
   - 后续对话：使用已有 Session
3. **消息持久化**：
   - 用户消息：sender_type=1, sender_id=用户ID
   - AI 回复：sender_type=2, sender_id=null

#### 1.2 私聊持久化

**当前流程（问题）：**
```
用户 A 私聊用户 B → WebSocket 接收 → 在线内存查找 → 转发给 B
                                              ↓
                                        数据库 ❌ 无记录
                                        离线用户 B ❌ 收不到
```

**改进流程：**
```
用户 A 私聊用户 B → WebSocket 接收 → 查询/创建私聊 Session → 保存消息到 DB
                                                                 ↓
                                                           检查 B 是否在线
                                                                 ↓
                                                    在线 → 实时推送
                                                    离线 → 消息留存，B 上线后可查看
                                                                 ↓
                                                           数据库 ✅ 有记录
```

**改造要点：**

1. **私聊会话创建规则**：
   - Session.session_type = 2（私聊）
   - Session.user_id = 发起者用户 ID
   - Session.target_user_id = 目标用户 ID
   - Session.title = "与 {目标用户名} 的对话"

2. **双向会话查询**：
   - 用户 A 查看与 B 的私聊：查询 user_id=A AND target_user_id=B
   - 用户 B 查看与 A 的私聊：查询 user_id=B AND target_user_id=A 或 user_id=A AND target_user_id=B
   - **建议**：增加复合查询或会话参与者表

### 2. 新数据库表设计（可选优化）

#### 2.1 现有表结构

```sql
-- sessions 表
CREATE TABLE sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,              -- 会话创建者
    title VARCHAR(100),
    session_type SMALLINT,                -- 1=AI, 2=私聊
    target_user_id BIGINT,                -- 私聊目标用户
    created_at DATETIME,
    updated_at DATETIME,
    is_active SMALLINT
);

-- messages 表
CREATE TABLE messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id BIGINT NOT NULL,
    sender_type SMALLINT,                 -- 1=用户, 2=AI, 3=系统
    sender_id BIGINT,                     -- 发送者用户ID
    content TEXT,
    message_type SMALLINT,                -- 1=文本, 2=图片, 3=文件
    media_url VARCHAR(500),
    status SMALLINT,                      -- 1=正常, 2=已撤回
    created_at DATETIME
);
```

#### 2.2 问题分析

**私聊会话的双向性问题：**
- 当前设计：session.user_id 是创建者，target_user_id 是目标
- 查询问题：用户 B 查看与 A 的会话时，需要查询两种情况
- 解决方案：新增 `session_participants` 表

#### 2.3 建议新增表（可选）

```sql
-- 会话参与者表（解决双向查询问题）
CREATE TABLE session_participants (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_read_at DATETIME,                -- 最后阅读时间
    is_deleted TINYINT DEFAULT 0,         -- 软删除标记
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_session_user (session_id, user_id),
    INDEX idx_user_id (user_id)
);

-- 消息阅读状态表
CREATE TABLE message_read_status (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    message_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    is_read TINYINT DEFAULT 0,
    read_at DATETIME,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_message_user (message_id, user_id)
);
```

### 3. 后端代码改造清单

| 文件 | 改造内容 | 优先级 |
|------|----------|--------|
| `main.py` - WebSocket | 集成数据库操作，消息持久化 | 高 |
| `database/crud.py` | 新增私聊会话查询、消息批量创建 | 高 |
| `api/sessions.py` | 新增私聊会话创建/查询接口 | 中 |
| `database/models.py` | 可选：新增参与者表模型 | 中 |

---

## 三、前端改进方案

### 1. 私聊模式改进

#### 1.1 当前问题

1. **点击用户直接进入私聊**：没有创建/关联会话
2. **私聊消息仅内存存储**：刷新页面后丢失
3. **无历史记录加载**：无法查看之前的聊天记录
4. **无删除聊天记录功能**：用户无法管理消息

#### 1.2 改进流程

**用户点击在线用户：**
```
点击用户
   ↓
查询是否已有私聊会话
   ├─ 有 → 加载历史消息 → 进入私聊
   └─ 无 → 创建新会话 → 进入私聊（无历史）
```

**发送私聊消息：**
```
用户输入消息
   ↓
本地显示（乐观更新）
   ↓
WebSocket 发送（携带 session_id）
   ↓
后端保存到数据库
   ↓
目标用户在线 → 实时推送
目标用户离线 → 消息留存
```

**加载历史记录：**
```
进入私聊会话
   ↓
调用 API: GET /api/messages/session/{session_id}
   ↓
显示历史消息
   ↓
新消息追加显示
```

### 2. 新功能设计

#### 2.1 删除聊天记录按钮

**UI 设计：**
- 每条消息右侧显示删除按钮（hover 时显示）
- 或长按消息弹出操作菜单
- 支持单条删除和批量删除

**功能流程：**
```
点击删除按钮
   ↓
确认弹窗：确定删除这条消息吗？
   ├─ 取消 → 无操作
   └─ 确定 → 调用 DELETE /api/messages/{id}
                  ↓
             本地移除消息
                  ↓
             后端软删除（status=2 已撤回）
```

#### 2.2 自动加载历史记录

**触发时机：**
1. 页面加载完成后，加载会话列表
2. 选择 AI 会话时，加载该会话的消息
3. 选择私聊用户时，先创建/查询会话，再加载消息
4. 分页加载：首次加载最新 50 条，滚动加载更多

**状态管理改进：**

当前 `chat.ts` 私聊消息存储：
```typescript
const privateMessages = ref<PrivateChatHistory>({});  // 仅用户名作为 key
```

改进后：
```typescript
// 私聊会话映射：targetUserId -> sessionId
const privateSessionMap = ref<Map<number, number>>(new Map());

// 私聊消息按 sessionId 存储
const sessionMessages = ref<Map<number, Message[]>>(new Map());
```

### 3. 前端代码改造清单

| 文件 | 改造内容 | 优先级 |
|------|----------|--------|
| `stores/chat.ts` | 私聊会话关联、消息持久化状态管理 | 高 |
| `stores/session.ts` | 扩展私聊会话加载、历史消息加载 | 高 |
| `views/ChatView.vue` | 私聊入口改造、消息删除按钮、历史加载 | 高 |
| `components/ChatMessage.vue` | 增加删除按钮 UI | 中 |
| `services/websocket.ts` | 消息携带 session_id | 中 |

---

## 四、数据流转设计

### 1. AI 对话数据流

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   前端      │         │   后端       │         │   数据库     │
└──────┬──────┘         └──────┬───────┘         └──────┬───────┘
       │                       │                        │
       │ 1. 选择/创建会话      │                        │
       │──────────────────────>│                        │
       │                       │ 2. 查询/创建 Session   │
       │                       │───────────────────────>│
       │                       │<───────────────────────│
       │<──────────────────────│                        │
       │                       │                        │
       │ 3. 发送消息           │                        │
       │──────────────────────>│                        │
       │                       │ 4. 保存用户消息        │
       │                       │───────────────────────>│
       │                       │                        │
       │                       │ 5. 调用 DeepSeek AI    │
       │                       │                        │
       │                       │ 6. 保存 AI 回复        │
       │                       │───────────────────────>│
       │ 7. 返回 AI 回复       │                        │
       │<──────────────────────│                        │
       │                       │                        │
```

### 2. 私聊数据流

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│  用户 A 前端 │         │   后端       │         │  用户 B 前端 │
└──────┬──────┘         └──────┬───────┘         └──────┬───────┘
       │                       │                        │
       │ 1. 点击用户 B         │                        │
       │──────────────────────>│                        │
       │                       │ 2. 查询/创建私聊会话   │
       │                       │   (A<->B)              │
       │<──────────────────────│                        │
       │                       │                        │
       │ 3. 加载历史消息       │                        │
       │──────────────────────>│                        │
       │<──────────────────────│                        │
       │                       │                        │
       │ 4. 发送私聊消息       │                        │
       │──────────────────────>│                        │
       │                       │ 5. 保存到数据库        │
       │                       │                        │
       │                       │ 6. 检查 B 是否在线     │
       │                       │    ├─ 在线 → 推送      │───────────────>│
       │                       │    └─ 离线 → 留存      │
       │                       │                        │
       │                       │                        │ 7. B 上线后
       │                       │                        │    加载历史消息
       │                       │                        │<──────────────│
       │                       │                        │
```

---

## 五、实施步骤

### 阶段一：后端基础改造（优先级：高）

1. **改造 WebSocket 路由**
   - 集成数据库 SessionFactory
   - AI 对话消息持久化
   - 私聊消息持久化

2. **完善 CRUD 操作**
   - 新增 `get_or_create_private_session` 函数
   - 新增 `get_private_sessions_by_user` 函数

### 阶段二：前端基础改造（优先级：高）

1. **改造私聊入口**
   - 点击用户时先创建/查询会话
   - 加载历史消息

2. **改造消息发送**
   - AI 对话：关联 session_id
   - 私聊：关联 session_id

### 阶段三：新增功能（优先级：中）

1. **删除消息功能**
   - 后端：`DELETE /api/messages/{id}`（已存在）
   - 前端：UI 按钮 + 调用 API

2. **历史记录自动加载**
   - 页面加载时加载会话列表
   - 选择会话时加载消息列表

### 阶段四：优化（优先级：低）

1. **新增会话参与者表**
   - 解决双向查询问题
   - 支持多人会话扩展

2. **消息已读状态**
   - 新增阅读状态表
   - 前端显示未读消息数

---

## 六、API 接口清单

### 现有接口（可直接使用）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/sessions` | 创建会话 |
| GET | `/api/sessions` | 获取会话列表 |
| GET | `/api/sessions/{id}` | 获取会话详情 |
| PUT | `/api/sessions/{id}` | 更新会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| GET | `/api/messages/session/{session_id}` | 获取会话消息列表 |
| DELETE | `/api/messages/{id}` | 撤回消息（软删除） |

### 待新增接口

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/sessions/private` | 创建或获取私聊会话 |
| GET | `/api/sessions/private/{target_user_id}` | 获取与指定用户的私聊会话 |
| POST | `/api/messages/batch` | 批量创建消息（可选优化） |
| DELETE | `/api/messages/batch` | 批量删除消息（可选优化） |

---

## 七、注意事项

### 1. 数据一致性

- WebSocket 消息发送和数据库写入需要事务处理
- 失败时需要回滚或补偿机制

### 2. 性能考虑

- 消息写入数据库可能增加延迟
- 考虑使用异步写入或队列
- 历史消息分页加载

### 3. 离线消息

- 私聊目标用户离线时，消息需要留存
- 用户上线时需要推送离线消息
- 或让用户主动加载历史记录

### 4. 安全性

- 消息删除需要权限校验（只能删除自己发送的消息）
- 会话访问需要权限校验（只能访问自己的会话）
