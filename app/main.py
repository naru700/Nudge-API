import json
import time
from fastapi import FastAPI, HTTPException, Depends, Request
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.auth import create_user, authenticate_user, create_access_token, get_current_user, \
    hash_password, verify_password
from app.api import speech
from app.db.dynamodb import get_table
from app.models.models import SessionStartRequest, MessageResponse, MessageRequest, UserRegister, TokenResponse, \
    UserLogin, UserOut, ChangePasswordRequest
from app.services.credit_manager import decrement_user_credits
from app.services.service import get_llm_response, stream_llm_response
from app.store.sessions_store import start_new_session, append_to_session, list_sessions, \
    get_session_summary, end_session
from app.core.config import CORS_ORIGINS
from app.store.sessions_store import get_session, update_session_metadata
from fastapi.responses import JSONResponse, StreamingResponse

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# In-memory per-session rate limit for /generate
_last_generate: dict[str, float] = {}
_GENERATE_COOLDOWN = 2.0  # seconds

# Include speech router for voice chat
app.include_router(speech.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.post("/register", response_model=TokenResponse, tags=["Auth"])
@limiter.limit("10/minute")
def register(request: Request, req: UserRegister):
    uid = create_user(req.name, req.email, req.password)
    token = create_access_token({"user_id": uid, "email": req.email, "token_version": 1})
    return {"access_token": token}

@app.post("/login", response_model=TokenResponse, tags=["Auth"])
def login(req: UserLogin):
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({
        "user_id": user["user_id"],
        "email": user["email"],
        "token_version": int(user.get("token_version", 1))
    })
    return {"access_token": token}

@app.get("/me", response_model=UserOut, tags=["Me"])
def get_me(user: dict = Depends(get_current_user)):
    table = get_table("users")
    db_user = table.get_item(Key={"user_id": user["user_id"]}).get("Item")

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": db_user["user_id"],
        "name": db_user["name"],
        "email": db_user["email"],
        "credits": int(db_user.get("credits", 0))  # include if you want credits shown
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


@app.post("/generate", tags=["LLM"])
@limiter.limit("30/minute")
async def generate(
    request: Request,
    req: MessageRequest,
    user: dict = Depends(get_current_user)
):
    session = get_session(req.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    now = time.time()
    if now - _last_generate.get(req.session_id, 0) < _GENERATE_COOLDOWN:
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")
    _last_generate[req.session_id] = now

    try:
        decrement_user_credits(user["user_id"])
    except HTTPException as e:
        if e.status_code == 402:
            return JSONResponse(
                status_code=402,
                content={"detail": "You're out of credits. Please top up to continue."}
            )
        raise e

    # Sliding window: system prompt + last 4 messages + new user message
    messages = session.get("messages", [])
    system_prompt = messages[:1]
    recent_exchanges = messages[-4:]
    context_window = system_prompt + recent_exchanges + [{"role": "user", "content": req.user_message}]

    print(f"OpenAI Context ({len(context_window)} msgs, streaming):")
    for msg in context_window:
        print(msg['role'].upper(), ":", msg['content'][:120])

    # Capture session_id / user_message / model in closure so the generator can persist after streaming
    session_id = req.session_id
    user_message = req.user_message
    session_model = session["llm"]

    async def generate_sse():
        full_response = ""
        try:
            async for token in stream_llm_response(context_window, session_model):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"[generate] streaming error: {e}")
            yield f"data: {json.dumps({'error': 'LLM error occurred. Please try again.'})}\n\n"
        finally:
            if full_response:
                append_to_session(session_id, "user", user_message)
                append_to_session(session_id, "assistant", full_response)
                update_session_metadata(session_id)

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.get("/sessions", tags=["Session"])
def get_user_sessions(user: dict = Depends(get_current_user)):
    return list_sessions(user["user_id"])

@app.get("/session-summary/{session_id}", tags=["Session"])
def get_summary(session_id: str, user: dict = Depends(get_current_user)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return get_session_summary(session_id)

@app.post("/end-session/{session_id}", tags=["Session"])
def end(session_id: str, user: dict = Depends(get_current_user)):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return end_session(session_id)

@app.post("/logout", tags=["Auth"])
def logout(user: dict = Depends(get_current_user)):
    # Client should delete token locally; we just acknowledge
    return JSONResponse(content={"message": "Logged out successfully"}, status_code=200)

@app.post("/change-password", tags=["Auth"])
def change_password(
    payload: ChangePasswordRequest,
    user: dict = Depends(get_current_user)
):
    table = get_table("users")

    # Fetch fresh user record
    db_user = table.get_item(Key={"user_id": user["user_id"]}).get("Item")

    if not db_user or not verify_password(payload.old_password, db_user["password"]):
        raise HTTPException(status_code=403, detail="Invalid current password")

    # Update password and atomically bump token_version to invalidate all existing tokens
    new_hashed = hash_password(payload.new_password)
    table.update_item(
        Key={"user_id": user["user_id"]},
        UpdateExpression="SET #pw = :new_pw ADD token_version :one",
        ExpressionAttributeNames={"#pw": "password"},
        ExpressionAttributeValues={":new_pw": new_hashed, ":one": 1}
    )

    return {"message": "Password updated. Please log in again with your new password."}
