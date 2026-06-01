# 聊天系统前端持久化与登录验证方案书

## 1. 方案概述

### 1.1 背景

当前前端实现存在以下问题：
- 无用户身份认证机制
- 用户名直接使用，无密码保护
- 刷新页面后登录状态丢失
- 聊天历史依赖后端内存存储

### 1.2 目标

- 实现完整的用户注册/登录/登出功能
- 使用 JWT 管理会话状态
- 本地持久化登录状态
- 支持历史消息加载和多会话管理

### 1.3 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| 状态管理 | Pinia | Vue3 官方状态管理 |
| 本地存储 | localStorage | 持久化 Token 和用户信息 |
| HTTP 客户端 | Axios | API 请求封装 |
| 路由守卫 | Vue Router | 页面访问控制 |
| 表单验证 | VeeValidate / 原生 | 表单数据验证 |
| 密码加密 | 前端仅传输，后端加密 | HTTPS 保障传输安全 |

---

## 2. 用户认证流程

### 2.1 认证架构

```
┌─────────────────┐
│   用户操作       │
└────────┬────────┘
         │
┌────────▼────────┐
│   前端表单       │
│  (用户名/密码)   │
└────────┬────────┘
         │ HTTPS POST
┌────────▼────────┐
│   后端验证       │
│  (密码哈希比对)  │
└────────┬────────┘
         │
┌────────▼────────┐
│   JWT Token     │
│  Access + Refresh│
└────────┬────────┘
         │
┌────────▼────────┐
│  前端存储        │
│  localStorage   │
└────────┬────────┘
         │
┌────────▼────────┐
│  后续请求        │
│  Header 携带 Token│
└─────────────────┘
```

### 2.2 状态管理设计

#### 2.2.1 Auth Store (Pinia)

```typescript
// stores/auth.ts
interface AuthState {
  // Token 相关
  accessToken: string | null
  refreshToken: string | null
  tokenExpiresAt: number | null
  
  // 用户信息
  user: User | null
  
  // 状态
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

interface User {
  id: number
  username: string
  nickname: string
  avatar: string | null
  status: number
}
```

#### 2.2.2 Session Store (Pinia)

```typescript
// stores/session.ts
interface SessionState {
  // 当前会话
  currentSessionId: number | null
  currentSession: ChatSession | null
  
  // 会话列表
  sessions: ChatSession[]
  
  // 消息列表（当前会话）
  messages: ChatMessage[]
  
  // 分页
  currentPage: number
  hasMore: boolean
  isLoading: boolean
}

interface ChatSession {
  id: number
  title: string
  sessionType: number  // 1-AI对话, 2-私聊
  targetUserId?: number
  updatedAt: string
  isActive: boolean
}

interface ChatMessage {
  id: number
  sessionId: number
  senderType: number  // 1-用户, 2-AI, 3-系统
  senderId: number | null
  content: string
  messageType: number  // 1-文本, 2-图片, 3-文件
  createdAt: string
  status: number
}
```

### 2.3 本地存储设计

```typescript
// localStorage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'chat_access_token',
  REFRESH_TOKEN: 'chat_refresh_token',
  TOKEN_EXPIRES_AT: 'chat_token_expires_at',
  USER_INFO: 'chat_user_info',
  REMEMBER_ME: 'chat_remember_me'
}
```

---

## 3. 页面路由设计

### 3.1 路由结构

```typescript
// router/index.ts
const routes = [
  {
    path: '/',
    redirect: '/chat',
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: ':sessionId',
        name: 'ChatSession',
        component: () => import('@/views/ChatSession.vue')
      }
    ]
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  }
]
```

### 3.2 路由守卫

```typescript
// router/guard.ts
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 需要登录的页面
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // 尝试从本地恢复登录状态
    const restored = await authStore.restoreFromStorage()
    
    if (!restored) {
      // 跳转登录页，携带重定向地址
      next({
        name: 'Login',
        query: { redirect: to.fullPath }
      })
      return
    }
  }
  
  // 已登录用户访问登录/注册页
  if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next({ name: 'Chat' })
    return
  }
  
  next()
})
```

