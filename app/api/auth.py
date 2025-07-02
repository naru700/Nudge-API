import uuid

from fastapi import Depends, HTTPException
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import JWT_SECRET
from app.core.security import oauth2_scheme

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fake in-memory DB
USERS = {}

def create_user(name: str, email: str, password: str):
    user_id = str(uuid.uuid4())
    hashed_pw = pwd_context.hash(password)
    USERS[email] = {"user_id": user_id, "name": name, "email": email, "password": hashed_pw}
    return user_id

def authenticate_user(email: str, password: str):
    user = USERS.get(email)
    if not user or not pwd_context.verify(password, user["password"]):
        return None
    return user

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise

def create_access_token(data: dict):
    return jwt.encode(data, JWT_SECRET, algorithm="HS256")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
