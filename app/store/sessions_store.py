import uuid

from fastapi import HTTPException

from app.db.dynamodb import get_table
from datetime import datetime
from boto3.dynamodb.conditions import Key

def start_new_session(user_id: str, position: str, llm: str, prompt: str, custom_prompt: str):
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    table = get_table("sessions")

    session_item = {
        "session_id": session_id,
        "user_id": user_id,
        "position": position,
        "llm": llm,
        "prompt": prompt,
        "custom_prompt": custom_prompt,
        "status": "active",
        "messages": [{"role": "system", "content": prompt}],
        "question_count": 0,
        "start_time": now,
        "last_updated": now
    }

    table.put_item(Item=session_item)
    return session_id

def append_to_session(session_id: str, role: str, content: str):
    table = get_table("sessions")
    response = table.get_item(Key={"session_id": session_id})
    session = response.get("Item")

    if not session:
        raise ValueError("Session not found")

    messages = session.get("messages", [])
    messages.append({"role": role, "content": content})
    table.update_item(
        Key={"session_id": session_id},
        UpdateExpression="SET messages = :msgs",
        ExpressionAttributeValues={":msgs": messages}
    )


def get_session_messages(session_id: str):
    table = get_table("sessions")
    response = table.get_item(Key={"session_id": session_id})
    session = response.get("Item")

    if not session:
        raise ValueError("Session not found")

    return session.get("messages", [])

def get_session(session_id: str):
    table = get_table("sessions")
    return table.get_item(Key={"session_id": session_id}).get("Item")

def update_session_metadata(session_id: str):
    table = get_table("sessions")
    session = get_session(session_id)

    question_count = session.get("question_count", 0) + 1
    last_updated = datetime.utcnow().isoformat()

    table.update_item(
        Key={"session_id": session_id},
        UpdateExpression="SET question_count = :qc, last_updated = :ts",
        ExpressionAttributeValues={
            ":qc": question_count,
            ":ts": last_updated
        }
    )

def list_sessions(user_id: str):
    table = get_table("sessions")
    response = table.query(
        IndexName="user_id-index",
        KeyConditionExpression=Key("user_id").eq(user_id)
    )
    return response.get("Items", [])



def get_session_summary(session_id: str):
    table = get_table("sessions")
    session = table.get_item(Key={"session_id": session_id}).get("Item")
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session["session_id"],
        "position": session["position"],
        "status": session["status"],
        "question_count": session["question_count"],
        "start_time": session["start_time"],
        "last_updated": session["last_updated"]
    }

def end_session(session_id: str):
    table = get_table("sessions")
    now = datetime.utcnow().isoformat()
    table.update_item(
        Key={"session_id": session_id},
        UpdateExpression="SET #s = :ended, ended_at = :now",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":ended": "ended", ":now": now}
    )
