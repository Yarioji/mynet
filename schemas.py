from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# ── Auth ──────────────────────────────────────────────
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = ""

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User ──────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    avatar_url: str
    is_online: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserShort(BaseModel):
    id: int
    username: str
    display_name: str
    avatar_url: str
    is_online: bool

    class Config:
        from_attributes = True


# ── Chat ──────────────────────────────────────────────
class ChatCreate(BaseModel):
    member_ids: List[int]       # ID пользователей (без себя)
    name: Optional[str] = ""    # Только для групп
    is_group: bool = False

class ChatOut(BaseModel):
    id: int
    name: str
    is_group: bool
    members: List[UserShort]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Message ───────────────────────────────────────────
class MessageCreate(BaseModel):
    content: str

class MessageOut(BaseModel):
    id: int
    content: str
    chat_id: int
    sender: UserShort
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
