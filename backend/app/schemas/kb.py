"""知识库管理 Schema：文档列表 / 上传入库 / 废弃。"""
from typing import Optional

from pydantic import BaseModel, Field


class KbDocumentOut(BaseModel):
    id: int
    doc_name: str
    category: str
    file_type: str
    file_path: str = ""
    chunk_count: int = 0
    is_active: int = 1
    created_at: Optional[str] = None


class KbDocumentContent(BaseModel):
    """文档文本内容（用于电子书/试卷在线查阅）。"""

    doc_id: int
    doc_name: str
    category: str
    file_type: str
    content: str = ""


class TextImportRequest(BaseModel):
    """粘贴文本入库请求。"""

    title: str = Field(..., min_length=1, max_length=255, description="文档标题")
    category: str = Field("制度", max_length=50, description="知识域")
    content: str = Field(..., min_length=1, description="粘贴的知识库正文")


class UploadResult(BaseModel):
    doc_id: int
    doc_name: str
    chunk_count: int = 0
    message: str = "ok"


class DeactivateRequest(BaseModel):
    doc_id: int = Field(..., description="要废弃的文档 ID")


class DeactivateResult(BaseModel):
    doc_id: int
    message: str = "已废弃，文档不再参与检索"
