from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./ray_local.db'
    artifact_dir: str = './generated'
    supabase_url: str = ''
    supabase_publishable_key: str = ''
    ollama_base_url: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'qwen3-vl:4b-instruct-q4_K_M'
    ollama_timeout_seconds: float = 180.0

@lru_cache
def settings() -> Settings:
    return Settings()
