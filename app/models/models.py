from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

# ----------- Auth Models -----------

class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    user_id: str
    name: str
    email: str
    credits: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v

# ----------- Session Models -----------

ALLOWED_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o4-mini"}

class SessionStartRequest(BaseModel):
    position: str = Field(max_length=200)
    llm: str = Field(max_length=50)
    prompt: str = Field(max_length=5000)
    customPrompt: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("position", "prompt")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v

    @field_validator("llm")
    @classmethod
    def llm_allowed(cls, v: str) -> str:
        if v not in ALLOWED_MODELS:
            raise ValueError(f"Model must be one of: {', '.join(sorted(ALLOWED_MODELS))}")
        return v

class SessionStartResponse(BaseModel):
    session_id: str

class SessionOut(BaseModel):
    session_id: str
    user_id: str
    position: str
    llm: str
    prompt: str
    customPrompt: Optional[str] = None
    question_count: int
    last_updated: datetime

# ----------- Message Models -----------

class MessageRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    user_message: str = Field(max_length=2000)

    @field_validator("user_message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

class MessageResponse(BaseModel):
    response: str

class MessageLog(BaseModel):
    role: str
    content: str
    timestamp: datetime
