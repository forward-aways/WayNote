from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from app.core.config import settings


# SECRET_KEY 统一从 backend/.env 读取，禁止硬编码（见 ADR-20260929）
SECRET_KEY = settings.secret_key
# algorithm是JWT的算法，用于签名和验证JWT
ALGORITHM = "HS256"
# access_token_expire_minutes是访问令牌的过期时间，单位是分钟
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days


# 对密码进行哈希处理
def hash_password(password: str) -> str:
    # 将密码编码为字节并截取前72个字节
    pwd_bytes = password.encode("utf-8")[:72]
    # 对密码进行哈希处理并返回
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


# 验证密码
def verify_password(plain: str, hashed: str) -> bool:
    # 将明文密码编码为字节并截取前72个字节
    plain_bytes = plain.encode("utf-8")[:72]
    # 检查哈希密码是否匹配并返回结果
    return bcrypt.checkpw(plain_bytes, hashed.encode("utf-8"))


# 创建访问令牌
def create_access_token(user_id: int) -> str:
    # 设置令牌的过期时间
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 设置令牌的载荷
    payload = {"sub": str(user_id), "exp": expire}
    # 返回签名后的令牌
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# 解码令牌
def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None

