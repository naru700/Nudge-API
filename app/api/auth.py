import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError

from app.core.config import JWT_SECRET
from app.core.security import oauth2_scheme
from app.db.dynamodb import get_table
from datetime import datetime, timedelta

from fastapi import HTTPException
from boto3.dynamodb.conditions import Key
from passlib.context import CryptContext

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

# Set auto_error=True to enforce token validation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=True)

# Fake in-memory DB
USERS = {}


def create_user(name: str, email: str, password: str):
    table = get_table("users")

    # Check if user already exists
    response = table.query(
        IndexName="email-index",  # requires a GSI on `email`
        KeyConditionExpression=Key("email").eq(email)
    )

    if response["Items"]:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())

    hashed_password = hash_password(password)  # hash the password here

    item = {
        "user_id": user_id,
        "name": name,
        "email": email,
        "password": hashed_password,
        "credits": 50
    }
    table.put_item(Item=item)
    return user_id



def authenticate_user(email: str, password: str):
    table = get_table("users")
    response = table.query(
        IndexName="email-index",
        KeyConditionExpression=Key("email").eq(email)
    )
    items = response.get("Items", [])
    if not items:
        return None

    user = items[0]
    hashed_pw = user.get("password")
    if not hashed_pw or not verify_password(password, hashed_pw):
        return None

    return user


def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        email = payload.get("email")
        if not user_id or not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return {"user_id": user_id, "email": email}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)