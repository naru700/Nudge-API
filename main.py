from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.cors import CORSMiddleware

from auth import USERS, create_user, authenticate_user, create_access_token, decode_token
from models import SessionStartRequest, MessageResponse, MessageRequest, UserRegister, TokenResponse, UserLogin, UserOut
from service import get_llm_response
from sessions_store import start_new_session, get_session_messages, append_to_session

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Allow frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

@app.post("/register")
def register(req: UserRegister):
    if req.email in USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = create_user(req.email, req.password)
    return {"user_id": uid}

@app.post("/login", response_model=TokenResponse)
def login(req: UserLogin):
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"user_id": user["user_id"], "email": user["email"]})
    return {"access_token": token}

@app.get("/me", response_model=UserOut)
def get_me(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        return {"user_id": payload["user_id"], "email": payload["email"]}
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/")
async def root():
    return {"message": "Nudge backend is running."}


@app.post("/start-session")
async def start_session(req: SessionStartRequest):
    session_id = start_new_session(req.user_id, req.prompt)
    return {"session_id": session_id}


@app.post("/generate", response_model=MessageResponse)
async def generate(req: MessageRequest):
    # 1. Get session history
    messages = get_session_messages(req.session_id)

    # 2. Append new user input
    user_msg = {"role": "user", "content": req.user_message}
    messages.append(user_msg)

    # 3. Send full history to LLM
    llm_reply = get_llm_response(messages)

    # 4. Append assistant response to history
    assistant_msg = {"role": "assistant", "content": llm_reply}
    append_to_session(req.session_id, "user", req.user_message)
    append_to_session(req.session_id, "assistant", llm_reply)

    return {"response": llm_reply}

