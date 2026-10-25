"""试卷研判模块 Schema。"""
from typing import Optional

from pydantic import BaseModel, Field


class ExamCreateRequest(BaseModel):
    exam_name: str = Field(..., min_length=1, max_length=200)
    subject: str = Field(..., min_length=1, max_length=32)
    grade: str = Field(..., min_length=1, max_length=32)


class ExamQuestionOut(BaseModel):
    question_no: int
    question_type: str = ""
    question_text: str
    answer: str = ""
    analysis: str = ""
    knowledge_points: list[str] = []
    difficulty: int = Field(3, ge=1, le=5)
    score: float = 0.0


class ExamOut(BaseModel):
    id: int
    exam_name: str
    subject: str
    grade: str
    source_file: str = ""
    question_count: int = 0
    status: str
    error_msg: Optional[str] = None
    created_at: Optional[str] = None


class ExamReportOut(BaseModel):
    exam_id: int
    report_md: str
    stats_json: Optional[dict] = None
    report_file: str = ""
    created_at: Optional[str] = None


class ScoreRow(BaseModel):
    """成绩表一行：学生 + 各题得分。"""

    student_name: str
    scores: dict[str, float] = Field(..., description="键为题号字符串，如 '1': 8.0")
