# 前端开发文档

## 1. 项目概述

本项目是基于 Vue3 构建的聊天系统前端应用，与 FastAPI 后端对接，提供 AI 对话、用户私聊、在线用户管理等功能。

### 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.4+ | 前端框架 |
| Vite | 5.0+ | 构建工具 |
| TypeScript | 5.3+ | 类型安全 |
| TailwindCSS | 3.4+ | 样式框架 |
| Pinia | 2.1+ | 状态管理 |
| Socket.IO Client | 4.6+ | WebSocket 客户端 |

## 2. 项目结构

```
frontend/
├── src/
│   ├── components/           # 组件目录
│   │   ├── ChatMessage.vue   # 聊天消息组件
│   │   ├── UserList.vue      # 用户列表组件
│   │   ├── LoginModal.vue    # 登录弹窗组件
│   │   └── MessageInput.vue  # 消息输入组件
│   ├── views/                # 页面视图
│   │   └── ChatView.vue      # 聊天主页面
│   ├── stores/               # 状态管理
│   │   └── chat.ts           # 聊天状态
│   ├── services/             # 服务层
│   │   ├── api.ts            # REST API 封装
│   │   └── websocket.ts      # WebSocket 封装
│   ├── types/                # 类型定义
│   │   └── index.ts          # 类型声明
│   ├── App.vue               # 根组件
│   ├── main.ts               # 入口文件
│   └── style.css             # 全局样式
├── public/                   # 静态资源
├── index.html               # HTML 模板
├── package.json             # 项目配置
├── vite.config.ts           # Vite 配置
├── tailwind.config.js       # TailwindCSS 配置
└── tsconfig.json            # TypeScript 配置
```

## 3. 核心组件

### 3.1 ChatMessage 组件

**功能**: 展示单条聊天消息

**Props**:
| 属性 | 类型 | 说明 |
|------|------|------|
| message | Message | 消息对象 |
| isOwn | boolean | 是否为自己发送 |

**使用示例**:
```vue
<ChatMessage :message="msg" :is-own="msg.role === 'user'" />
```

### 3.2 UserList 组件

**功能**: 展示在线用户列表

**Props**:
| 属性 | 类型 | 说明 |
|------|------|------|
| users | string[] | 在线用户列表 |
| currentUser | string | 当前用户 |

**事件**:
| 事件 | 参数 | 说明 |
|------|------|------|
| select-user | username | 选择用户进行私聊 |

### 3.3 MessageInput 组件

**功能**: 消息输入框

**Props**:
| 属性 | 类型 | 说明 |
|------|------|------|
| placeholder | string | 占位文本 |

**事件**:
| 事件 | 参数 | 说明 |
|------|------|------|
| send | string | 发送消息 |

### 3.4 LoginModal 组件

**功能**: 用户登录弹窗

**事件**:
| 事件 | 参数 | 说明 |
|------|------|------|
| login | username | 用户登录 |

## 4. 状态管理

### 4.1 Chat Store

**状态**:
| 状态 | 类型 | 说明 |
|------|------|------|
| currentUser | string | 当前用户名 |
| messages | Message[] | 消息列表 |
| onlineUsers | string[] | 在线用户列表 |
| isConnected | boolean | WebSocket 连接状态 |
| selectedUser | string | 当前选中的私聊用户 |

**Actions**:
| 方法 | 参数 | 说明 |
|------|------|------|
| login | username | 用户登录 |
| sendMessage | content | 发送消息 |
| sendPrivateMessage | to, content | 发送私聊 |
| getOnlineUsers | - | 获取在线用户 |
| connectWebSocket | - | 连接 WebSocket |
| disconnectWebSocket | - | 断开 WebSocket |

## 5. 服务层

### 5.1 API 服务 (api.ts)

**方法**:
| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| login | username: string | Promise\<LoginResponse\> | 用户登录 |
| chat | username: string, message: string | Promise\<ChatResponse\> | AI 对话 |
| getOnlineUsers | - | Promise\<OnlineUsersResponse\> | 获取在线用户 |
| sendPrivate | from, to, content | Promise\<PrivateMessageResponse\> | 发送私聊 |
| getHistory | username: string | Promise\<HistoryResponse\> | 获取聊天历史 |

### 5.2 WebSocket 服务 (websocket.ts)

**方法**:
| 方法 | 参数 | 说明 |
|------|------|------|
| connect | username: string | 连接 WebSocket |
| disconnect | - | 断开连接 |
| send | data: object | 发送消息 |

**事件监听**:
| 事件 | 说明 |
|------|------|
| message | 接收消息 |
| connect | 连接成功 |
| disconnect | 连接断开 |
| error | 连接错误 |

## 6. 类型定义

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'private';
  content: string;
  from?: string;
  timestamp: Date;
}

interface LoginResponse {
  success: boolean;
  message: string;
}

interface ChatResponse {
  success: boolean;
  content: string;
  error: string;
}

interface OnlineUsersResponse {
  success: boolean;
  users: string[];
}

interface PrivateMessageResponse {
  success: boolean;
  message: string;
}

interface WebSocketMessage {
  type: 'ai' | 'user' | 'users' | 'ping' | 'pong' | 'private' | 'info' | 'error';
  content?: string;
  to?: string;
  from?: string;
  users?: string[];
}
```

## 7. 配置说明

### 7.1 环境变量

创建 `.env` 文件：

```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

### 7.2 API 配置

```typescript
// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
```

## 8. 核心流程

### 8.1 登录流程

```
用户输入用户名 → 调用 login API → 成功后连接 WebSocket → 更新状态
```

### 8.2 发送消息流程

```
用户输入 → 发送到 WebSocket → 服务端处理 → 接收响应 → 更新消息列表
```

### 8.3 私聊流程

```
选择用户 → 切换到私聊模式 → 发送私聊消息 → 接收私聊响应
```

### 8.4 心跳机制

```
定时发送 ping → 接收 pong → 检测连接状态
```

## 9. 部署说明

### 9.1 开发环境

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 9.2 生产构建

```bash
# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

### 9.3 部署建议

- 使用 Nginx 反向代理
- 配置 HTTPS
- 设置适当的 CORS 策略

## 10. 代码示例

### 10.1 WebSocket 连接示例

```typescript
import { ref, onMounted, onUnmounted } from 'vue';

const ws = ref<WebSocket | null>(null);

const connectWebSocket = (username: string) => {
  ws.value = new WebSocket(`${WS_URL}/${username}`);
  
  ws.value.onopen = () => {
    console.log('WebSocket connected');
  };
  
  ws.value.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
  };
  
  ws.value.onclose = () => {
    console.log('WebSocket disconnected');
  };
};

const sendMessage = (data: object) => {
  ws.value?.send(JSON.stringify(data));
};
```

### 10.2 发送 AI 消息

```typescript
const sendMessage = async (content: string) => {
  await api.chat(currentUser, content);
};
```

### 10.3 发送私聊消息

```typescript
const sendPrivateMessage = async (to: string, content: string) => {
  await api.sendPrivate(currentUser, to, content);
};
```

## 11. 注意事项

1. **WebSocket 重连**: 需要实现断线重连机制
2. **消息去重**: 处理重复消息
3. **错误处理**: 完善的错误提示
4. **性能优化**: 虚拟列表优化大量消息渲染
5. **样式适配**: 响应式设计适配不同屏幕