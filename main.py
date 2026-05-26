import asyncio
import json


async def send_message(writer: asyncio.StreamWriter, message: str):
    """仅发送消息，不等待回复"""
    msg_data = message.encode("utf-8")
    writer.write(len(msg_data).to_bytes(4, "big"))
    writer.write(msg_data)
    await writer.drain()

async def receive_messages(reader: asyncio.StreamReader):
    """专门负责接收服务器消息的后台任务"""
    while True:
        try:
            raw_len = await reader.readexactly(4)
            data_len = int.from_bytes(raw_len, "big")
            if data_len == 0:
                continue
            data = await reader.readexactly(data_len)
            message = data.decode("utf-8")

            if message == "PONG":
                # 心跳响应，忽略（或可打印调试信息）
                print("[心跳] 接收PONG")
                continue

            # 普通回复（AI 回答）显示出来
            print(f"\n助手: {message}")
            print("你: ", end="", flush=True)
        except asyncio.IncompleteReadError:
            print("\n连接已断开")
            break
        except Exception as e:
            print(f"\n接收错误: {e}")
            break

async def heartbeat_task(writer: asyncio.StreamWriter):
    """定期发送心跳 PING，不等待响应"""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        try:
            await send_message(writer, "PING")
            # 可选：打印心跳日志
            print("[心跳] 发送PING")
        except Exception as e:
            print(f"心跳发送失败: {e}")
            break

# 加载客户端配置
with open("./config/client_config.json", "r") as f:
    config = json.load(f)



SERVER_HOST = config["server"]["host"]
SERVER_PORT = config["server"]["port"]
HEARTBEAT_INTERVAL = config["heartbeat"]["interval"]



async def main():
    reader, writer = await asyncio.open_connection(SERVER_HOST, SERVER_PORT)
    print("已连接到服务器")

    # 启动后台任务：接收消息 和 心跳发送
    asyncio.create_task(receive_messages(reader))
    asyncio.create_task(heartbeat_task(writer))

    print("多轮对话客户端 (输入 'quit' 退出)")
    while True:
        # 使用 run_in_executor 避免阻塞事件循环
        question = await asyncio.get_event_loop().run_in_executor(None, input, "你: ")
        if question.lower() == "quit":
            break
        if not question:
            continue
        # 发送用户消息，回复会由 receive_messages 自动打印
        await send_message(writer, question)

if __name__ == "__main__":
    asyncio.run(main())









