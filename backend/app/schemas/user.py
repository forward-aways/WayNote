from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

# 6 位数字码（与 core/email_code.generate_code 的输出格式一致）
CODE_FIELD = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class UserRegister(BaseModel):
    email: EmailStr
    # 服务端校验才是权威（前端校验只负责体验）；72 与 bcrypt 的字节上限对齐
    password: str = Field(min_length=6, max_length=72)
    name: str | None = Field(default=None, max_length=50)
    # 注册邮箱验证码（purpose=register）：证明邮箱所有权，见 ADR §6.5
    code: str = CODE_FIELD


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class EmailCodeRequest(BaseModel):
    email: EmailStr
    # 用途隔离（不变量 I4）：login=免密登录（未注册则建号）；register=注册验证；reset=找回/设置密码
    purpose: Literal["login", "register", "reset"]


class EmailCodeOut(BaseModel):
    ok: bool = True
    cooldown_seconds: int
    ttl_minutes: int
    message: str


class EmailCodeLogin(BaseModel):
    email: EmailStr
    code: str = CODE_FIELD


class PasswordReset(BaseModel):
    email: EmailStr
    code: str = CODE_FIELD
    new_password: str = Field(min_length=6, max_length=72)


class PasswordChange(BaseModel):
    """已登录改密：有密码走 old_password；免密账号走邮箱验证码（purpose=reset）。"""

    new_password: str = Field(min_length=6, max_length=72)
    old_password: str | None = None
    code: str | None = Field(default=None, min_length=6, max_length=6, pattern=r"^\d{6}$")


class UserOut(BaseModel):
    id: int
    email: str
    name: str | None
    created_at: datetime
    # 由 User.has_password 派生（免密账号为 False）
    has_password: bool

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