---

## 4. 页面组件设计

### 4.1 登录页 (Login.vue)

**界面元素：**
- 用户名输入框
- 密码输入框
- 记住我复选框
- 登录按钮
- 忘记密码链接
- 跳转注册链接

**表单验证：**
```typescript
const validationRules = {
  username: [
    required('请输入用户名'),
    minLength(3, '用户名至少3个字符'),
    maxLength(50, '用户名最多50个字符')
  ],
  password: [
    required('请输入密码'),
    minLength(8, '密码至少8个字符'),
    maxLength(50, '密码最多50个字符')
  ]
}
```

**登录逻辑：**
```typescript
const handleLogin = async () => {
  try {
    const response = await authApi.login(formData)
    
    // 保存 Token
    await authStore.saveTokens({
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      expiresIn: response.expires_in
    })
    
    // 保存用户信息
    authStore.setUser(response.user)
    
    // 记住我
    if (formData.rememberMe) {
      localStorage.setItem('chat_remember_username', formData.username)
    }
    
    // 跳转
    const redirect = route.query.redirect as string
    router.push(redirect || '/chat')
    
  } catch (error) {
    showMessage(error.message || '登录失败', 'error')
  }
}
```

### 4.2 注册页 (Register.vue)

**界面元素：**
- 用户名输入框
- 昵称输入框
- 密码输入框
- 确认密码输入框
- 注册按钮
- 跳转登录链接

**表单验证：**
```typescript
const validationRules = {
  username: [
    required('请输入用户名'),
    minLength(3, '用户名至少3个字符'),
    maxLength(50, '用户名最多50个字符'),
    pattern(/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线')
  ],
  nickname: [
    required('请输入昵称'),
    maxLength(50, '昵称最多50个字符')
  ],
  password: [
    required('请输入密码'),
    minLength(8, '密码至少8个字符'),
    maxLength(50, '密码最多50个字符'),
    pattern(/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, '密码需要包含大小写字母和数字')
  ],
  confirmPassword: [
    required('请确认密码'),
    sameAs(password, '两次密码输入不一致')
  ]
}
```

**注册逻辑：**
```typescript
const handleRegister = async () => {
  try {
    await authApi.register(formData)
    
    showMessage('注册成功，请登录', 'success')
    setTimeout(() => {
      router.push({
        name: 'Login',
        query: { username: formData.username }
      })
    }, 1500)
    
  } catch (error) {
    showMessage(error.message || '注册失败', 'error')
  }
}
```

### 4.3 聊天页 (Chat.vue)

**界面布局：**
```
┌─────────────────────────────────────────────────────────────┐
│  左侧边栏 (会话列表)      │      右侧主区域 (聊天内容)        │
├──────────────────────────┼───────────────────────────────────┤
│ ┌──────────────────────┐ │ ┌───────────────────────────────┐ │
│ │ 搜索框              │ │ │ 头部: 会话标题 + 设置按钮     │ │
│ └──────────────────────┘ │ ├───────────────────────────────┤ │
│ ┌──────────────────────┐ │ │                               │ │
│ │ 新建会话按钮         │ │ │     消息列表区域             │ │
│ └──────────────────────┘ │ │    (支持滚动加载历史)        │ │
│                          │ │                               │ │
│ ┌──────────────────────┐ │ ├───────────────────────────────┤ │
│ │ 会话列表             │ │ │                               │ │
│ │ - AI 对话 1          │ │ │ 输入框区域                   │ │
│ │ - AI 对话 2          │ │ │ - 消息输入                   │ │
│ │ - 私聊: user2        │ │ │ - 发送按钮                   │ │
│ └──────────────────────┘ │ └───────────────────────────────┘ │
│                          │                                   │
│ ┌──────────────────────┐ │                                   │
│ │ 底部: 用户信息+登出  │ │                                   │
│ └──────────────────────┘ │                                   │
└──────────────────────────┴───────────────────────────────────┘
```

