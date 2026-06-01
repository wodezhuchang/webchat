from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class Message(BaseModel):
    role: str = Field(..., description="消息角色: user 或 assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的消息")
    username: str = Field(..., description="用户名")


class ChatResponse(BaseModel):
    success: bool = Field(default=True, description="请求是否成功")
    content: str = Field("", description="AI回复内容")
    error: str = Field("", description="错误信息")


class UserInfo(BaseModel):
    username: str = Field(..., description="用户名")
    is_online: bool = Field(default=True, description="是否在线")


class OnlineUsersResponse(BaseModel):
    success: bool = Field(default=True, description="请求是否成功")
    users: List[str] = Field(default_factory=list, description="在线用户列表")


class PrivateMessageRequest(BaseModel):
    from_user: str = Field(..., description="发送方用户名")
    to_user: str = Field(..., description="接收方用户名")
    content: str = Field(..., description="消息内容")


class PrivateMessageResponse(BaseModel):
    success: bool = Field(default=True, description="请求是否成功")
    message: str = Field("", description="操作结果消息")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")


class LoginResponse(BaseModel):
    success: bool = Field(default=True, description="登录是否成功")
    message: str = Field("", description="登录结果消息")


class WebSocketMessage(BaseModel):
    type: str = Field(..., description="消息类型: ai, user, users, ping, pong, private, info, error")
    content: Optional[str] = Field(None, description="消息内容")
    to: Optional[str] = Field(None, description="接收方用户名")
    users: Optional[List[str]] = Field(None, description="用户列表")


# ============================================
# 新增：认证相关 Pydantic 模型
# ============================================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=8, max_length=50)
    confirm_password: str = Field(..., description="确认密码")
    nickname: Optional[str] = Field(None, description="昵称", max_length=50)


class UserLoginRequest(BaseModel):
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    password: str = Field(..., description="密码", min_length=8, max_length=50)


class UserResponse(BaseModel):
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    status: int = Field(..., description="状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


class AuthLoginResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    message: str = Field("", description="消息")
    access_token: Optional[str] = Field(None, description="Access Token")
    refresh_token: Optional[str] = Field(None, description="Refresh Token")
    token_type: str = Field("bearer", description="Token 类型")
    expires_in: Optional[int] = Field(None, description="过期时间（秒）")
    user: Optional[UserResponse] = Field(None, description="用户信息")


class AuthRefreshResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    access_token: str = Field(..., description="新的 Access Token")
    token_type: str = Field("bearer", description="Token 类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class AuthLogoutResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    message: str = Field("", description="消息")


class ApiResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    message: str = Field("", description="消息")
    data: Optional[Dict] = Field(None, description="数据")


# ============================================
# 新增：会话相关 Pydantic 模型
# ============================================

class SessionCreateRequest(BaseModel):
    title: str = Field("新对话", description="会话标题", max_length=100)
    session_type: int = Field(1, description="会话类型: 1-AI对话, 2-私聊")
    target_user_id: Optional[int] = Field(None, description="私聊目标用户ID")


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="会话标题", max_length=100)


class SessionResponse(BaseModel):
    id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    title: str = Field(..., description="会话标题")
    session_type: int = Field(..., description="会话类型")
    target_user_id: Optional[int] = Field(None, description="私聊目标用户ID")
    is_active: int = Field(..., description="是否活跃")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    sessions: List[SessionResponse] = Field(default_factory=list, description="会话列表")


# ============================================
# 新增：消息相关 Pydantic 模型
# ============================================

class MessageResponse(BaseModel):
    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="会话ID")
    sender_type: int = Field(..., description="发送者类型: 1-用户, 2-AI, 3-系统")
    sender_id: Optional[int] = Field(None, description="发送者用户ID")
    content: str = Field(..., description="消息内容")
    message_type: int = Field(..., description="消息类型: 1-文本, 2-图片, 3-文件")
    media_url: Optional[str] = Field(None, description="媒体文件URL")
    status: int = Field(..., description="状态: 1-正常, 2-已撤回")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    success: bool = Field(default=True, description="是否成功")
    messages: List[MessageResponse] = Field(default_factory=list, description="消息列表")
    total: int = Field(0, description="总数")
    page: int = Field(1, description="当前页")
    limit: int = Field(20, description="每页数量")
    has_more: bool = Field(False, description="是否还有更多")
