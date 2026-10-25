"""沧州市劝学路小学智能体 - 后端服务入口。

FastAPI 应用装配：日志、CORS、路由注册、健康检查。
启动方式：
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, chat, exam, kb, lesson, school_info
from app.utils.logging_conf import get_logger, setup_logging

setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("沧州市劝学路小学智能体启动 (env=%s, llm=%s, vector=%s)", settings.APP_ENV, settings.LLM_MODE, settings.VECTOR_BACKEND)
    yield
    logger.info("服务已退出")


app = FastAPI(
    title="沧州市劝学路小学智能体 API",
    description="基于 LangChain 的教育智能体：通用问答 / 教案一键生成 / 学校信息问答 / 智能试卷研判",
    version="1.0.0",
    lifespan=lifespan,
)

# 跨域：前端 Vite 开发服务器与 Nginx 同源部署均可访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 业务路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/chat", tags=["通用问答"])
app.include_router(school_info.router, prefix="/api/school_info", tags=["学校信息问答"])
app.include_router(lesson.router, prefix="/api/lesson", tags=["教案一键生成"])
app.include_router(exam.router, prefix="/api/exam", tags=["智能试卷研判"])
app.include_router(kb.router, prefix="/api/kb", tags=["知识库管理"])


@app.get("/api/health", tags=["系统"])
def health_check():
    """健康检查：供 Docker / Nginx / 运维探活使用。"""
    return {
        "status": "ok",
        "app": "czqxl-agent",
        "llm_mode": settings.LLM_MODE,
        "vector_backend": settings.VECTOR_BACKEND,
    }
