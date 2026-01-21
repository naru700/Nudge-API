# 🧠 Nudge — AI Assistant

Nudge is a real-time AI-powered assistant designed to help candidates during meetings. It listens, transcribes, and generates high-quality responses using OpenAI’s GPT models.

---

## 🚀 Features

- ✅ User registration & login with JWT auth
- ✅ Start and manage LLM-based sessions
- ✅ Send questions and receive structured responses
- ✅ Sliding context window to reduce cost and improve speed
- ✅ Speech-to-text transcription using OpenAI Whisper (requires FFmpeg)

---

## 📦 Tech Stack

- **Backend**: FastAPI + Python
- **LLM**: OpenAI GPT-4
- **Authentication**: JWT
- **Speech-to-Text**: OpenAI Whisper (requires FFmpeg)

---

## 🛠️ Local Setup

### 1. Clone the repo
git clone https://github.com/your-username/nudge-backend.git
cd nudge-backend.

---

💡 This step sets up your isolated environment

## 2. Create a virtual environment

python -m venv .venv
.\.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

### 3. Install dependencies

pip install -r requirements.txt

### 4. Install FFmpeg (Required for Speech Transcription)

**Windows:**
```powershell
choco install ffmpeg
# or
winget install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

For detailed installation instructions, see [FFMPEG_SETUP.md](FFMPEG_SETUP.md)

### 5. Create a .env file

### 6. Run the app
uvicorn app.main:app --reload

---

App runs at: http://localhost:8000
Swagger docs: http://localhost:8000/docs 

### Speech API Endpoints

- `GET /speech/ping` - Check if speech service is available
- `POST /speech/transcribe` - Transcribe audio file to text
- `POST /speech/transcribe-and-generate` - Transcribe audio and generate AI response

For testing the speech API, see [FFMPEG_SETUP.md](FFMPEG_SETUP.md)

---


🧑 Author
Built with ❤️ by @Kalyan
---





