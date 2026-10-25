"""通用问答 / 学校信息问答：会话与消息 Schema。"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    module: Literal["general", "school_info"] = "general"
    title: str = ""


class SessionOut(BaseModel):
    id: int
    module: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: int = Field(..., description="会话 ID")
    question: str = Field(..., min_length=1, max_length=4000, description="用户提问")
    stream: bool = True


class RefItem(BaseModel):
    index: int = Field(..., description="引用编号，对应回答中的 [N]")
    source: str = Field(..., description="来源文档名")
    doc_id: Optional[int] = None
    category: str = ""
    snippet: str = Field(default="", description="命中的原文片段（截断）")


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    refs: Optional[list[RefItem]] = None
    created_at: Optional[str] = None


class ChatHistoryOut(BaseModel):
    session: SessionOut
    messages: list[ChatMessageOut]
