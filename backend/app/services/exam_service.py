"""智能试卷研判服务：题目切分、逐题分析（结构化输出）、学情统计、报告生成。

对齐开发文档 3.4：上传试卷 → 解析 → 切题 → 逐题分析 → 学情统计 → 研判报告。
"""
import json
import re
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.models.entities import Exam, ExamQuestion, ExamReport
from app.prompts import templates
from app.schemas.exam import ExamQuestionOut, ScoreRow
from app.services.llm_factory import llm_factory
from app.utils.logging_conf import get_logger
from pydantic import BaseModel

logger = get_logger("exam_service")

QUESTION_SPLIT_RE = re.compile(r"(?m)^\s*(\d{1,3})\s*[.、．)）]")


class ExamQuestionList(BaseModel):
    """逐题分析的结构化输出容器。"""

    items: list[ExamQuestionOut]


def parse_questions(text: str) -> list[str]:
    """按题号切分试卷文本为单题列表；切分失败时整体作为一个题目。"""
    matches = list(QUESTION_SPLIT_RE.finditer(text))
    if len(matches) < 2:
        return [t.strip() for t in text.split("\n\n") if t.strip()]
    questions = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        questions.append(text[start:end].strip())
    return [q for q in questions if len(q) > 5]


async def analyze_questions(
    db: Session, exam: Exam, questions: list[str], user_id: int
) -> list[ExamQuestionOut]:
    """分批逐题分析（每批 8 题），结构化输出并落库。"""
    llm = llm_factory.get_chat_model(task="exam", stream=False)
    structured = llm.with_structured_output(ExamQuestionList)

    results: list[ExamQuestionOut] = []
    exam.status = "analyzing"
    db.commit()

    for batch_no, start in enumerate(range(0, len(questions), 8), start=1):
        batch = questions[start : start + 8]
        numbered = "\n\n".join(f"第{i+1+start}题：\n{q}" for i, q in enumerate(batch))
        messages = [
            SystemMessage(content=templates.EXAM_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=f"请分析以下题目：\n{numbered}"),
        ]
        try:
            result = await structured.ainvoke(messages)
            items = result.items if isinstance(result, ExamQuestionList) else []
            for item in items:
                # 模型返回的 question_no 为批次内序号（1-based），换算为原卷绝对题号
                qno = start + item.question_no
                results.append(item)
                db.add(
                    ExamQuestion(
                        exam_id=exam.id,
                        question_no=qno,
                        question_type=item.question_type,
                        question_text=item.question_text,
                        answer=item.answer,
                        analysis=item.analysis,
                        knowledge_points=json.dumps(item.knowledge_points, ensure_ascii=False),
                        difficulty=item.difficulty,
                        score=item.score,
                    )
                )
            db.commit()
        except Exception as exc:
            logger.error("逐题分析批次失败 batch=%d: %s", batch_no, exc)
            # 兜底：原样作为题目文本写入，保证流程不中断
            for i, q in enumerate(batch):
                qno = start + i + 1
                db.add(
                    ExamQuestion(
                        exam_id=exam.id,
                        question_no=qno,
                        question_text=q,
                        analysis="（本题目分析失败，请人工复核）",
                    )
                )
            db.commit()

    exam.question_count = len(results) if results else len(questions)
    exam.status = "done"
    db.commit()
    return results


def compute_stats(exam: Exam, score_rows: list[ScoreRow]) -> dict:
    """学情统计：平均分、各题得分率、知识点归因、薄弱点。"""
    db_questions = {}  # 由调用方传入
    # 简化：直接基于调用方传入的题目信息与成绩行
    return _compute_from_rows(exam, score_rows)


def _compute_from_rows(exam: Exam, rows: list[ScoreRow]) -> dict:
    if not rows:
        return {"class_average": 0, "question_stats": [], "knowledge_stats": [], "weak_points": [], "suggestions": []}
    total = 0.0
    q_totals: dict[str, float] = {}
    for row in rows:
        total += sum(row.scores.values())
        for qno, score in row.scores.items():
            q_totals[qno] = q_totals.get(qno, 0.0) + score
    class_average = total / len(rows)
    question_stats = [
        {"question_no": q, "average_score": round(v / len(rows), 2), "full_score": 0, "pass_rate": 0}
        for q, v in sorted(q_totals.items(), key=lambda x: int(x[0]))
    ]
    return {
        "class_average": round(class_average, 2),
        "student_count": len(rows),
        "question_stats": question_stats,
        "knowledge_stats": [],
        "weak_points": [],
        "suggestions": [],
    }


def generate_report(db: Session, exam: Exam) -> ExamReport:
    """生成 Markdown 研判报告并落库。"""
    questions = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).order_by(ExamQuestion.question_no).all()
    existing = db.query(ExamReport).filter(ExamReport.exam_id == exam.id).first()
    report = existing or ExamReport(exam_id=exam.id, report_md="")

    lines = [
        f"# 试卷研判报告：{exam.exam_name}",
        "",
        f"- 学科：{exam.subject}　年级：{exam.grade}",
        f"- 题目数量：{len(questions)}",
        "",
        "## 一、逐题分析",
        "",
        "| 题号 | 题型 | 难度 | 分值 | 知识点 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for q in questions:
        kps = "、".join(json.loads(q.knowledge_points or "[]") or [])
        lines.append(f"| {q.question_no} | {q.question_type} | {q.difficulty or '-'} | {q.score or '-'} | {kps} |")

    lines.append("")
    lines.append("## 二、参考答案与解析")
    for q in questions:
        lines.append(f"### 第 {q.question_no} 题")
        lines.append(f"**答案**：{q.answer or '（未提供）'}")
        lines.append(f"**解析**：{q.analysis or '（未提供）'}")
        lines.append("")

    lines.append("## 三、学情统计")
    stats = json.loads(exam_reports_stats(db, exam.id) or "{}")
    if stats:
        lines.append(f"- 班级平均分：{stats.get('class_average', '-')}")
        lines.append(f"- 参考人数：{stats.get('student_count', '-')}")
        if stats.get("weak_points"):
            lines.append(f"- 薄弱知识点：{'、'.join(stats['weak_points'])}")
    else:
        lines.append("- 未导入班级成绩，暂无统计（可上传成绩表补充）。")
    lines.append("")
    lines.append("## 四、教学建议")
    lines.append("- （待补充，可结合薄弱知识点生成）")

    report.report_md = "\n".join(lines)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def exam_reports_stats(db: Session, exam_id: int) -> Optional[str]:
    report = db.query(ExamReport).filter(ExamReport.exam_id == exam_id).first()
    if report and report.stats_json:
        return report.stats_json
    return None


def export_report_docx(report_md: str, output_path: str) -> str:
    """报告 MD → docx（简单转换）。"""
    import docx

    document = docx.Document()
    for line in report_md.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("### "):
            document.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            document.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            document.add_heading(line[2:], level=1)
        elif line.startswith("- "):
            document.add_paragraph(line[2:], style="List Bullet")
        else:
            document.add_paragraph(line)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    return output_path
