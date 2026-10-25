"""认证模块 Schema：注册 / 登录 / 用户信息。"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="登录名")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    display_name: str = Field(..., min_length=1, max_length=64, description="显示名")
    role: Literal["teacher", "student"] = "student"
    phone: str = Field("", max_length=20, description="手机号（可选）")


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    phone: str = ""
    created_at: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RegisterOut(BaseModel):
    """注册结果：学生直接登录，教师返回待审核。"""

    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserOut] = None
    message: str = "注册成功"
    pending: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


class TeacherReviewOut(BaseModel):
    """待审核教师信息。"""

    id: int
    username: str
    display_name: str
    phone: str = ""
    created_at: Optional[str] = None


class ReviewResult(BaseModel):
    user_id: int
    message: str
