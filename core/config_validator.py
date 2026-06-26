import os

REQUIRED_ENV_VARS = {
    "GROQ_API_KEY": "Groq API key for LLM classification",
    "GEMINI_API_KEY": "Google Gemini API key for fallback classification",
    "JWT_SECRET_KEY": "Secret key for JWT token signing",
}

OPTIONAL_ENV_VARS = {
    "GROQ_MODEL": "llama-3.1-8b-instant",
    "GEMINI_MODEL": "gemini-2.0-flash",
    "BATCH_SIZE": "15",
    "MAX_REVIEWS": "2000",
    "SESSION_TTL_HOURS": "48",
}


def validate_config() -> dict:
    missing = []
    warnings = []

    for key, description in REQUIRED_ENV_VARS.items():
        value = os.environ.get(key, "").strip()
        if not value:
            missing.append(f"{key} — {description}")
        elif len(value) < 10:
            warnings.append(f"{key} looks too short — verify it is correct")

    if missing:
        raise EnvironmentError(
            "FeedbackIQ cannot start. Missing required environment variables:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nAdd these to your .env file and restart."
        )

    for key, default in OPTIONAL_ENV_VARS.items():
        if not os.environ.get(key):
            os.environ[key] = default

    return {
        "status": "ok",
        "required_vars": list(REQUIRED_ENV_VARS.keys()),
        "warnings": warnings,
    }
