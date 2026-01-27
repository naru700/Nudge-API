import base64
import json
import tempfile
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import OpenAI

from app.core.config import OPENAI_API_KEY

router = APIRouter(prefix="/speech", tags=["Speech"])

# Initialize OpenAI client for Whisper transcription
openai_client = OpenAI(api_key=OPENAI_API_KEY)


class AudioBuffer:
    """Manages audio buffering for Voice Activity Detection (VAD)"""

    def __init__(self):
        self.buffers: Dict[str, List[bytes]] = {}  # session_id -> list of audio chunks
        self.last_audio_time: Dict[str, float] = {}  # session_id -> timestamp
        self.pending_timestamps: Dict[str, str] = {}  # session_id -> first chunk timestamp
        self.SILENCE_THRESHOLD = 2.0  # seconds of silence before transcribing (reduced for faster response)
        self.MIN_BUFFER_SIZE = 5120  # 5KB minimum to transcribe

    def add_chunk(self, session_id: str, audio_bytes: bytes, timestamp: str) -> None:
        """Add audio chunk to buffer"""
        if session_id not in self.buffers:
            self.buffers[session_id] = []
            self.pending_timestamps[session_id] = timestamp

        self.buffers[session_id].append(audio_bytes)
        self.last_audio_time[session_id] = time.time()
        print(f"📦 Buffered chunk for session {session_id}: {len(audio_bytes)} bytes (total chunks: {len(self.buffers[session_id])})")

    def should_transcribe(self, session_id: str) -> bool:
        """Check if enough silence has passed to transcribe accumulated audio"""
        if session_id not in self.last_audio_time:
            return False

        silence_duration = time.time() - self.last_audio_time[session_id]
        has_audio = session_id in self.buffers and len(self.buffers[session_id]) > 0

        # Calculate total buffer size
        total_size = sum(len(chunk) for chunk in self.buffers.get(session_id, []))

        if silence_duration >= self.SILENCE_THRESHOLD and has_audio and total_size >= self.MIN_BUFFER_SIZE:
            print(f"🔇 Silence detected for session {session_id}: {silence_duration:.1f}s - Ready to transcribe {total_size} bytes")
            return True
        return False

    def get_combined_audio(self, session_id: str) -> Optional[bytes]:
        """Get all accumulated audio for a session and clear buffer"""
        if session_id not in self.buffers or not self.buffers[session_id]:
            return None

        combined = b''.join(self.buffers[session_id])
        timestamp = self.pending_timestamps.get(session_id)

        # Clear buffers
        self.buffers[session_id] = []
        del self.last_audio_time[session_id]
        if session_id in self.pending_timestamps:
            del self.pending_timestamps[session_id]

        print(f"🎤 Combined audio for session {session_id}: {len(combined)} bytes")
        return combined

    def get_timestamp(self, session_id: str) -> Optional[str]:
        """Get the timestamp of the first chunk in buffer"""
        return self.pending_timestamps.get(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear all buffers for a session"""
        if session_id in self.buffers:
            del self.buffers[session_id]
        if session_id in self.last_audio_time:
            del self.last_audio_time[session_id]
        if session_id in self.pending_timestamps:
            del self.pending_timestamps[session_id]


audio_buffer = AudioBuffer()


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
        Transcribed text (empty string if only music/noise detected)
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

        # Filter out music symbols and artifacts
        text = transcript.text.strip()

        # List of patterns that indicate non-speech audio
        ignore_patterns = [
            '♪', '♫', '🎵', '🎶',  # Music symbols
            '[Music]', '[music]',
            '[Silence]', '[silence]',
            'you', 'You',  # Common Whisper artifacts from silence
            'uh', 'um', 'hmm',  # Single filler words
        ]

        # If transcription is only music/noise artifacts, return empty
        if text in ignore_patterns or len(text) < 3:
            print(f"Filtered out non-speech: '{text}'")
            return ""

        # If transcription contains only music symbols
        if all(char in '♪♫🎵🎶 []Musicmusic' for char in text):
            print(f"Filtered out music: '{text}'")
            return ""

        return text
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription with Voice Activity Detection (VAD)

    VAD Strategy:
    - Accumulates audio chunks (sent every 2-3 seconds from client)
    - Detects 3+ seconds of silence
    - Transcribes complete accumulated audio as one question
    - Handles pauses naturally

    Supports both old format (text/bytes) and new format (JSON with base64)

    For Angular apps:
    - Connect: ws://localhost:8000/speech/ws
    - Send: {"audio": "base64_string", "timestamp": "ISO_date", "session_id": "required"}
    - Receive: {"type": "transcription", "text": "...", "timestamp": "...", "session_id": "..."}
    """
    await manager.connect(websocket)

    session_id = None
    vad_check_task = None
    is_connected = True  # Flag to track WebSocket state - must be before check_vad_periodically

    async def check_vad_periodically():
        """Background task to check for silence and trigger transcription"""
        nonlocal is_connected  # Access the parent scope variable

        while is_connected:
            try:
                await asyncio.sleep(1)  # Check every second

                if session_id and is_connected and audio_buffer.should_transcribe(session_id):
                    combined_audio = audio_buffer.get_combined_audio(session_id)
                    timestamp = audio_buffer.get_timestamp(session_id)

                    if combined_audio and is_connected:
                        print(f"🎯 VAD triggered transcription for session {session_id}")
                        transcription = transcribe_audio(combined_audio)

                        if transcription and is_connected:
                            print(f"✅ Complete question transcribed: {transcription}")
                            try:
                                await manager.send_json({
                                    "type": "transcription",
                                    "text": transcription,
                                    "timestamp": timestamp,
                                    "session_id": session_id
                                }, websocket)
                            except Exception as send_error:
                                print(f"⚠️ Could not send transcription (WebSocket closed): {send_error}")
                                break
                        else:
                            print("⏭️ Skipping empty/filtered transcription")

            except asyncio.CancelledError:
                print("VAD task cancelled")
                break
            except Exception as e:
                print(f"VAD check error: {e}")
                break

    try:
        # Start VAD monitoring task
        vad_check_task = asyncio.create_task(check_vad_periodically())

        while True:
            try:
                message = await websocket.receive()

                # Handle new JSON format with VAD buffering
                if "text" in message:
                    try:
                        data = json.loads(message["text"])

                        # Check if it's JSON with audio field
                        if isinstance(data, dict) and "audio" in data:
                            audio_base64 = data.get("audio")
                            timestamp = data.get("timestamp")
                            session_id = data.get("session_id", session_id)

                            if not session_id:
                                await manager.send_json({
                                    "type": "error",
                                    "message": "session_id is required for VAD"
                                }, websocket)
                                continue

                            # Decode base64 audio
                            audio_bytes = base64.b64decode(audio_base64)

                            # Skip very small chunks (likely silence)
                            if len(audio_bytes) < 2048:  # 2KB threshold
                                print(f"⏭️ Skipping tiny chunk: {len(audio_bytes)} bytes")
                                continue

                            print(f"📥 Audio chunk received: {len(audio_bytes)} bytes")

                            # Add to buffer instead of immediate transcription
                            audio_buffer.add_chunk(session_id, audio_bytes, timestamp)

                            # Send acknowledgment
                            await manager.send_json({
                                "type": "ack",
                                "message": "chunk_received",
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
                    # Binary audio data (old format) - immediate transcription
                    audio_data = message["bytes"]
                    print(f"Audio data received (bytes): {len(audio_data)} bytes")

                    # Immediate transcription for binary format (backward compatibility)
                    transcription = transcribe_audio(audio_data)  # Sync call - no await

                    if transcription:
                        print(f"System audio transcribed: {transcription}")
                        await manager.send_text(transcription, websocket)
                    else:
                        print("Skipping empty/filtered transcription")

            except WebSocketDisconnect:
                is_connected = False  # Signal VAD task to stop
                manager.disconnect(websocket)
                print("WebSocket disconnected")
                if session_id:
                    audio_buffer.clear_session(session_id)
                break

            except Exception as e:
                print(f"WebSocket error: {str(e)}")
                import traceback
                traceback.print_exc()

                # Only try to send error if still connected
                if is_connected:
                    try:
                        await manager.send_json({
                            "type": "error",
                            "message": str(e)
                        }, websocket)
                    except:
                        pass  # WebSocket already closed

    finally:
        # Signal background task to stop
        is_connected = False

        # Cancel VAD monitoring task
        if vad_check_task:
            vad_check_task.cancel()
            try:
                await vad_check_task
            except asyncio.CancelledError:
                pass

        manager.disconnect(websocket)
        if session_id:
            audio_buffer.clear_session(session_id)
            print(f"🧹 Cleaned up session {session_id}")
