import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-fallback")
DEBUG = os.getenv("DEBUG", "False") == "True"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