**会话管理逻辑：**
```typescript
// 创建新会话
const createNewSession = async () => {
  try {
    const session = await sessionApi.create({
      title: '新对话',
      sessionType: 1
    })
    
    sessionStore.addSession(session)
    sessionStore.setCurrentSession(session.id)
    
    // 清空消息列表
    sessionStore.messages = []
    
  } catch (error) {
    showMessage('创建会话失败', 'error')
  }
}

// 切换会话
const switchSession = async (sessionId: number) => {
  sessionStore.setCurrentSession(sessionId)
  sessionStore.messages = []
  sessionStore.currentPage = 1
  sessionStore.hasMore = true
  
  // 加载历史消息
  await loadMessages(sessionId)
}

// 加载历史消息
const loadMessages = async (sessionId: number, page: number = 1) => {
  if (sessionStore.isLoading || !sessionStore.hasMore) return
  
  sessionStore.isLoading = true
  
  try {
    const response = await messageApi.getBySession(sessionId, {
      page,
      limit: 20
    })
    
    // 消息按时间正序排列
    const sortedMessages = [...response.data].reverse()
    sessionStore.messages = [...sortedMessages, ...sessionStore.messages]
    
    sessionStore.hasMore = response.data.length === 20
    sessionStore.currentPage = page
    
  } catch (error) {
    showMessage('加载消息失败', 'error')
  } finally {
    sessionStore.isLoading = false
  }
}
```

### 4.4 用户资料页 (Profile.vue)

**界面元素：**
- 头像预览和上传
- 用户名显示（不可修改）
- 昵称输入框
- 修改密码区域
  - 原密码输入框
  - 新密码输入框
  - 确认新密码输入框
- 保存按钮

---

## 5. API 服务层设计

### 5.1 Axios 拦截器

```typescript
// services/http.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：添加 Token
http.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器：处理 Token 过期
http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const authStore = useAuthStore()
    
    // 401 且不是刷新 Token 请求
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        // 尝试刷新 Token
        const newToken = await authStore.refreshToken()
        
        if (newToken) {
          // 更新原请求的 Token 并重试
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return http(originalRequest)
        }
      } catch (refreshError) {
        // 刷新失败，登出
        authStore.logout()
        router.push('/login')
      }
    }
    
    return Promise.reject(error)
  }
)
```

### 5.2 API 封装

```typescript
// services/auth.ts
import http from './http'

export const authApi = {
  // 注册
  register: (data: RegisterRequest) => 
    http.post('/auth/register', data),
  
  // 登录
  login: (data: LoginRequest) => 
    http.post<LoginResponse>('/auth/login', data),
  
  // 刷新 Token
  refresh: (refreshToken: string) => 
    http.post<RefreshResponse>('/auth/refresh', null, {
      headers: {
        Authorization: `Bearer ${refreshToken}`
      }
    }),
  
  // 登出
  logout: () => 
    http.post('/auth/logout'),
  
  // 获取当前用户
  getCurrentUser: () => 
    http.get<User>('/auth/me')
}
```

```typescript
// services/session.ts
import http from './http'

export const sessionApi = {
  // 获取会话列表
  list: (params?: SessionListParams) => 
    http.get<PaginatedResponse<ChatSession>>('/sessions', { params }),
  
  // 创建会话
  create: (data: CreateSessionRequest) => 
    http.post<ChatSession>('/sessions', data),
  
  // 更新会话
  update: (id: number, data: UpdateSessionRequest) => 
    http.put<ChatSession>(`/sessions/${id}`, data),
  
  // 删除会话
  delete: (id: number) => 
    http.delete(`/sessions/${id}`)
}
```

