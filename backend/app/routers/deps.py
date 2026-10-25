"""认证依赖：OAuth2 Bearer Token 解析与当前用户获取。"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import User
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """校验 Bearer Token 并返回当前用户；未登录返回 401。"""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供登录凭证")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期或凭证无效")
    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if not user or user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用")
    if user.is_approved != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号待管理员审核，暂时无法使用")
    return user


def require_role(*roles: str):
    """角色校验依赖工厂：admin / teacher / student / parent。"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限执行该操作")
        return user

    return checker
