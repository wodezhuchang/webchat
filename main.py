from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from config import settings
from utils import chat_histories, online_users, call_deepseek_async
from models import Message, UserInfo
import asyncio
from datetime import datetime

from api.auth import router as auth_router
from api.conversations import router as conversations_router
from api.sessions import router as sessions_router
from api.messages import router as messages_router
from api.users import router as users_router
from database.connection import engine, SessionLocal
from database import models
from database import crud

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chat WebAPI", version="2.0.0", description="基于FastAPI的聊天系统后端接口 - 支持私聊和AI对话")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(conversations_router)
app.include_router(sessions_router)
app.include_router(messages_router)
app.include_router(users_router, prefix="/api")


def get_user_id_by_username(username: str) -> int:
    db = SessionLocal()
    try:
        user = crud.get_user_by_username(db, username)
        return user.id if user else None
    finally:
        db.close()
    return None


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

    print(f"[WS] User {username} connected, online: {len(online_users)}")

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except Exception as e:
                print(f"[WS] User {username} receive error:", e)
                break

            message_type = data.get("type")
            content = data.get("content", "")
            conversation_id = data.get("conversation_id")

            if message_type == "ai":
                db = SessionLocal()
                try:
                    current_user_id = get_user_id_by_username(username)
                    
                    if current_user_id is None:
                        await websocket.send_json({"type": "error", "content": "User not found"})
                        continue
                    
                    conv = None
                    if conversation_id:
                        conv = crud.get_conversation_by_id(db, conversation_id)
                        participant = crud.get_participant_by_user(db, conversation_id, current_user_id)
                        if not conv or not participant or participant.is_deleted:
                            await websocket.send_json({"type": "error", "content": "Conversation not found or no permission"})
                            continue
                    else:
                        conv, _ = crud.get_or_create_ai_conversation(db, current_user_id)
                        conversation_id = conv.id
                    
                    crud.create_message_with_visibility(
                        db=db,
                        conversation_id=conversation_id,
                        sender_type=1,
                        content=content,
                        sender_id=current_user_id
                    )
                    
                    history = chat_histories[username]
                    history.append({"role": "user", "content": content})
                    
                    try:
                        answer = await asyncio.wait_for(call_deepseek_async(history), timeout=15)
                    except asyncio.TimeoutError:
                        answer = "Request timeout, please try again"
                    except Exception as e:
                        answer = f"AI error: {str(e)}"
                    
                    history.append({"role": "assistant", "content": answer})
                    
                    ai_message = crud.create_message_with_visibility(
                        db=db,
                        conversation_id=conversation_id,
                        sender_type=2,
                        content=answer
                    )
                    
                    await websocket.send_json({
                        "type": "ai",
                        "content": answer,
                        "conversation_id": conversation_id,
                        "message_id": ai_message.id,
                        "timestamp": ai_message.created_at.isoformat() if ai_message.created_at else ""
                    })
                finally:
                    db.close()
            
            elif message_type == "user":
                to_user = data.get("to")
                db = SessionLocal()
                try:
                    current_user_id = get_user_id_by_username(username)
                    target_user = crud.get_user_by_username(db, to_user)
                    
                    if not target_user:
                        await websocket.send_json({"type": "error", "content": f"User {to_user} not found"})
                        continue
                    
                    if current_user_id is None:
                        await websocket.send_json({"type": "error", "content": "User not found"})
                        continue
                    
                    conv, _ = crud.get_or_create_private_conversation(
                        db=db,
                        user_id=current_user_id,
                        target_user_id=target_user.id
                    )
                    conversation_id = conv.id
                    
                    message = crud.create_message_with_visibility(
                        db=db,
                        conversation_id=conversation_id,
                        sender_type=1,
                        content=content,
                        sender_id=current_user_id
                    )
                    
                    if to_user in online_users:
                        target_ws = online_users[to_user]
                        await target_ws.send_json({
                            "type": "private",
                            "from": username,
                            "from_id": current_user_id,
                            "content": content,
                            "conversation_id": conversation_id,
                            "message_id": message.id,
                            "timestamp": message.created_at.isoformat() if message.created_at else datetime.utcnow().isoformat()
                        })
                        await websocket.send_json({
                            "type": "info",
                            "content": f"Sent to {to_user}",
                            "conversation_id": conversation_id,
                            "message_id": message.id,
                            "timestamp": message.created_at.isoformat() if message.created_at else ""
                        })
                    else:
                        await websocket.send_json({
                            "type": "info",
                            "content": f"User {to_user} is offline, message saved",
                            "conversation_id": conversation_id,
                            "message_id": message.id,
                            "timestamp": message.created_at.isoformat() if message.created_at else ""
                        })
                except Exception as e:
                    print(f"[WS] Private message error:", e)
                    await websocket.send_json({"type": "error", "content": f"Send failed: {str(e)}"})
                finally:
                    db.close()
            
            elif message_type == "users":
                user_list = list(online_users.keys())
                await websocket.send_json({"type": "users", "users": user_list})
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        print(f"[WS] User {username} disconnected")
    finally:
        if username in online_users and online_users[username] == websocket:
            online_users.pop(username, None)
            print(f"[WS] User {username} cleaned up, online: {len(online_users)}")


@app.get("/")
async def root():
    return {"message": "Chat WebAPI Running (v2.0)"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/db-test")
async def db_test():
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
