import base64
import json
import tempfile
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import OpenAI
from app.core.config import OPENAI_API_KEY
router = APIRouter(prefix="/speech", tags=["Speech"])
# Initialize OpenAI client for Whisper transcription
openai_client = OpenAI(api_key=OPENAI_API_KEY)
class ConnectionManager:
    """Manages WebSocket connections"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    async def send_text(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    async def send_json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)
manager = ConnectionManager()
def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe audio using OpenAI Whisper API
    Args:
        audio_bytes: Raw audio data in WebM or other format
    Returns:
        Transcribed text
    """
    try:
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
        # Transcribe using Whisper
        with open(temp_audio_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        # Clean up temp file
        Path(temp_audio_path).unlink()
        return transcript.text
    except Exception as e:
        print(f"Transcription error: {e}")
        return f"[Error transcribing audio: {str(e)}]"
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription
    Supports both old format (text/bytes) and new format (JSON with base64)
    For Angular apps:
    - Connect: ws://localhost:8000/speech/ws
    - Send: {"audio": "base64_string", "timestamp": "ISO_date", "session_id": "optional"}
    - Receive: {"type": "transcription", "text": "...", "timestamp": "...", "session_id": "..."}
    """
    await manager.connect(websocket)
    session_id = None
    try:
        while True:
            try:
                message = await websocket.receive()
                # Handle new JSON format (for Angular)
                if "text" in message:
                    try:
                        data = json.loads(message["text"])
                        # Check if it's JSON with audio field
                        if isinstance(data, dict) and "audio" in data:
                            audio_base64 = data.get("audio")
                            timestamp = data.get("timestamp")
                            session_id = data.get("session_id", session_id)
                            # Decode base64 audio
                            audio_bytes = base64.b64decode(audio_base64)
                            print(f"Audio data received (base64): {len(audio_bytes)} bytes")
                            # Transcribe
                            transcription = transcribe_audio(audio_bytes)
                            print(f"Transcribed: {transcription}")
                            # Send JSON response
                            await manager.send_json({
                                "type": "transcription",
                                "text": transcription,
                                "timestamp": timestamp,
                                "session_id": session_id
                            }, websocket)
                        else:
                            # Old format: plain text from browser speech recognition
                            print(f"Voice input received (text): {data}")
                    except (json.JSONDecodeError, ValueError):
                        # Not JSON, treat as plain text (old format)
                        data = message["text"]
                        print(f"Voice input received (plain text): {data}")
                elif "bytes" in message:
                    # Binary audio data (old format)
                    audio_data = message["bytes"]
                    print(f"Audio data received (bytes): {len(audio_data)} bytes")
                    # Transcribe
                    transcription = transcribe_audio(audio_data)
                    print(f"System audio transcribed: {transcription}")
                    # Send transcription back
                    await manager.send_text(transcription, websocket)
            except WebSocketDisconnect:
                manager.disconnect(websocket)
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"WebSocket error: {str(e)}")
                import traceback
                traceback.print_exc()
                await manager.send_json({
                    "type": "error",
                    "message": str(e)
                }, websocket)
    finally:
        manager.disconnect(websocket)
