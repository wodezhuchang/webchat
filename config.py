from pydantic_settings import BaseSettings, SettingsConfigDict
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
    DB_HOST: str = "localhost"
    DB_PORT: int = 3308
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "chat_system"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    JWT_SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


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