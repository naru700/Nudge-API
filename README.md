# 🧠 Nudge — AI Assistant

Nudge is a real-time AI-powered assistant designed to help candidates during meetings. It listens, transcribes, and generates high-quality responses using OpenAI’s GPT models.

---

## 🚀 Features

- ✅ User registration & login with JWT auth
- ✅ Start and manage LLM-based sessions
- ✅ Send questions and receive structured responses
- ✅ Sliding context window to reduce cost and improve speed
- 🔜 (Upcoming) Real-time voice-to-text transcription

---

## 📦 Tech Stack

- **Backend**: FastAPI + Python
- **LLM**: OpenAI GPT-4
- **Authentication**: JWT
- **Voice Support**: Web Speech API (dev) / Whisper (planned)

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

### 4. Create a .env file

### 5. Run the app
uvicorn app.main:app --reload

---

App runs at: http://localhost:8000
Swagger docs: http://localhost:8000/docs 

---


🧑 Author
Built with ❤️ by @Kalyan
---





