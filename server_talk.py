import asyncio
import json
import time
import aiohttp
from typing import Dict, List, Optional

# 加载配置
with open("server_config.json", "r") as f:
    config = json.load(f)

SERVER_HOST = config["server"]["host"]
SERVER_PORT = config["server"]["port"]
API_URL = config["deepseek"]["api_url"]
API_KEY = config["deepseek"]["api_key"]
API_TIMEOUT = config["deepseek"]["timeout"]
HEARTBEAT_INTERVAL = config["heartbeat"]["interval"]
HEARTBEAT_TIMEOUT = config["heartbeat"]["timeout"]

# 在线用户: username -> (writer, reader)
online_users: Dict[str, asyncio.StreamWriter] = {}
# 对话历史: username -> list of messages (用于AI)
chat_histories: Dict[str, List[Dict]] = {}
# 最后活动时间: writer -> float
last_activity: Dict[asyncio.StreamWriter, float] = {}

async def call_deepseek_async(messages: List[Dict]) -> str:
    """调用DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "stream": False
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=payload, timeout=API_TIMEOUT) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return f"API错误({resp.status}): {text}"
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except asyncio.TimeoutError:
        return "API调用超时"
    except Exception as e:
        return f"API调用异常: {str(e)}"

async def send_json(writer: asyncio.StreamWriter, data: dict):
    """发送JSON消息 (长度前缀+JSON字符串)"""
    msg = json.dumps(data, ensure_ascii=False)
    msg_bytes = msg.encode("utf-8")
    writer.write(len(msg_bytes).to_bytes(4, "big"))
    writer.write(msg_bytes)
    await writer.drain()

async def recv_json(reader: asyncio.StreamReader) -> Optional[dict]:
    """接收JSON消息，失败返回None"""
    try:
        raw_len = await reader.readexactly(4)
    except asyncio.IncompleteReadError:
        return None
    data_len = int.from_bytes(raw_len, "big")
    if data_len == 0:
        return None
    data = await reader.readexactly(data_len)
    return json.loads(data.decode("utf-8"))

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    print(f"[连接] {addr}")
    username = None
    last_activity[writer] = time.time()

    try:
        # 1. 等待登录消息
        login_msg = await recv_json(reader)
        if not login_msg or login_msg.get("type") != "login":
            await send_json(writer, {"type": "error", "content": "请先登录"})
            return
        username = login_msg.get("username", "").strip()
        if not username:
            await send_json(writer, {"type": "error", "content": "用户名不能为空"})
            return
        if username in online_users:
            await send_json(writer, {"type": "error", "content": "用户名已被占用"})
            return
        # 登录成功
        online_users[username] = writer
        # 初始化对话历史（若没有则新建）
        if username not in chat_histories:
            chat_histories[username] = []
        await send_json(writer, {"type": "login_ok", "content": f"欢迎 {username}"})
        print(f"[登录] {username} ({addr})")

        # 主循环处理消息
        while True:
            # 更新活动时间
            last_activity[writer] = time.time()
            # 接收消息（带超时检测，但不会真正超时，因为心跳会维持连接）
            msg = await recv_json(reader)
            if msg is None:
                break

            msg_type = msg.get("type")
            if msg_type == "ping":
                # 心跳响应
                await send_json(writer, {"type": "pong"})
                continue
            elif msg_type == "ai":
                # 处理AI对话
                content = msg.get("content", "")
                if not content:
                    continue
                # 获取该用户的对话历史
                history = chat_histories[username]
                history.append({"role": "user", "content": content})
                answer = await call_deepseek_async(history)
                history.append({"role": "assistant", "content": answer})
                # 发送AI回复
                await send_json(writer, {"type": "ai", "content": answer})
                print(f"[AI] {username}: {content[:30]}...")
            elif msg_type == "user":
                # 私聊
                to_user = msg.get("to")
                content = msg.get("content", "")
                if not to_user or not content:
                    await send_json(writer, {"type": "error", "content": "缺少收件人或内容"})
                    continue
                if to_user not in online_users:
                    await send_json(writer, {"type": "error", "content": f"用户 {to_user} 不在线"})
                    continue
                # 转发消息
                target_writer = online_users[to_user]
                await send_json(target_writer, {
                    "type": "private",
                    "from": username,
                    "content": content
                })
                # 给发送方一个回执（可选）
                await send_json(writer, {"type": "info", "content": f"已发送给 {to_user}"})
                print(f"[私聊] {username} -> {to_user}: {content[:30]}...")
            elif msg_type == "users":
                # 查询在线用户列表
                user_list = list(online_users.keys())
                await send_json(writer, {"type": "users", "users": user_list})
            else:
                await send_json(writer, {"type": "error", "content": "未知消息类型"})
    except Exception as e:
        print(f"[异常] {addr}: {e}")
    finally:
        # 清理
        if username:
            online_users.pop(username, None)
            print(f"[登出] {username}")
        last_activity.pop(writer, None)
        writer.close()
        await writer.wait_closed()
        print(f"[断开] {addr}")

async def heartbeat_monitor():
    """检查超时未活动的连接（没有收发任何消息）"""
    while True:
        await asyncio.sleep(5)
        now = time.time()
        for writer, last_time in list(last_activity.items()):
            if now - last_time > HEARTBEAT_TIMEOUT:
                addr = writer.get_extra_info('peername')
                print(f"[超时断开] {addr}")
                writer.close()
                # 注意：这里不会直接删除online_users，因为finally块会处理

async def main():
    server = await asyncio.start_server(handle_client, SERVER_HOST, SERVER_PORT)
    print(f"服务端启动 {SERVER_HOST}:{SERVER_PORT}")
    asyncio.create_task(heartbeat_monitor())
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())