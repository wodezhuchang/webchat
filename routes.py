from fastapi import APIRouter, HTTPException
from models import (
    ChatRequest, ChatResponse,
    OnlineUsersResponse,
    PrivateMessageRequest, PrivateMessageResponse,
    LoginRequest, LoginResponse
)
from utils import chat_histories, online_users, call_deepseek_async

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    try:
        username = request.username
        message = request.message
        
        if username not in chat_histories:
            chat_histories[username] = []
        
        history = chat_histories[username]
        history.append({"role": "user", "content": message})
        
        answer = await call_deepseek_async(history)
        history.append({"role": "assistant", "content": answer})
        
        return ChatResponse(success=True, content=answer)
    except Exception as e:
        return ChatResponse(success=False, error=str(e))


@router.get("/users", response_model=OnlineUsersResponse)
async def get_online_users():
    users = list(online_users.keys())
    return OnlineUsersResponse(success=True, users=users)


@router.post("/private", response_model=PrivateMessageResponse)
async def send_private_message(request: PrivateMessageRequest):
    from_user = request.from_user
    to_user = request.to_user
    content = request.content
    
    if to_user not in online_users:
        return PrivateMessageResponse(success=False, message=f"用户 {to_user} 不在线")
    
    target_ws = online_users[to_user]
    
    try:
        await target_ws.send_json({
            "type": "private",
            "from": from_user,
            "content": content
        })
        return PrivateMessageResponse(success=True, message=f"已发送给 {to_user}")
    except Exception as e:
        return PrivateMessageResponse(success=False, message=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    username = request.username.strip()
    
    if not username:
        return LoginResponse(success=False, message="用户名不能为空")
    
    if username in online_users:
        return LoginResponse(success=False, message="用户名已被占用")
    
    return LoginResponse(success=True, message=f"欢迎 {username}")


@router.get("/history/{username}")
async def get_chat_history(username: str):
    if username not in chat_histories:
        return {"success": True, "history": []}
    return {"success": True, "history": chat_histories[username]}