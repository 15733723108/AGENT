"""教案模块 Schema（结构化输出 + 请求/响应）。"""
from typing import Optional

from pydantic import BaseModel, Field


class LessonPlanRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=32, description="学科，如 语文")
    grade: str = Field(..., min_length=1, max_length=32, description="年级，如 三年级")
    topic: str = Field(..., min_length=1, max_length=200, description="课题")
    class_hours: int = Field(1, ge=1, le=10, description="课时")
    course_type: str = Field("", max_length=32, description="课型，如 新授课")
    student_profile: str = Field("", max_length=500, description="学情简述（可选）")
    use_textbook_rag: bool = Field(True, description="是否注入教材参考片段")
    base_json: Optional[dict] = Field(None, description="基于上次结果修改时传入上次的 content_json")


class TeachingStep(BaseModel):
    stage: str = Field(..., description="教学环节名，如 导入")
    duration_minutes: int = Field(..., ge=1, le=45)
    content: str = Field(..., description="环节内容")


class LessonPlanContent(BaseModel):
    """教案结构化内容（LLM with_structured_output 的目标 schema）。"""

    title: str
    subject: str
    grade: str
    class_hours: int = 1
    course_type: str = ""
    teaching_objectives: dict = Field(..., description="键: 知识与技能/过程与方法/情感态度与价值观")
    key_points: list[str]
    difficult_points: list[str]
    teaching_prep: list[str] = []
    teaching_process: list[TeachingStep]
    board_design: str = ""
    homework: dict = Field(..., description="键: 基础作业/提高作业/拓展作业")
    reflection: str = ""


class LessonPlanOut(BaseModel):
    id: int
    subject: str
    grade: str
    topic: str
    class_hours: int
    course_type: str
    content_json: dict
    created_at: Optional[str] = None
