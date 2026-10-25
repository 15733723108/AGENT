"""教案一键生成服务：结构化输出、字段校验、保存、导出 md/docx。"""
import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.models.entities import LessonPlan
from app.prompts import templates
from app.schemas.lesson import LessonPlanContent, LessonPlanRequest
from app.services.llm_factory import llm_factory
from app.services.rag_pipeline import rag_pipeline
from app.utils.logging_conf import get_logger

logger = get_logger("lesson_service")

DEFAULT_PERIOD_MINUTES = 40


def _build_user_prompt(req: LessonPlanRequest, context: str = "") -> str:
    lines = [
        f"学科：{req.subject}",
        f"年级：{req.grade}",
        f"课题：{req.topic}",
        f"课时：第 {req.class_hours} 课时",
        f"课型：{req.course_type or '新授课'}",
    ]
    if req.student_profile:
        lines.append(f"学情简述：{req.student_profile}")
    if context:
        lines.append(f"教材参考片段：\n{context}")
    if req.base_json:
        lines.append(f"（请在以下上次教案基础上修改完善，保持 JSON 结构）\n上次教案：{json.dumps(req.base_json, ensure_ascii=False)}")
    return "\n".join(lines)


def _validate(content: LessonPlanContent) -> str | None:
    """字段完整性 / 时长校验，返回错误信息或 None。"""
    if not content.title or not content.key_points or not content.teaching_process:
        return "教案结构不完整（缺少标题/重点/教学过程），请重试"
    total = sum(s.duration_minutes for s in content.teaching_process)
    if abs(total - DEFAULT_PERIOD_MINUTES) > 10:
        return f"教学环节时长合计 {total} 分钟，与单课时 {DEFAULT_PERIOD_MINUTES} 分钟偏差过大，请重试"
    return None


def _extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON（容忍 Markdown 代码块等包裹）。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


async def generate_lesson_plan(db: Session, user_id: int, req: LessonPlanRequest) -> LessonPlan:
    llm = llm_factory.get_chat_model(task="lesson_plan", stream=False)
    # DeepSeek 不支持 json_schema 结构化输出，改用其支持的 json_object 模式 + 手动解析校验
    json_llm = llm.bind(response_format={"type": "json_object"})

    context = ""
    if req.use_textbook_rag:
        try:
            hits = rag_pipeline.search(req.topic, category="教材")
            if hits:
                context = rag_pipeline.format_context(hits)
        except Exception as exc:
            logger.warning("教案教材检索失败（忽略）: %s", exc)

    messages = [
        SystemMessage(content=templates.LESSON_PLAN_SYSTEM_PROMPT),
        HumanMessage(content=_build_user_prompt(req, context)),
    ]

    # 失败重试一次（对齐文档 3.2.2）
    content: LessonPlanContent | None = None
    for attempt in range(2):
        try:
            raw = await json_llm.ainvoke(messages)
            text = raw.content if isinstance(raw.content, str) else str(raw.content)
            data = json.loads(_extract_json(text))
            if not isinstance(data, dict):
                raise ValueError("教案 JSON 不是对象")
            # 用请求参数兜底补全元信息（不依赖 LLM 是否写出）
            data.setdefault("title", req.topic)
            data.setdefault("subject", req.subject)
            data.setdefault("grade", req.grade)
            data.setdefault("class_hours", req.class_hours)
            data.setdefault("course_type", req.course_type or "新授课")
            candidate = LessonPlanContent.model_validate(data)
            err = _validate(candidate)
            if err:
                logger.warning("教案校验失败 attempt=%d: %s", attempt + 1, err)
                continue
            content = candidate
            break
        except Exception as exc:
            logger.warning("教案生成异常 attempt=%d: %s", attempt + 1, exc)
    if content is None:
        raise RuntimeError("教案生成失败，请调整输入后重试")

    content_json = content.model_dump()
    plan = LessonPlan(
        teacher_id=user_id,
        subject=req.subject,
        grade=req.grade,
        topic=req.topic,
        class_hours=req.class_hours,
        course_type=req.course_type,
        content_json=content_json,
        status="done",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def export_markdown(plan: LessonPlan) -> str:
    c = plan.content_json
    lines = [
        f"# {c.get('title', plan.topic)}",
        "",
        f"- 学科：{plan.subject}　年级：{plan.grade}　课时：{plan.class_hours}　课型：{c.get('course_type', plan.course_type) or '新授课'}",
        "",
        "## 一、教学目标",
    ]
    for k, v in (c.get("teaching_objectives") or {}).items():
        lines.append(f"- **{k}**：{v}")
    lines += ["", "## 二、教学重点", *[f"- {x}" for x in c.get("key_points", [])],
              "", "## 三、教学难点", *[f"- {x}" for x in c.get("difficult_points", [])]]
    if c.get("teaching_prep"):
        lines += ["", "## 四、教学准备", *[f"- {x}" for x in c["teaching_prep"]]]
    lines += ["", "## 五、教学过程"]
    for step in c.get("teaching_process", []):
        lines.append(f"### {step.get('stage')}（{step.get('duration_minutes')} 分钟）")
        lines.append(step.get("content", ""))
    if c.get("board_design"):
        lines += ["", "## 六、板书设计", c["board_design"]]
    lines += ["", "## 七、作业设计"]
    for k, v in (c.get("homework") or {}).items():
        lines.append(f"- **{k}**：{v}")
    if c.get("reflection"):
        lines += ["", "## 八、教学反思（预留）", c["reflection"]]
    return "\n".join(lines)


def export_docx(plan: LessonPlan, output_path: str) -> str:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    document = docx.Document()
    title = plan.content_json.get("title", plan.topic)
    document.add_heading(title, level=0)
    p = document.add_paragraph(f"学科：{plan.subject}　年级：{plan.grade}　课时：{plan.class_hours}　课型：{plan.course_type or '新授课'}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    document.add_heading("一、教学目标", level=1)
    for k, v in (plan.content_json.get("teaching_objectives") or {}).items():
        document.add_paragraph(f"{k}：{v}")
    document.add_heading("二、教学重点", level=1)
    for x in plan.content_json.get("key_points", []):
        document.add_paragraph(x, style="List Bullet")
    document.add_heading("三、教学难点", level=1)
    for x in plan.content_json.get("difficult_points", []):
        document.add_paragraph(x, style="List Bullet")
    document.add_heading("五、教学过程", level=1)
    for step in plan.content_json.get("teaching_process", []):
        document.add_heading(f"{step.get('stage')}（{step.get('duration_minutes')} 分钟）", level=2)
        document.add_paragraph(step.get("content", ""))
    document.add_heading("七、作业设计", level=1)
    for k, v in (plan.content_json.get("homework") or {}).items():
        document.add_paragraph(f"{k}：{v}")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    return output_path
