from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ----------- Auth Models -----------

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

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

# ----------- Session Models -----------

class SessionStartRequest(BaseModel):
    position: str
    llm: str
    prompt: str
    customPrompt: Optional[str] = None

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
    session_id: str
    user_message: str

class MessageResponse(BaseModel):
    response: str

class MessageLog(BaseModel):
    role: str
    content: str
    timestamp: datetime
