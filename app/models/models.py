from pydantic import BaseModel

class SessionStartRequest(BaseModel):
    prompt: str


class MessageRequest(BaseModel):
    session_id: str
    user_message: str

class MessageResponse(BaseModel):
    response: str

class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    user_id: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
