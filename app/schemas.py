from pydantic import BaseModel, EmailStr
from typing import Optional, List
import datetime
from enum import Enum

class ChatType(str, Enum):
    private = "private"
    group = "group"

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class MessageCreate(BaseModel):
    chat_id: Optional[int] = None
    recipient_id: Optional[int] = None
    text: str

class MessageOut(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    timestamp: datetime.datetime
    read: bool

    class Config:
        orm_mode = True

class GroupCreate(BaseModel):
    name: str
    participant_ids: List[int]

class GroupOut(BaseModel):
    id: int
    name: str
    creator_id: int
    chat_id: int
    participant_ids: List[int]

    class Config:
        orm_mode = True
