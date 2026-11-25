"""Shared configuration — single source of truth for all three projects.

Every secret is read from environment variables (see ../.env.example). Nothing
is hardcoded. Copy ../.env.example to ../.env and fill in real values locally.
"""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads a sibling .env if present
except Exception:  # python-dotenv optional
    pass


# --- MySQL -----------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")

# --- Qdrant ----------------------------------------------------------------
QDRANT_URL = os.getenv("URL_LINK", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# --- LLM providers ---------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

# --- SMTP ------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.yandex.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_LOGIN = os.getenv("SMTP_LOGIN", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# --- Netgsm ----------------------------------------------------------------
NETGSM_USERCODE = os.getenv("NETGSM_USERCODE", "")
NETGSM_PASSWORD = os.getenv("NETGSM_PASSWORD", "")


def db_config() -> dict:
    """mysql.connector / PyMySQL style connection kwargs."""
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
    }
