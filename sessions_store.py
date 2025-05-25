import uuid

# Simple in-memory session store
SESSIONS = {}

def start_new_session(user_id: str, system_prompt: str):
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = [{
        "role": "system",
        "content": system_prompt
    }]
    return session_id

def get_session_messages(session_id: str):
    return SESSIONS.get(session_id, [])

def append_to_session(session_id: str, role: str, content: str):
    if session_id in SESSIONS:
        SESSIONS[session_id].append({
            "role": role,
            "content": content
        })
