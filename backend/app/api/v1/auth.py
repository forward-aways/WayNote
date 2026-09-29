from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.user import UserRegister, UserLogin, UserOut, TokenOut
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password, create_access_token


log = get_logger("api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


# 注册用户接口，返回token，7天有效期
@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if not settings.allow_registration:
        log.warning("注册已关闭，拒绝注册请求", extra={"event": "auth.register.disabled"})
        raise HTTPException(status_code=403, detail="注册功能已关闭")

    exists = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 创建用户
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name
    )
    # 添加用户到数据库
    db.add(user)
    # 提交事务
    db.commit()
    # 刷新用户对象
    db.refresh(user)

    # 创建token
    token = create_access_token(user.id)
    # 返回token
    log.info("用户注册 id=%s", user.id, extra={"event": "auth.register"})
    return TokenOut(access_token=token)


# 登录接口，返回token，7天有效期
@router.post("/login", response_model=TokenOut)
def login(data: UserLogin, db: Session = Depends(get_db)):
    # 查询用户
    user = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        log.warning("登录失败 email=%s", data.email, extra={"event": "auth.login.failed"})
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    # 创建token
    token = create_access_token(user.id)
    log.info("登录成功 id=%s", user.id, extra={"event": "auth.login"})
    return TokenOut(access_token=token)


# 获取当前用户接口，返回用户信息
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


