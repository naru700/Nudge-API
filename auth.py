import uuid
from passlib.context import CryptContext
from jose import JWTError, jwt

SECRET_KEY = "secret-must-be-env"  # replace with os.getenv() for real
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fake in-memory DB
USERS = {}

def create_user(email: str, password: str):
    user_id = str(uuid.uuid4())
    hashed_pw = pwd_context.hash(password)
    USERS[email] = {"user_id": user_id, "email": email, "password": hashed_pw}
    return user_id

def authenticate_user(email: str, password: str):
    user = USERS.get(email)
    if not user or not pwd_context.verify(password, user["password"]):
        return None
    return user

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
