import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"
BATCH_SIZE = 15
MAX_REVIEWS = 100
MIN_REVIEWS = 5
MAX_REVIEW_LENGTH = 1000
MIN_REVIEW_LENGTH = 3

# ── Auth configuration ──────────────────────────────
import secrets as _secrets
JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY", _secrets.token_hex(32)
)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7   # 7 days
REFRESH_TOKEN_EXPIRE_DAYS = 30
