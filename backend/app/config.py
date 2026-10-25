"""全局配置：pydantic-settings 从 .env 加载，字段与 .env.example 对齐。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 运行模式
    APP_ENV: str = "development"
    # LLM 模式：api=云端OpenAI兼容API  local=本地vLLM
    LLM_MODE: str = "api"

    # LLM（API 模式）
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_MODEL_STRONG: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.3
    # 降级通道
    FALLBACK_LLM_BASE_URL: str = ""
    FALLBACK_LLM_API_KEY: str = ""
    FALLBACK_LLM_MODEL: str = ""

    # LLM（本地 vLLM 模式）
    VLLM_BASE_URL: str = "http://127.0.0.1:8000/v1"
    VLLM_API_KEY: str = "EMPTY"
    VLLM_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"

    # Embedding / Rerank
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_API_BASE: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_DIM: int = 1024
    RERANK_MODEL: str = "BAAI/bge-reranker-base"

    # 向量库（milvus | pgvector | memory）
    VECTOR_BACKEND: str = "memory"
    MILVUS_HOST: str = "127.0.0.1"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "school_kb_v1"
    PGVECTOR_CONNECTION_STRING: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/school_agent"

    # MySQL
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "school_agent"
    MYSQL_USER: str = "school_app"
    MYSQL_PASSWORD: str = "school_app_123456"
    # 完整数据库连接串；设置后优先于 MYSQL_* 逐项配置。
    # 示例：mysql+pymysql://user:pwd@127.0.0.1:3306/school_agent?charset=utf8mb4
    DATABASE_URL: str = ""

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin123"
    MINIO_BUCKET: str = "school-agent"

    # 安全
    JWT_SECRET: str = "change-me-to-a-long-random-string-at-least-32-chars"
    JWT_EXPIRE_MINUTES: int = 1440

    # 服务
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    # 跨域白名单（逗号分隔；同源部署时可为空）
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    # 产出目录（导出文件、上传文件落盘根目录）
    OUTPUT_DIR: str = "./data"

    # RAG 参数
    RAG_TOP_K: int = 20
    RAG_SCORE_THRESHOLD: float = 0.35
    RAG_FINAL_K: int = 5
    RAG_CHUNK_SIZE: int = 600
    RAG_CHUNK_OVERLAP: int = 80

    # 会话记忆窗口（轮）
    CHAT_MEMORY_WINDOW: int = 10

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
