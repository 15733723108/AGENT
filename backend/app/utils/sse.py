"""SSE（Server-Sent Events）工具：统一事件格式化。"""
import json
from typing import Any, AsyncGenerator


def sse_event(event: str, data: Any) -> str:
    """构造单条 SSE 事件。data 为 JSON 序列化后的对象。"""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def sse_done() -> str:
    return sse_event("done", {"status": "ok"})


def sse_error(message: str) -> str:
    return sse_event("error", {"message": message})


async def event_stream(gen: AsyncGenerator[str, None]):
    """包装异步生成器为 SSE 字节流。"""
    async for chunk in gen:
        yield chunk.encode("utf-8")
