"""教案一键生成路由：生成 / 列表 / 详情 / 导出。"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.entities import LessonPlan, User
from app.routers.deps import require_role
from app.schemas.lesson import LessonPlanOut, LessonPlanRequest
from app.services.lesson_service import export_docx, export_markdown, generate_lesson_plan
from app.utils.logging_conf import get_logger

router = APIRouter()
logger = get_logger("lesson")


def _plan_out(p: LessonPlan) -> LessonPlanOut:
    return LessonPlanOut(
        id=p.id,
        subject=p.subject,
        grade=p.grade,
        topic=p.topic,
        class_hours=p.class_hours,
        course_type=p.course_type or "",
        content_json=p.content_json,
        created_at=str(p.created_at) if p.created_at else None,
    )


@router.post("/generate", response_model=LessonPlanOut, summary="一键生成教案")
async def generate(
    req: LessonPlanRequest,
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    plan = await generate_lesson_plan(db, user.id, req)
    return _plan_out(plan)


@router.get("/plans", summary="教案列表")
def list_plans(
    subject: Optional[str] = "",
    limit: int = 50,
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    q = db.query(LessonPlan).filter(LessonPlan.teacher_id == user.id).order_by(LessonPlan.id.desc())
    if subject:
        q = q.filter(LessonPlan.subject == subject)
    plans = q.limit(min(limit, 200)).all()
    return [_plan_out(p) for p in plans]


@router.get("/plans/{plan_id}", response_model=LessonPlanOut, summary="教案详情")
def detail(plan_id: int, user: User = Depends(require_role("admin", "teacher")), db: Session = Depends(get_db)):
    plan = db.query(LessonPlan).filter(LessonPlan.id == plan_id, LessonPlan.teacher_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="教案不存在")
    return _plan_out(plan)


@router.get("/plans/{plan_id}/export", summary="导出教案（md / docx）")
def export(
    plan_id: int,
    fmt: str = "md",
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    plan = db.query(LessonPlan).filter(LessonPlan.id == plan_id, LessonPlan.teacher_id == user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="教案不存在")

    out_dir = Path(settings.OUTPUT_DIR) / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "md":
        content = export_markdown(plan)
        path = out_dir / f"lesson_plan_{plan.id}.md"
        path.write_text(content, encoding="utf-8")
        media = "text/markdown; charset=utf-8"
    elif fmt == "docx":
        path = out_dir / f"lesson_plan_{plan.id}.docx"
        export_docx(plan, str(path))
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="仅支持 md / docx")
    return FileResponse(str(path), media_type=media, filename=path.name)
