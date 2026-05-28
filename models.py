from pydantic import BaseModel, Field
from typing import List, Optional, Dict
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