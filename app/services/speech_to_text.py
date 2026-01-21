"""
Speech-to-Text Service using OpenAI Whisper
Handles audio transcription with proper error handling for missing dependencies
"""
import os
import shutil
import tempfile
import subprocess
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FFmpegNotFoundError(Exception):
    """Raised when ffmpeg is not found in the system"""
    pass


def check_ffmpeg_available() -> bool:
    """
    Check if ffmpeg is available in the system PATH
    
    Returns:
        bool: True if ffmpeg is available, False otherwise
    """
    return shutil.which("ffmpeg") is not None


def get_ffmpeg_install_instructions() -> str:
    """
    Get platform-specific instructions for installing ffmpeg
    
    Returns:
        str: Installation instructions
    """
    return """
FFmpeg is required for audio transcription but was not found in your system PATH.

Installation instructions:

**Windows:**
  1. Using Chocolatey: choco install ffmpeg
  2. Using winget: winget install ffmpeg
  3. Manual: Download from https://www.gyan.dev/ffmpeg/builds/ and add to PATH

**macOS:**
  brew install ffmpeg

**Linux (Ubuntu/Debian):**
  sudo apt update && sudo apt install ffmpeg

**Linux (Fedora/RHEL):**
  sudo dnf install ffmpeg

After installation, restart your terminal/IDE and verify with: ffmpeg -version
"""


class SpeechToTextService:
    """
    Service for transcribing audio using OpenAI Whisper
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize the Speech-to-Text service
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available"""
        if not check_ffmpeg_available():
            error_msg = "FFmpeg is not installed or not found in system PATH.\n\n"
            error_msg += get_ffmpeg_install_instructions()
            raise FFmpegNotFoundError(error_msg)
    
    def _load_model(self):
        """Lazy load the Whisper model"""
        if self.model is None:
            try:
                import whisper
                logger.info(f"Loading Whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
                logger.info(f"Whisper model loaded successfully")
            except ImportError:
                raise ImportError(
                    "openai-whisper is not installed. "
                    "Install it with: pip install openai-whisper"
                )
    
    def transcribe_file(
        self, 
        audio_file_path: str, 
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe an audio file
        
        Args:
            audio_file_path: Path to the audio file
            language: Language code (e.g., 'en', 'es', 'fr'). None for auto-detect
        
        Returns:
            Dict with transcription results including text, segments, and metadata
        
        Raises:
            FFmpegNotFoundError: If ffmpeg is not available
            FileNotFoundError: If audio file doesn't exist
        """
        # Verify ffmpeg is still available
        if not check_ffmpeg_available():
            raise FFmpegNotFoundError(get_ffmpeg_install_instructions())
        
        # Verify audio file exists
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Load model if not already loaded
        self._load_model()
        
        logger.info(f"Transcribing audio file: {audio_file_path}")
        
        # Transcribe with Whisper
        result = self.model.transcribe(
            audio_file_path,
            language=language,
            fp16=False,  # Use FP32 for CPU compatibility
            verbose=False
        )
        
        logger.info(f"Transcription completed. Text length: {len(result['text'])}")
        
        return {
            "text": result["text"].strip(),
            "language": result["language"],
            "segments": result.get("segments", []),
            "duration": result.get("duration"),
        }
    
    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        format: str = "mp3",
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio from bytes
        
        Args:
            audio_bytes: Audio file content as bytes
            format: Audio format (mp3, wav, etc.)
            language: Language code (e.g., 'en', 'es', 'fr'). None for auto-detect
        
        Returns:
            Dict with transcription results
        
        Raises:
            FFmpegNotFoundError: If ffmpeg is not available
        """
        # Verify ffmpeg is available before creating temp file
        if not check_ffmpeg_available():
            raise FFmpegNotFoundError(get_ffmpeg_install_instructions())
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            suffix=f".{format}", 
            delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(audio_bytes)
        
        try:
            # Transcribe the temporary file
            result = self.transcribe_file(tmp_path, language=language)
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
