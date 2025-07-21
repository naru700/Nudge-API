from fastapi import FastAPI, HTTPException, Depends
from starlette.middleware.cors import CORSMiddleware

from app.api.auth import USERS, create_user, authenticate_user, create_access_token, decode_token, get_current_user
from app.db.dynamodb import get_table
from app.models.models import SessionStartRequest, MessageResponse, MessageRequest, UserRegister, TokenResponse, UserLogin, UserOut
from app.services.service import get_llm_response
from app.store.sessions_store import start_new_session, get_session_messages, append_to_session, list_sessions, \
    get_session_summary, end_session
from app.core.config import CORS_ORIGINS
from app.store.sessions_store import get_session, update_session_metadata
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post("/register", tags=["Auth"])
def register(req: UserRegister):
    if req.email in USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = create_user(req.name, req.email, req.password)
    return {"user_id": uid}

@app.post("/login", response_model=TokenResponse, tags=["Auth"])
def login(req: UserLogin):
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"user_id": user["user_id"], "email": user["email"]})
    return {"access_token": token}

@app.get("/me", response_model=UserOut, tags=["Me"])
def get_me(user: dict = Depends(get_current_user)):
    table = get_table("users")
    db_user = table.get_item(Key={"email": user["email"]}).get("Item")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": db_user["user_id"],
        "name": db_user["name"],
        "email": db_user["email"]
    }


@app.get("/")
async def root():
    return {"message": "Nudge backend is running."}


@app.post("/start-session", tags=["session"])
async def start_session(
    req: SessionStartRequest,
    user: dict = Depends(get_current_user)
):
    session_id = start_new_session(
        user_id=user["user_id"],
        position=req.position,
        llm=req.llm,
        prompt=req.prompt,
        custom_prompt=req.customPrompt
    )
    return {"session_id": session_id}


@app.post("/generate", response_model=MessageResponse, tags=["LLM"])
async def generate(
    req: MessageRequest,
    user: dict = Depends(get_current_user)
):
    session = get_session(req.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if session.get("credits_remaining", 0) <= 0:
        raise HTTPException(status_code=402, detail="Out of credits")

    # Use sliding window: system + last 2 turns
    messages = session.get("messages", [])
    system_prompt = messages[:1]
    recent_exchanges = messages[-4:]
    context_window = system_prompt + recent_exchanges

    user_msg = {"role": "user", "content": req.user_message}
    context_window.append(user_msg)

    print(f"OpenAI Context ({len(context_window)} msgs):")
    for msg in context_window:
        print(msg['role'].upper(), ":", msg['content'])

    llm_reply = get_llm_response(context_window)

    append_to_session(req.session_id, "user", req.user_message)
    append_to_session(req.session_id, "assistant", llm_reply)

    update_session_metadata(req.session_id)  # ⬅️ Updates count, credits, timestamp

    return {"response": llm_reply}

@app.get("/sessions")
def get_user_sessions(user: dict = Depends(get_current_user)):
    return list_sessions(user["user_id"])

@app.get("/session-summary/{session_id}")
def get_summary(session_id: str, user: dict = Depends(get_current_user)):
    return get_session_summary(session_id)

@app.post("/end-session/{session_id}")
def end(session_id: str, user: dict = Depends(get_current_user)):
    return end_session(session_id)

@app.post("/logout", tags=["Auth"])
def logout(user: dict = Depends(get_current_user)):
    # Client should delete token locally; we just acknowledge
    return JSONResponse(content={"message": "Logged out successfully"}, status_code=200)
