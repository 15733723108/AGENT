"""知识库管理路由：文档列表、上传入库、废弃文档、电子书/试卷查阅。"""
import mimetypes
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.entities import KbDocument, User
from app.routers.deps import get_current_user, require_role
from app.schemas.kb import (
    DeactivateRequest,
    DeactivateResult,
    KbDocumentContent,
    KbDocumentOut,
    TextImportRequest,
    UploadResult,
)
from app.services.doc_parser import SUPPORTED_EXTENSIONS, parse_file
from app.utils.logging_conf import get_logger

router = APIRouter()
logger = get_logger("kb")


def _doc_out(d: KbDocument) -> KbDocumentOut:
    return KbDocumentOut(
        id=d.id,
        doc_name=d.doc_name,
        category=d.category,
        file_type=d.file_type,
        file_path=d.file_path or "",
        chunk_count=d.chunk_count or 0,
        is_active=d.is_active,
        created_at=str(d.created_at) if d.created_at else None,
    )


@router.get("/documents", summary="知识库文档列表")
def list_documents(
    category: str = "",
    active_only: bool = True,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(KbDocument)
    if category:
        q = q.filter(KbDocument.category == category)
    if active_only:
        q = q.filter(KbDocument.is_active == 1)
    docs = q.order_by(KbDocument.id.desc()).limit(min(limit, 500)).all()
    return [_doc_out(d) for d in docs]


@router.get("/documents/{doc_id}/content", response_model=KbDocumentContent, summary="读取文档文本内容（在线查阅）")
def document_content(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(KbDocument).filter(KbDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    content = ""
    path = Path(doc.file_path) if doc.file_path else None
    if path and path.exists():
        try:
            content = parse_file(str(path))
        except Exception as exc:
            logger.warning("文档内容解析失败 doc_id=%s: %s", doc.id, exc)
            content = ""
    return KbDocumentContent(
        doc_id=doc.id,
        doc_name=doc.doc_name,
        category=doc.category,
        file_type=doc.file_type,
        content=content,
    )


@router.get("/documents/{doc_id}/download", summary="下载/查看原始文件")
def document_download(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(KbDocument).filter(KbDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    path = Path(doc.file_path) if doc.file_path else None
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="源文件不存在")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(str(path), media_type=media_type, filename=doc.doc_name or path.name)


@router.post("/library/upload", response_model=UploadResult, summary="直接存储资源文件（不解析、不向量化）")
async def library_upload(
    file: UploadFile = File(...),
    name: str = Form(..., min_length=1, max_length=255, description="资源名称"),
    category: str = Form("教材", description="分类：教材/试卷"),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}，支持 {sorted(SUPPORTED_EXTENSIONS)}")

    kb_dir = Path(settings.OUTPUT_DIR) / "kb" / (category if category else "教材")
    kb_dir.mkdir(parents=True, exist_ok=True)
    dest = kb_dir / f"{int(time.time())}_{Path(file.filename or 'resource').name}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = KbDocument(
        doc_name=name.strip(),
        category=category,
        file_type=ext.lstrip(".").lower() or "img",
        file_path=str(dest),
        version=1,
        is_active=1,
        chunk_count=0,
        uploader_id=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info("资源已存储: %s -> doc_id=%s (category=%s)", name, doc.id, category)
    return UploadResult(doc_id=doc.id, doc_name=doc.doc_name, chunk_count=0)


@router.post("/upload", response_model=UploadResult, summary="上传文档并入库（解析/分块/向量化）")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("auto", description="知识域，auto 则按目录名推断"),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}，支持 {sorted(SUPPORTED_EXTENSIONS)}")

    kb_dir = Path(settings.OUTPUT_DIR) / "kb" / (category if category != "auto" else "general")
    kb_dir.mkdir(parents=True, exist_ok=True)
    dest = kb_dir / f"{int(time.time())}_{Path(file.filename or 'doc').name}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    from app.knowledge.ingest import ingest_file

    doc_id = ingest_file(str(dest), category=category, uploader_id=user.id)
    if not doc_id:
        raise HTTPException(status_code=400, detail="文档解析为空，入库失败")
    doc = db.query(KbDocument).filter(KbDocument.id == doc_id).first()
    logger.info("知识库上传入库: %s -> doc_id=%s", dest.name, doc_id)
    return UploadResult(doc_id=doc_id, doc_name=doc.doc_name, chunk_count=doc.chunk_count or 0)


@router.post("/import-text", response_model=UploadResult, summary="粘贴文本入库（解析/分块/向量化）")
def import_text(
    req: TextImportRequest,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from app.knowledge.ingest import ingest_text

    title = req.title.strip() or f"粘贴文本_{int(time.time())}"
    doc_id = ingest_text(title=title, category=req.category, text=req.content, uploader_id=user.id)
    if not doc_id:
        raise HTTPException(status_code=400, detail="文本内容为空，入库失败")
    doc = db.query(KbDocument).filter(KbDocument.id == doc_id).first()
    logger.info("粘贴文本入库: %s -> doc_id=%s", title, doc_id)
    return UploadResult(doc_id=doc_id, doc_name=doc.doc_name, chunk_count=doc.chunk_count or 0)


@router.post("/deactivate", response_model=DeactivateResult, summary="废弃文档（不再参与检索）")
def deactivate(
    req: DeactivateRequest,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from app.knowledge.ingest import deactivate_document

    doc = db.query(KbDocument).filter(KbDocument.id == req.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    deactivate_document(req.doc_id)
    return DeactivateResult(doc_id=req.doc_id)