```typescript
// services/message.ts
import http from './http'

export const messageApi = {
  // 获取会话消息
  getBySession: (sessionId: number, params?: MessageListParams) => 
    http.get<PaginatedResponse<ChatMessage>>(`/sessions/${sessionId}/messages`, { params }),
  
  // 撤回消息
  recall: (messageId: number) => 
    http.delete(`/messages/${messageId}`)
}
```

---

## 6. WebSocket 认证

### 6.1 连接参数

```typescript
// services/websocket.ts
class ChatWebSocket {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  
  connect(authStore: AuthStore) {
    const token = authStore.accessToken
    
    if (!token) {
      throw new Error('未登录')
    }
    
    // 在 URL 中携带 Token（或连接后发送认证消息）
    const wsUrl = `${import.meta.env.VITE_WS_URL}?token=${encodeURIComponent(token)}`
    
    this.ws = new WebSocket(wsUrl)
    
    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      console.log('✅ WebSocket 连接成功')
    }
    
    this.ws.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data))
    }
    
    this.ws.onclose = () => {
      this.handleDisconnect()
    }
    
    this.ws.onerror = (error) => {
      console.error('❌ WebSocket 错误:', error)
    }
  }
}
```

### 6.2 消息处理

```typescript
private handleMessage(data: WebSocketMessage) {
  switch (data.type) {
    case 'ai':
      // AI 回复消息
      this.sessionStore.addMessage({
        id: Date.now(),
        senderType: 2,  // AI
        content: data.content,
        createdAt: new Date().toISOString()
      })
      break
      
    case 'private':
      // 私聊消息
      this.sessionStore.addMessage({
        id: Date.now(),
        senderType: 1,  // 用户
        senderId: data.from,
        content: data.content,
        createdAt: new Date().toISOString()
      })
      break
      
    case 'error':
      showMessage(data.content, 'error')
      break
      
    case 'pong':
      // 心跳响应
      break
  }
}
```

---

## 7. Token 刷新机制

### 7.1 刷新策略

```typescript
// stores/auth.ts
const tokenRefreshBuffer = 60 * 1000  // 提前 60 秒刷新

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    accessToken: null,
    refreshToken: null,
    tokenExpiresAt: null,
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null
  }),
  
  actions: {
    /**
     * 检查 Token 是否即将过期
     */
    shouldRefreshToken(): boolean {
      if (!this.tokenExpiresAt) return false
      
      const now = Date.now()
      return this.tokenExpiresAt - now < tokenRefreshBuffer
    },
    
    /**
     * 刷新 Token
     */
    async refreshToken(): Promise<string | null> {
      if (!this.refreshToken) return null
      
      try {
        const response = await authApi.refresh(this.refreshToken)
        
        this.accessToken = response.access_token
        this.tokenExpiresAt = Date.now() + response.expires_in * 1000
        
        // 保存到本地
        this.saveToStorage()
        
        return response.access_token
        
      } catch (error) {
        console.error('Token 刷新失败:', error)
        this.logout()
        return null
      }
    },
    
    /**
     * 启动自动刷新定时器
     */
    startAutoRefresh() {
      // 检查是否需要立即刷新
      if (this.shouldRefreshToken()) {
        this.refreshToken()
        return
      }
      
      // 计算下次刷新时间
      const refreshDelay = this.tokenExpiresAt! - Date.now() - tokenRefreshBuffer
      
      setTimeout(() => {
        this.refreshToken()
        this.startAutoRefresh()  // 继续下一轮
      }, refreshDelay)
    }
  }
})
```

---

## 8. 安全注意事项

### 8.1 存储安全

| 数据 | 存储位置 | 说明 |
|------|----------|------|
| Access Token | localStorage | 30分钟过期 |
| Refresh Token | localStorage | 7天过期 |
| 用户信息 | localStorage | 缓存使用 |
| 密码 | ❌ 不存储 | 绝对不能存储 |

