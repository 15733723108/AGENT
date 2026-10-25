"""统一响应格式：{code, message, data}。"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


def ok(data: Any = None, message: str = "ok") -> ApiResponse:
    return ApiResponse(code=0, message=message, data=data)


def fail(code: int, message: str) -> ApiResponse:
    return ApiResponse(code=code, message=message, data=None)
