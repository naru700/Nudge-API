# FFmpeg Setup Guide for Speech Transcription

## Overview

The speech-to-text feature in Nudge API uses [OpenAI Whisper](https://github.com/openai/whisper) for audio transcription. Whisper requires **FFmpeg** to process audio files (MP3, WAV, M4A, etc.).

## Error: FileNotFoundError [WinError 2]

If you see this error when trying to transcribe audio:

```
FileNotFoundError: [WinError 2] The system cannot find the file specified
```

This means **FFmpeg is not installed** or not available in your system PATH.

---

## Installation Instructions

### Windows

#### Option 1: Using Chocolatey (Recommended)

If you have [Chocolatey](https://chocolatey.org/) installed:

```powershell
choco install ffmpeg
```

#### Option 2: Using winget (Windows 11)

```powershell
winget install ffmpeg
```

#### Option 3: Manual Installation

1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Extract the ZIP file (e.g., to `C:\ffmpeg`)
3. Add FFmpeg to your PATH:
   - Open **System Properties** → **Environment Variables**
   - Edit the **Path** variable under **System variables**
   - Add the path to the `bin` folder (e.g., `C:\ffmpeg\bin`)
   - Click **OK** to save

4. **Restart your terminal/IDE** (PyCharm, VS Code, etc.) for changes to take effect

---

### macOS

Using [Homebrew](https://brew.sh/):

```bash
brew install ffmpeg
```

---

### Linux

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

#### Fedora/RHEL/CentOS

```bash
sudo dnf install ffmpeg
```

#### Arch Linux

```bash
sudo pacman -S ffmpeg
```

---

## Verification

After installation, verify FFmpeg is available:

```bash
ffmpeg -version
```

You should see output like:

```
ffmpeg version 6.0 Copyright (c) 2000-2023 the FFmpeg developers
built with gcc 11.3.0 (Ubuntu 11.3.0-1ubuntu1~22.04)
configuration: ...
```

---

## Testing the Speech API

Once FFmpeg is installed, test the speech transcription endpoint:

### 1. Check Service Health

```bash
curl http://localhost:8000/speech/ping
```

Expected response:

```json
{
  "status": "ok",
  "service": "speech-to-text",
  "ffmpeg_available": true,
  "message": "Speech service is running"
}
```

### 2. Transcribe an Audio File

```bash
curl -X POST "http://localhost:8000/speech/transcribe" \
     -F "audio=@path/to/your/audio.mp3" \
     -F "language=en"
```

Expected response:

```json
{
  "success": true,
  "text": "This is the transcribed text...",
  "language": "en",
  "duration": 15.5,
  "model": "whisper-base"
}
```

---

## Troubleshooting

### FFmpeg still not found after installation

1. **Restart your terminal/IDE** - PATH changes require a restart
2. **Verify PATH**: Run `echo $PATH` (Linux/macOS) or `echo %PATH%` (Windows)
3. **Check installation**: Run `where ffmpeg` (Windows) or `which ffmpeg` (Linux/macOS)

### First transcription is slow

- The first transcription downloads the Whisper model (~100MB for "base" model)
- Subsequent transcriptions are much faster (2-5 seconds)
- Model is cached at `~/.cache/whisper/` (Linux/macOS) or `%USERPROFILE%\.cache\whisper\` (Windows)

### Audio format not supported

Supported formats: MP3, WAV, M4A, OGG, WEBM, FLAC

If your format is not supported, convert it using FFmpeg:

```bash
ffmpeg -i input.aac -c:a libmp3lame output.mp3
```

---

## Model Sizes and Performance

The API uses the **base** model by default. You can change this in `app/services/speech_to_text.py`:

| Model  | Size   | Speed | Accuracy |
|--------|--------|-------|----------|
| tiny   | 39 MB  | ⚡⚡⚡ | ~85%     |
| base   | 74 MB  | ⚡⚡   | ~90%     |
| small  | 244 MB | ⚡     | ~93%     |
| medium | 769 MB | 🐢     | ~95%     |
| large  | 1550 MB| 🐌     | ~97%     |

---

## Additional Resources

- [Whisper GitHub](https://github.com/openai/whisper)
- [FFmpeg Official Site](https://ffmpeg.org/)
- [Whisper Model Cards](https://github.com/openai/whisper/blob/main/model-card.md)

---

## Need Help?

If you're still experiencing issues:

1. Check the server logs for detailed error messages
2. Verify FFmpeg is in your PATH
3. Ensure you have sufficient disk space for model downloads
4. Try testing FFmpeg directly: `ffmpeg -i test.mp3 output.wav`