### 8.2 XSS 防护

- 不要直接将 Token 暴露给 JS（已在 localStorage，需注意）
- 使用 HttpOnly Cookie 更安全（可选方案）
- 所有用户输入进行转义
- 使用 CSP 策略

### 8.3 传输安全

- 生产环境必须使用 HTTPS
- 配置 HSTS
- 不要在 URL 参数中传递敏感信息（除了 WebSocket 的 Token）

### 8.4 登出处理

```typescript
async logout() {
  try {
    // 调用后端登出接口（加入黑名单）
    await authApi.logout()
  } catch (error) {
    console.error('登出请求失败:', error)
  } finally {
    // 清除本地数据
    this.accessToken = null
    this.refreshToken = null
    this.tokenExpiresAt = null
    this.user = null
    this.isAuthenticated = false
    
    // 清除 localStorage
    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key)
    })
    
    // 清除 WebSocket 连接
    webSocket.disconnect()
    
    // 跳转登录页
    router.push('/login')
  }
}
```

---

## 9. 项目文件结构调整

```
frontend/
├── src/
│   ├── components/
│   │   ├── LoginForm.vue           # 登录表单
│   │   ├── RegisterForm.vue        # 注册表单
│   │   ├── SessionList.vue         # 会话列表
│   │   ├── MessageList.vue         # 消息列表
│   │   ├── MessageInput.vue        # 消息输入
│   │   ├── UserAvatar.vue          # 用户头像
│   │   ├── UserMenu.vue            # 用户菜单（含登出）
│   │   └── ProfileForm.vue         # 个人资料表单
│   │
│   ├── views/
│   │   ├── Login.vue               # 登录页
│   │   ├── Register.vue            # 注册页
│   │   ├── Chat.vue                # 聊天页
│   │   ├── ChatSession.vue         # 会话详情页
│   │   └── Profile.vue             # 个人资料页
│   │
│   ├── stores/
│   │   ├── auth.ts                 # 认证状态
│   │   ├── session.ts              # 会话状态
│   │   └── message.ts              # 消息状态
│   │
│   ├── services/
│   │   ├── http.ts                 # Axios 封装
│   │   ├── auth.ts                 # 认证 API
│   │   ├── session.ts              # 会话 API
│   │   ├── message.ts              # 消息 API
│   │   └── websocket.ts            # WebSocket 服务
│   │
│   ├── router/
│   │   ├── index.ts                # 路由定义
│   │   └── guard.ts                # 路由守卫
│   │
│   ├── utils/
│   │   ├── storage.ts              # 本地存储封装
│   │   ├── validation.ts           # 验证规则
│   │   └── format.ts               # 格式化工具
│   │
│   └── types/
│       ├── auth.ts                 # 认证类型
│       ├── session.ts              # 会话类型
│       ├── message.ts              # 消息类型
│       └── api.ts                  # API 响应类型
│
├── .env                            # 环境变量
└── .env.example                    # 环境变量示例
```

---

## 10. 测试计划

### 10.1 功能测试

| 功能 | 测试点 |
|------|--------|
| 注册 | 用户名格式、密码强度、重复用户名 |
| 登录 | 正确凭证、错误密码、已禁用账号 |
| Token | 自动刷新、过期处理、黑名单 |
| 会话 | 创建、切换、删除、重命名 |
| 消息 | 发送、接收、历史加载、分页 |
| 权限 | 未登录跳转、已登录访问登录页 |

### 10.2 边界测试

- Token 刚好过期时的请求
- 网络断开重连
- 刷新页面后的状态恢复
- 多个标签页登录同步

---

## 11. 环境变量配置

```env
# .env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_TIMEOUT=15000
VITE_TOKEN_REFRESH_BUFFER=60000
VITE_MAX_RECONNECT_ATTEMPTS=5
```

---

**文档版本**: v1.0  
**创建日期**: 2026-06-01  
**适用项目**: 聊天系统前端