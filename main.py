from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from config import settings
from utils import chat_histories, online_users
from models import Message, UserInfo
app = FastAPI(title="Chat WebAPI", version="1.0.0", description="基于FastAPI的聊天系统后端接口")
app.add_middleware(
 CORSMiddleware,
 allow_origins=["*"],
 allow_credentials=True,
 allow_methods=["*"],
 allow_headers=["*"],
)
app.include_router(router, prefix="/api")
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
 await websocket.accept()
 online_users[username] = websocket
 if username not in chat_histories:
 chat_histories[username] = []
 try:
 while True:
 data = await websocket.receive_json()
 message_type = data.get("type")
 content = data.get("content", "")
 if message_type == "ai":
 from utils import call_deepseek_async
 history = chat_histories[username]
 history.append({"role": "user", "content": content})
 answer = await call_deepseek_async(history)
 history.append({"role": "assistant", "content": answer})
 await websocket.send_json({"type": "ai", "content": answer})
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
 elif message_type == "users":
 user_list = list(online_users.keys())
 await websocket.send_json({"type": "users", "users": user_list})
 elif message_type == "ping":
 await websocket.send_json({"type": "pong"})
 except WebSocketDisconnect:
 online_users.pop(username, None)
 print(f"用户 {username} 已断开连接")
@app.get("/")
async def root():
 return {"message": "Chat WebAPI 运行中"}
@app.get("/health")
async def health_check():
 return {"status": "healthy"}
if __name__ == "__main__":
 import uvicorn
 uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)