# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, SecretStr
from dotenv import load_dotenv
import os

load_dotenv()
class Settings(BaseSettings):
    PROJECT_NAME: str = "API Triggered Crawler"
    VERSION: str = "1.0.0"
    DATABASE_URL: str 
    DB_SCHEMA: str 
    OPENAI_API_KEY: SecretStr
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    CRM_API_URL: str
    CRM_API_KEY: SecretStr
    CRAWLER_A_URL: str
    CRAWLER_B_URL: str
    CRAWLER_C_URL: str  
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "./logs/app.log"
    LOG_ROTATION: str = "10MB"  # 新增日志轮转配置
    AF_GOOGLE_MAPS_API_KEY: str
    AF_FUID: str
    AF_BASE_URL: str
    AF_GOOGLE_BASE_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()