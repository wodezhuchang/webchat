from pydantic_settings import BaseSettings
import json
import os
class Settings(BaseSettings):
 SERVER_HOST: str = "0.0.0.0"
 SERVER_PORT: int = 8000
 API_URL: str = "https://api.deepseek.com/v1/chat/completions"
 API_KEY: str = ""
 API_TIMEOUT: int = 30
 HEARTBEAT_INTERVAL: int = 30
 HEARTBEAT_TIMEOUT: int = 60
 class Config:
 env_file = ".env"
def load_config_from_json():
 config_path = os.path.join(os.path.dirname(__file__), "config", "server_config.json")
 if os.path.exists(config_path):
 with open(config_path, "r", encoding="utf-8") as f:
 return json.load(f)
 return {}
json_config = load_config_from_json()
settings = Settings(
 SERVER_HOST=json_config.get("server", {}).get("host", "0.0.0.0"),
 SERVER_PORT=json_config.get("server", {}).get("port", 8000),
 API_URL=json_config.get("deepseek", {}).get("api_url", "https://api.deepseek.com/v1/chat/completions"),
 API_KEY=json_config.get("deepseek", {}).get("api_key", ""),
 API_TIMEOUT=json_config.get("deepseek", {}).get("timeout", 30),
 HEARTBEAT_INTERVAL=json_config.get("heartbeat", {}).get("interval", 30),
 HEARTBEAT_TIMEOUT=json_config.get("heartbeat", {}).get("timeout", 60),
)