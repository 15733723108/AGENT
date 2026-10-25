"""智能试卷研判路由：上传/创建、逐题分析、学情统计、研判报告导出。"""
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.entities import Exam, ExamQuestion, ExamReport, User
from app.routers.deps import require_role
from app.schemas.exam import (
    ExamCreateRequest,
    ExamOut,
    ExamQuestionOut,
    ExamReportOut,
    ScoreRow,
)
from app.services.doc_parser import parse_file
from app.services.exam_service import (
    analyze_questions,
    compute_stats,
    exam_reports_stats,
    export_report_docx,
    generate_report,
    parse_questions,
)
from app.utils.logging_conf import get_logger

router = APIRouter()
logger = get_logger("exam")

ALLOWED_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md", ".png", ".jpg", ".jpeg"}


def _exam_out(e: Exam) -> ExamOut:
    return ExamOut(
        id=e.id,
        exam_name=e.exam_name,
        subject=e.subject,
        grade=e.grade,
        source_file=e.source_file or "",
        question_count=e.question_count or 0,
        status=e.status,
        error_msg=e.error_msg,
        created_at=str(e.created_at) if e.created_at else None,
    )


def _question_out(q: ExamQuestion) -> ExamQuestionOut:
    return ExamQuestionOut(
        question_no=q.question_no,
        question_type=q.question_type or "",
        question_text=q.question_text,
        answer=q.answer or "",
        analysis=q.analysis or "",
        knowledge_points=q.knowledge_points or [],
        difficulty=q.difficulty or 3,
        score=float(q.score) if q.score is not None else 0.0,
    )


def _create_exam_from_text(db: Session, teacher_id: int, req: ExamCreateRequest, text: str, source_file: str = "") -> Exam:
    questions = parse_questions(text)
    exam = Exam(
        teacher_id=teacher_id,
        exam_name=req.exam_name,
        subject=req.subject,
        grade=req.grade,
        source_file=source_file,
        question_count=len(questions),
        status="pending",
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    for i, q_text in enumerate(questions, start=1):
        db.add(ExamQuestion(exam_id=exam.id, question_no=i, question_text=q_text))
    db.commit()
    logger.info("试卷已创建: %s (id=%s, %d 题)", exam.exam_name, exam.id, len(questions))
    return exam


@router.post("/create", response_model=ExamOut, summary="手动创建试卷（粘贴文本）")
def create_exam(
    req: ExamCreateRequest,
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    if not req.exam_name.strip():
        raise HTTPException(status_code=400, detail="试卷名称不能为空")
    # 简化：手动创建时题目文本由后续 update 接口补充；此处创建空试卷
    exam = Exam(
        teacher_id=user.id,
        exam_name=req.exam_name,
        subject=req.subject,
        grade=req.grade,
        question_count=0,
        status="pending",
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _exam_out(exam)


@router.post("/create/with-text", response_model=ExamOut, summary="粘贴试卷全文创建并切题")
def create_exam_with_text(
    exam_name: str = Form(..., min_length=1, max_length=200, description="试卷名称"),
    subject: str = Form("未分类", max_length=32, description="学科"),
    grade: str = Form("未知", max_length=32, description="年级"),
    paper_text: str = Form(..., min_length=10, description="试卷全文"),
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    req = ExamCreateRequest(exam_name=exam_name, subject=subject, grade=grade)
    exam = _create_exam_from_text(db, user.id, req, paper_text)
    return _exam_out(exam)


@router.post("/upload", response_model=ExamOut, summary="上传试卷文件（自动解析切题）")
async def upload_exam(
    file: UploadFile = File(...),
    exam_name: str = Form("", description="试卷名称，留空则取文件名"),
    subject: str = Form("", description="学科"),
    grade: str = Form("", description="年级"),
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}，支持 {sorted(ALLOWED_EXTS)}")

    upload_dir = Path(settings.OUTPUT_DIR) / "uploads" / "exams"
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{user.id}_{int(__import__('time').time())}{ext}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    text = parse_file(str(dest))
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件解析失败或内容为空（扫描件需安装 rapidocr_onnxruntime）")

    name = exam_name or Path(file.filename or "试卷").stem
    req = ExamCreateRequest(exam_name=name, subject=subject or "未分类", grade=grade or "未知")
    exam = _create_exam_from_text(db, user.id, req, text, source_file=str(dest))
    return _exam_out(exam)


@router.get("/list", summary="试卷列表")
def list_exams(
    subject: str = "",
    status: str = "",
    limit: int = 50,
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    q = db.query(Exam).filter(Exam.teacher_id == user.id).order_by(Exam.id.desc())
    if subject:
        q = q.filter(Exam.subject == subject)
    if status:
        q = q.filter(Exam.status == status)
    exams = q.limit(min(limit, 200)).all()
    return [_exam_out(e) for e in exams]


@router.get("/{exam_id}", summary="试卷详情（含逐题明细）")
def exam_detail(exam_id: int, user: User = Depends(require_role("admin", "teacher")), db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.teacher_id == user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    questions = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.question_no).all()
    return {"exam": _exam_out(exam), "questions": [_question_out(q) for q in questions]}


@router.post("/{exam_id}/analyze", response_model=ExamOut, summary="触发逐题智能分析")
async def analyze(
    exam_id: int,
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.teacher_id == user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    questions = [q.question_text for q in db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.question_no)]
    if not questions:
        raise HTTPException(status_code=400, detail="试卷暂无题目，请先上传/粘贴试卷文本")
    try:
        await analyze_questions(db, exam, questions, user.id)
    except Exception as exc:
        exam.status = "failed"
        exam.error_msg = str(exc)[:500]
        db.commit()
        logger.error("试卷分析失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"分析失败：{exc}")
    return _exam_out(exam)


@router.post("/{exam_id}/stats", summary="学情统计（成绩表 → 统计/薄弱点）")
def stats(
    exam_id: int,
    rows: list[ScoreRow],
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.teacher_id == user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    return compute_stats(exam, rows)


@router.get("/{exam_id}/report", response_model=ExamReportOut, summary="研判报告")
def report(exam_id: int, user: User = Depends(require_role("admin", "teacher")), db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.teacher_id == user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    rep = generate_report(db, exam)
    return ExamReportOut(
        exam_id=exam.id,
        report_md=rep.report_md,
        stats_json=rep.stats_json,
        report_file=rep.report_file or "",
        created_at=str(rep.created_at) if rep.created_at else None,
    )


@router.get("/{exam_id}/report/export", summary="导出研判报告（docx）")
def export_report(
    exam_id: int,
    user: User = Depends(require_role("admin", "teacher")),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.teacher_id == user.id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    rep = generate_report(db, exam)
    out_dir = Path(settings.OUTPUT_DIR) / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"exam_report_{exam.id}.docx"
    export_report_docx(rep.report_md, str(path))
    return FileResponse(
        str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=path.name,
    )
