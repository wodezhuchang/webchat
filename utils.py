import asyncio
import aiohttp
from typing import List, Dict, Optional
from config import settings
online_users: Dict[str, object] = {}
chat_histories: Dict[str, List[Dict]] = {}
async def call_deepseek_async(messages: List[Dict]) -> str:
 headers = {
 "Authorization": f"Bearer {settings.API_KEY}",
 "Content-Type": "application/json"
 }
 payload = {
 "model": "deepseek-chat",
 "messages": messages,
 "stream": False
 }
 try:
 async with aiohttp.ClientSession() as session:
 async with session.post(
 settings.API_URL,
 headers=headers,
 json=payload,
 timeout=aiohttp.ClientTimeout(total=settings.API_TIMEOUT)
 ) as resp:
 if resp.status != 200:
 text = await resp.text()
 return f"API错误({resp.status}): {text}"
 data = await resp.json()
 return data["choices"][0]["message"]["content"]
 except asyncio.TimeoutError:
 return "API调用超时"
 except Exception as e:
 return f"API调用异常: {str(e)}"
async def send_json(writer, data: dict):
 import json
 msg = json.dumps(data, ensure_ascii=False)
 msg_bytes = msg.encode("utf-8")
 writer.write(len(msg_bytes).to_bytes(4, "big"))
 writer.write(msg_bytes)
 await writer.drain()
async def recv_json(reader) -> Optional[dict]:
 import json
 try:
 raw_len = await reader.readexactly(4)
 except asyncio.IncompleteReadError:
 return None
 data_len = int.from_bytes(raw_len, "big")
 if data_len == 0:
 return None
 data = await reader.readexactly(data_len)
 return json.loads(data.decode("utf-8"))