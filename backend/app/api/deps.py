from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.logging import user_id_var
from app.core.security import decode_token


# 定义一个HTTPBearer实例，用于获取token
bearer_scheme = HTTPBearer()


# 定义一个依赖函数，用于获取当前用户
def get_current_user(
        # 定义一个参数，用于接收Authorization头中的token
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        # 定义一个参数，用于接收数据库会话
        db: Session = Depends(get_db)
) -> User:
    # 解码token并获取用户ID
    user_id = decode_token(credentials.credentials)

    # 如果用户ID为空，则抛出401异常
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的token",
        )

    # 根据用户ID从数据库中获取用户对象
    user = db.get(User, user_id)

    # 如果用户对象为空，则抛出401异常
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 日志上下文：后续业务日志自动携带 user_id
    user_id_var.set(user.id)

    return user
