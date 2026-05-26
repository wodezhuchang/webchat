import asyncio
import json

with open("./config/client_config.json", "r") as f:
    config = json.load(f)

SERVER_HOST = config["server"]["host"]
SERVER_PORT = config["server"]["port"]
HEARTBEAT_INTERVAL = config["heartbeat"]["interval"]

async def send_json(writer: asyncio.StreamWriter, data: dict):
    msg = json.dumps(data, ensure_ascii=False)
    msg_bytes = msg.encode("utf-8")
    writer.write(len(msg_bytes).to_bytes(4, "big"))
    writer.write(msg_bytes)
    await writer.drain()

async def recv_json(reader: asyncio.StreamReader):
    raw_len = await reader.readexactly(4)
    data_len = int.from_bytes(raw_len, "big")
    if data_len == 0:
        return None
    data = await reader.readexactly(data_len)
    return json.loads(data.decode("utf-8"))

async def heartbeat_task(writer):
    """只发送心跳，不等待响应（避免与接收协程冲突）"""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        try:
            await send_json(writer, {"type": "ping"})
        except:
            print("心跳发送失败，连接中断")
            break

async def receive_messages(reader):
    """唯一接收消息的协程，处理所有服务器推送"""
    while True:
        try:
            msg = await recv_json(reader)
            if msg is None:
                break
            msg_type = msg.get("type")
            if msg_type == "pong":
                # 忽略，服务端心跳响应，无需处理
                continue
            elif msg_type == "private":
                from_user = msg.get("from", "未知")
                content = msg.get("content", "")
                print(f"\n[私聊] {from_user}: {content}")
                print("你: ", end="", flush=True)
            elif msg_type == "ai":
                print(f"\n[AI]: {msg.get('content')}")
                print("你: ", end="", flush=True)
            elif msg_type == "users":
                users = msg.get("users", [])
                print("\n[在线用户]: " + ", ".join(users))
                print("你: ", end="", flush=True)
            elif msg_type == "info":
                print(f"\n[系统] {msg.get('content')}")
                print("你: ", end="", flush=True)
            elif msg_type == "error":
                print(f"\n[错误] {msg.get('content')}")
                print("你: ", end="", flush=True)
        except Exception as e:
            print(f"\n接收消息错误: {e}")
            break

async def main():
    reader, writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)
    print("已连接到服务器")

    username = input("请输入用户名: ").strip()
    if not username:
        print("用户名不能为空")
        return
    await send_json(writer, {"type": "login", "username": username})
    login_resp = await recv_json(reader)
    if login_resp.get("type") != "login_ok":
        print(f"登录失败: {login_resp.get('content')}")
        return
    print(login_resp.get("content"))

    # 启动心跳（只发送）和后台接收协程
    asyncio.create_task(heartbeat_task(writer))
    asyncio.create_task(receive_messages(reader))

    print("\n使用说明:")
    print("  - 直接输入文字: 发送给AI")
    print("  - @用户名 消息内容: 发送私聊")
    print("  - /users : 查看在线用户")
    print("  - /quit : 退出")
    print("-" * 40)

    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, "你: ")
        if user_input.lower() == "/quit":
            break
        if user_input.startswith("@"):
            parts = user_input.split(" ", 1)
            if len(parts) < 2:
                print("格式错误: @用户名 消息内容")
                continue
            to_user = parts[0][1:]
            content = parts[1]
            await send_json(writer, {"type": "user", "to": to_user, "content": content})
        elif user_input == "/users":
            await send_json(writer, {"type": "users"})
        elif user_input.strip():
            await send_json(writer, {"type": "ai", "content": user_input})

    writer.close()
    await writer.wait_closed()
    print("已退出")

if __name__ == "__main__":
    asyncio.run(main())