from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from config import settings
from utils import chat_histories, online_users, call_deepseek_async
from models import Message, UserInfo
import asyncio

from api.auth import router as auth_router
from api.sessions import router as sessions_router
from api.messages import router as messages_router
from database.connection import engine
from database import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chat WebAPI", version="1.0.0", description="基于FastAPI的聊天系统后端接口")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(messages_router, prefix="/api")


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    
    if username in online_users:
        try:
            old_ws = online_users[username]
            await old_ws.close(code=1008, reason="检测到新的连接")
        except:
            pass
    
    online_users[username] = websocket
    
    if username not in chat_histories:
        chat_histories[username] = []
    
    print(f"✅ 用户 {username} 连接成功，在线用户数: {len(online_users)}")
    
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except Exception as e:
                print(f"❌ 用户 {username} 接收消息异常:", e)
                break
            
            message_type = data.get("type")
            content = data.get("content", "")
            
            if message_type == "ai":
                history = chat_histories[username]
                history.append({"role": "user", "content": content})
                try:
                    answer = await asyncio.wait_for(call_deepseek_async(history), timeout=15)
                except asyncio.TimeoutError:
                    answer = "请求超时，请重试"
                except Exception as e:
                    answer = f"AI 出错：{str(e)}"
                
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
        print(f"👋 用户 {username} 主动断开")
    finally:
        if username in online_users and online_users[username] == websocket:
            online_users.pop(username, None)
            print(f"🧹 用户 {username} 资源清理完毕，在线用户数: {len(online_users)}")


@app.get("/")
async def root():
    return {"message": "Chat WebAPI 运行中"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/db-test")
async def db_test():
    from database.connection import SessionLocal
    from sqlalchemy import text
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT VERSION()"))
        version = result.scalar()
        db.close()
        return {"success": True, "mysql_version": version}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
