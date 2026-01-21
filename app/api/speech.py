"""
Speech-to-Text API endpoints
Handles audio transcription and integration with LLM generation
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from typing import Optional
import logging

from app.services.speech_to_text import (
    SpeechToTextService, 
    FFmpegNotFoundError,
    check_ffmpeg_available
)
from app.api.auth import get_current_user

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["Speech"])

# Lazy-loaded STT service (to avoid slow startup)
_stt_service: Optional[SpeechToTextService] = None


def get_stt_service() -> SpeechToTextService:
    """
    Get or initialize the Speech-to-Text service
    Uses lazy loading to avoid slow application startup
    
    Raises:
        HTTPException: If ffmpeg is not available or service initialization fails
    """
    global _stt_service
    
    if _stt_service is None:
        logger.info("[TRANSCRIBE] Loading STT service...")
        try:
            _stt_service = SpeechToTextService(model_size="base")
            logger.info("[TRANSCRIBE] STT service loaded successfully")
        except FFmpegNotFoundError as e:
            logger.error(f"[TRANSCRIBE] ✗ FFmpeg not found: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "FFmpeg not found",
                    "message": str(e),
                    "instructions": "Please install ffmpeg to enable audio transcription"
                }
            )
        except Exception as e:
            logger.error(f"[TRANSCRIBE] ✗ Error initializing STT service: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error initializing speech service: {str(e)}"
            )
    
    return _stt_service


@router.get("/ping")
async def ping():
    """
    Health check endpoint for speech service
    Also checks if ffmpeg is available
    """
    ffmpeg_available = check_ffmpeg_available()
    
    return {
        "status": "ok",
        "service": "speech-to-text",
        "ffmpeg_available": ffmpeg_available,
        "message": "Speech service is running" if ffmpeg_available else "FFmpeg not found - transcription will fail"
    }


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Transcribe an audio file to text
    
    Args:
        audio: Audio file (mp3, wav, m4a, etc.)
        language: Language code (default: 'en' for English)
    
    Returns:
        JSON with transcription results
    
    Raises:
        HTTPException: If transcription fails or ffmpeg is not available
    """
    logger.info(f"[TRANSCRIBE] Received file: {audio.filename} ({audio.content_type})")
    
    # Validate audio file
    allowed_types = [
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/wave", 
        "audio/x-wav", "audio/m4a", "audio/mp4", "audio/ogg",
        "audio/webm", "audio/flac"
    ]
    
    if audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audio format: {audio.content_type}. Supported: {', '.join(allowed_types)}"
        )
    
    try:
        # Read audio bytes
        audio_bytes = await audio.read()
        logger.info(f"[TRANSCRIBE] Read {len(audio_bytes)} bytes")
        
        # Extract file extension
        file_ext = audio.filename.split(".")[-1].lower() if "." in audio.filename else "mp3"
        
        # Get STT service (lazy loaded)
        logger.info("[TRANSCRIBE] Loading STT service...")
        stt_service = get_stt_service()
        
        # Transcribe
        logger.info("[TRANSCRIBE] STT service loaded, starting transcription...")
        result = stt_service.transcribe_bytes(
            audio_bytes=audio_bytes,
            format=file_ext,
            language=language if language and language != "auto" else None
        )
        
        logger.info(f"[TRANSCRIBE] ✓ Success: {len(result['text'])} characters transcribed")
        
        return {
            "success": True,
            "text": result["text"],
            "language": result["language"],
            "duration": result.get("duration"),
            "segments": result.get("segments", []),
            "model": "whisper-base"
        }
        
    except FFmpegNotFoundError as e:
        logger.error(f"[TRANSCRIBE] ✗ FFmpeg Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "FFmpeg not found",
                "message": str(e),
                "instructions": "Please install ffmpeg to enable audio transcription"
            }
        )
    except Exception as e:
        logger.error(f"[TRANSCRIBE] ✗ Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.post("/transcribe-and-generate")
async def transcribe_and_generate(
    audio: UploadFile = File(...),
    language: str = Form("en"),
    session_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """
    Transcribe audio and generate AI response
    
    Combines speech transcription with the existing /generate endpoint
    
    Args:
        audio: Audio file to transcribe
        language: Language code (default: 'en')
        session_id: Optional session ID for context
        user: Authenticated user (from JWT token)
    
    Returns:
        JSON with transcription and AI-generated response
    """
    logger.info(f"[TRANSCRIBE-GENERATE] User {user['email']} - Session: {session_id}")
    
    # First, transcribe the audio
    transcription_result = await transcribe_audio(audio=audio, language=language)
    
    if not transcription_result["success"]:
        raise HTTPException(
            status_code=500,
            detail="Transcription failed"
        )
    
    transcribed_text = transcription_result["text"]
    logger.info(f"[TRANSCRIBE-GENERATE] Transcribed: {transcribed_text[:100]}...")
    
    # TODO: Integrate with /generate endpoint
    # This would require importing and calling the generate logic
    # For now, return just the transcription
    
    return {
        "success": True,
        "transcription": transcribed_text,
        "language": transcription_result["language"],
        "ai_response": None,  # TODO: Integrate with /generate
        "message": "Transcription completed. AI generation integration pending."
    }
