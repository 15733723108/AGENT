"""文档解析服务：PDF / Word / Excel / 文本 / 图片(OCR 可选)。

对齐开发文档 2.4 RAG 链路"文档解析"段。RapidOCR 为可选依赖，
未安装时图片解析返回空并提示安装 rapidocr_onnxruntime。
"""
from pathlib import Path

from app.utils.logging_conf import get_logger

logger = get_logger("doc_parser")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg"}


def parse_pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    parts = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        parts.append(f"--- 第 {i} 页 ---\n{text}")
    return "\n\n".join(parts)


def parse_docx(path: str) -> str:
    import docx

    document = docx.Document(path)
    lines = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines)


def parse_xlsx(path: str) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    lines = []
    for ws in wb.worksheets:
        lines.append(f"# Sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            values = ["" if v is None else str(v) for v in row]
            if any(values):
                lines.append(" | ".join(values))
    return "\n".join(lines)


def parse_image(path: str) -> str:
    """扫描件 OCR（RapidOCR 可选依赖）。"""
    try:
        from rapidocr_onnxruntime import RapidOCR

        engine = RapidOCR()
        result, _ = engine(str(path))
        if not result:
            return ""
        return "\n".join(item[1] for item in result)
    except ImportError:
        logger.warning("RapidOCR 未安装，无法 OCR 图片: %s", path)
        return ""


def parse_file(path: str) -> str:
    """按扩展名自动分派解析，返回纯文本。"""
    p = Path(path)
    ext = p.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return ""
    if ext == ".pdf":
        return parse_pdf(path)
    if ext in (".docx", ".doc"):
        return parse_docx(path)
    if ext in (".xlsx", ".xls"):
        return parse_xlsx(path)
    if ext in (".png", ".jpg", ".jpeg"):
        return parse_image(path)
    # 文本类
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return p.read_text(encoding="gbk", errors="ignore")
