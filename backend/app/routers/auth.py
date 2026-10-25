"""认证路由：注册 / 登录 / 当前用户。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import User
from app.routers.deps import get_current_user, require_role
from app.schemas.auth import RegisterRequest, RegisterOut, ReviewResult, TeacherReviewOut, TokenOut, UserOut
from app.utils.logging_conf import get_logger
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter()
logger = get_logger("auth")


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        phone=user.phone or "",
        created_at=str(user.created_at) if user.created_at else None,
    )


@router.post("/register", response_model=RegisterOut, summary="注册")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existed = db.query(User).filter(User.username == req.username).first()
    if existed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    pending = req.role == "teacher"
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=req.display_name,
        role=req.role,
        phone=req.phone,
        status=1,
        is_approved=0 if pending else 1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("新用户注册: %s (%s) 待审核=%s", user.username, user.role, pending)
    if pending:
        return RegisterOut(pending=True, message="注册成功，请等待管理员审核通过后再登录")
    token = create_access_token(user.id, user.role)
    return RegisterOut(access_token=token, user=_user_out(user), message="注册成功")


@router.post("/login", response_model=TokenOut, summary="账号密码登录")
def login(payload: dict, db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    if user.is_approved != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号待管理员审核，请稍后再试")
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, user=_user_out(user))


@router.get("/me", response_model=UserOut, summary="当前登录用户")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.get("/pending-teachers", response_model=list[TeacherReviewOut], summary="待审核教师列表")
def pending_teachers(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = (
        db.query(User)
        .filter(User.role == "teacher", User.is_approved == 0)
        .order_by(User.id.asc())
        .all()
    )
    return [
        TeacherReviewOut(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            phone=u.phone or "",
            created_at=str(u.created_at) if u.created_at else None,
        )
        for u in rows
    ]


@router.post("/teachers/{user_id}/approve", response_model=ReviewResult, summary="通过教师审核")
def approve_teacher(user_id: int, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if u.role != "teacher":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该用户不是教师")
    if u.is_approved == 1:
        return ReviewResult(user_id=user_id, message="该教师已通过审核")
    u.is_approved = 1
    db.commit()
    logger.info("教师审核通过: %s (%s)", u.username, u.display_name)
    return ReviewResult(user_id=user_id, message="已通过审核")


@router.post("/teachers/{user_id}/reject", response_model=ReviewResult, summary="拒绝教师审核")
def reject_teacher(user_id: int, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if u.role != "teacher":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该用户不是教师")
    db.delete(u)
    db.commit()
    logger.info("教师审核拒绝并删除: %s (%s)", u.username, u.display_name)
    return ReviewResult(user_id=user_id, message="已拒绝并删除该申请")
