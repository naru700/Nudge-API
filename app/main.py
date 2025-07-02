from fastapi import FastAPI, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware

from app.api.auth import USERS, create_user, authenticate_user, create_access_token, decode_token, get_current_user
from app.models.models import SessionStartRequest, MessageResponse, MessageRequest, UserRegister, TokenResponse, UserLogin, UserOut
from app.services.service import get_llm_response
from app.store.sessions_store import start_new_session, get_session_messages, append_to_session
from app.core.config import CORS_ORIGINS
from app.core.security import oauth2_scheme

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post("/register")
def register(req: UserRegister):
    if req.email in USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = create_user(req.name, req.email, req.password)
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
async def start_session(
    req: SessionStartRequest,
    user: dict = Depends(get_current_user)
):
    session_id = start_new_session( req.prompt)
    return {"session_id": session_id}

@app.post("/generate", response_model=MessageResponse)
async def generate(
    req: MessageRequest,
    user: dict = Depends(get_current_user)
):
    messages = get_session_messages(req.session_id)

    # Sliding window: system + last 2 message pairs (4 total)
    system_prompt = messages[:1]
    recent_exchanges = messages[-4:]  # 2 user+assistant turns = 4 messages

    context_window = system_prompt + recent_exchanges

    user_msg = {"role": "user", "content": req.user_message}
    context_window.append(user_msg)

    print(f"OpenAI Context ({len(context_window)} msgs):")
    for msg in context_window:
        print(msg['role'].upper(), ":", msg['content'])

    llm_reply = get_llm_response(context_window)

    append_to_session(req.session_id, "user", req.user_message)
    append_to_session(req.session_id, "assistant", llm_reply)

    return {"response": llm_reply}


