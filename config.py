"""
Cloud SRE-NEXUS - Centralized Configuration Module
===================================================
Loads environment variables from .env file or system environment.
Provides typed access, fallback defaults, and validation for all components.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent

# Automatically load .env file if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=False)
else:
    load_dotenv(override=False)

def _get_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "y", "on")

def _get_int(key: str, default: int = 8501) -> int:
    val = os.getenv(key)
    try:
        return int(val) if val is not None else default
    except ValueError:
        return default

def _get_float(key: str, default: float = 0.2) -> float:
    val = os.getenv(key)
    try:
        return float(val) if val is not None else default
    except ValueError:
        return default

class Config:
    # --- Project Metadata ---
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Cloud SRE-NEXUS")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = _get_int("APP_PORT", 8501)

    # --- LLM API Configuration (Google AI Studio Free Tier) ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_TEMPERATURE: float = _get_float("GEMINI_TEMPERATURE", 0.2)
    GEMINI_TIMEOUT_SECONDS: int = _get_int("GEMINI_TIMEOUT_SECONDS", 30)

    # --- Provider 1: Infrastructure Provider (Operations MCP) ---
    INFRA_SOURCE_TYPE: str = os.getenv("INFRA_SOURCE_TYPE", "mock").lower()  # "mock" | "live"
    INFRA_JSON_PATH: str = os.getenv("INFRA_JSON_PATH", "my_infra.json")
    AZURE_MCP_ENDPOINT: str = os.getenv("AZURE_MCP_ENDPOINT", "http://localhost:8000/sse")

    # --- Provider 2: Official Knowledge Provider (Learning MCP) ---
    ENABLE_MULTICLOUD: bool = _get_bool("ENABLE_MULTICLOUD", False)
    MS_LEARN_SEARCH_LIMIT: int = _get_int("MS_LEARN_SEARCH_LIMIT", 3)
    MS_LEARN_TIMEOUT_SECONDS: int = _get_int("MS_LEARN_TIMEOUT_SECONDS", 10)

    # --- Provider 3: Third-Party & Internal RAG Provider ---
    ENABLE_THIRD_PARTY_RAG: bool = _get_bool("ENABLE_THIRD_PARTY_RAG", True)

    # --- Notification Dispatchers (Alert Channels) ---
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # --- Event Webhook Integration ---
    GAS_WEBHOOK_URL: str = os.getenv("GAS_WEBHOOK_URL", "")

# Global Singleton Instance
settings = Config()