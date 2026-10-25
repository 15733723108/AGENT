"""SQLAlchemy ORM 模型：对齐开发文档第 4 章数据库设计（MySQL 8.0 / utf8mb4）。"""
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    DECIMAL,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT as _MEDIUMTEXT, TINYINT as _TINYINT

from app.database import Base

# SQLite 兼容：SQLite 无 TINYINT / MEDIUMTEXT，自动回退到 INTEGER / TEXT（MySQL 下保持原类型不变）
TINYINT = _TINYINT().with_variant(Integer, "sqlite")
MEDIUMTEXT = _MEDIUMTEXT().with_variant(Text, "sqlite")


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, comment="登录名")
    password_hash = Column(String(128), nullable=False, comment="密码哈希(bcrypt)")
    display_name = Column(String(64), nullable=False, comment="显示名")
    role = Column(Enum("admin", "teacher", "student", "parent"), nullable=False, default="student")
    phone = Column(String(20), nullable=True)
    status = Column(TINYINT, nullable=False, default=1, comment="1启用 0禁用")
    is_approved = Column(TINYINT, nullable=False, default=1, comment="1已审核通过 0待管理员审核")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ChatSession(Base):
    """会话表"""

    __tablename__ = "chat_sessions"
    __table_args__ = (Index("idx_user_module", "user_id", "module"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    module = Column(Enum("general", "school_info", "lesson_plan", "exam"), nullable=False, comment="所属模块")
    title = Column(String(200), default="", comment="会话标题(取首问截断)")
    status = Column(TINYINT, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    """消息表"""

    __tablename__ = "chat_messages"
    __table_args__ = (Index("idx_session", "session_id", "created_at"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, nullable=False)
    role = Column(Enum("user", "assistant"), nullable=False)
    content = Column(MEDIUMTEXT, nullable=False, comment="消息正文")
    refs = Column(JSON, nullable=True, comment="引用来源列表(学校信息问答)")
    token_count = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class KbDocument(Base):
    """知识库文档表"""

    __tablename__ = "kb_documents"
    __table_args__ = (Index("idx_category_active", "category", "is_active"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    doc_name = Column(String(255), nullable=False, comment="文档名")
    category = Column(String(50), nullable=False, comment="知识域:招生/作息/制度/通知/教材/试卷等")
    file_type = Column(String(20), nullable=False, comment="pdf/docx/xlsx/png...")
    file_path = Column(String(500), nullable=False, comment="对象存储路径")
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(TINYINT, nullable=False, default=1, comment="1有效(参与检索) 0废弃")
    chunk_count = Column(Integer, default=0)
    uploader_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class KbChunk(Base):
    """知识库文本块表"""

    __tablename__ = "kb_chunks"
    __table_args__ = (Index("idx_doc", "doc_id", "chunk_index"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    doc_id = Column(BigInteger, nullable=False)
    chunk_index = Column(Integer, nullable=False, comment="块序号")
    content = Column(MEDIUMTEXT, nullable=False, comment="文本块")
    chunk_metadata = Column("metadata", JSON, nullable=True, comment="章节/页码等元数据")
    vector_id = Column(String(64), nullable=True, comment="向量库主键")
    is_active = Column(TINYINT, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class LessonPlan(Base):
    """教案记录表"""

    __tablename__ = "lesson_plans"
    __table_args__ = (Index("idx_teacher", "teacher_id", "created_at"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    teacher_id = Column(BigInteger, nullable=False)
    subject = Column(String(32), nullable=False, comment="学科")
    grade = Column(String(32), nullable=False, comment="年级")
    topic = Column(String(200), nullable=False, comment="课题")
    class_hours = Column(TINYINT, nullable=False, default=1, comment="课时")
    course_type = Column(String(32), default="", comment="课型")
    content_json = Column(JSON, nullable=False, comment="教案结构化内容")
    status = Column(Enum("draft", "done"), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Exam(Base):
    """试卷表"""

    __tablename__ = "exams"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    teacher_id = Column(BigInteger, nullable=False)
    exam_name = Column(String(200), nullable=False, comment="试卷名称")
    subject = Column(String(32), nullable=False)
    grade = Column(String(32), nullable=False)
    source_file = Column(String(500), default="", comment="原卷文件路径")
    question_count = Column(Integer, default=0)
    status = Column(
        Enum("pending", "parsing", "analyzing", "done", "failed"),
        nullable=False,
        default="pending",
    )
    error_msg = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ExamQuestion(Base):
    """题目分析表"""

    __tablename__ = "exam_questions"
    __table_args__ = (UniqueConstraint("exam_id", "question_no", name="uk_exam_no"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    exam_id = Column(BigInteger, nullable=False)
    question_no = Column(Integer, nullable=False)
    question_type = Column(String(32), default="")
    question_text = Column(MEDIUMTEXT, nullable=False)
    answer = Column(MEDIUMTEXT, nullable=True)
    analysis = Column(MEDIUMTEXT, nullable=True)
    knowledge_points = Column(JSON, nullable=True, comment="知识点标签数组")
    difficulty = Column(TINYINT, nullable=True, comment="1-5")
    score = Column(DECIMAL(5, 1), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class ExamReport(Base):
    """试卷研判报告表"""

    __tablename__ = "exam_reports"
    __table_args__ = (Index("idx_exam", "exam_id"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    exam_id = Column(BigInteger, nullable=False)
    report_md = Column(MEDIUMTEXT, nullable=False, comment="报告正文Markdown")
    stats_json = Column(JSON, nullable=True, comment="学情统计(得分率/知识点归因)")
    report_file = Column(String(500), default="", comment="导出文件路径")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class LlmUsage(Base):
    """LLM 调用用量表"""

    __tablename__ = "llm_usage"
    __table_args__ = (Index("idx_created", "created_at"),)

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True)
    module = Column(String(32), nullable=False)
    model_name = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost = Column(DECIMAL(10, 4), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


def to_dict(obj, exclude: set | None = None) -> dict:
    """ORM 对象转 dict（用于 API 响应）。"""
    exclude = exclude or {"password_hash"}
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in exclude}
