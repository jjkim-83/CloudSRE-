"""
Cloud SRE-NEXUS - Centralized Configuration Module
===================================================
Loads environment variables from:
1. System environment variables (os.environ)
2. Local .env file (via python-dotenv)
3. Streamlit Cloud Secrets (st.secrets fallback)
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

def _get_raw(key: str, default=None):
    """Retrieve setting from os.getenv first, then st.secrets fallback."""
    val = os.getenv(key)
    if val is not None and str(val).strip() != "":
        return val
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            s_val = st.secrets[key]
            if s_val is not None and str(s_val).strip() != "":
                return s_val
    except Exception:
        pass
    return default

def _get_str(key: str, default: str = "") -> str:
    val = _get_raw(key, default)
    return str(val).strip() if val is not None else default

def _get_bool(key: str, default: bool = False) -> bool:
    val = _get_raw(key, default)
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() in ("true", "1", "yes", "y", "on")

def _get_int(key: str, default: int = 8501) -> int:
    val = _get_raw(key, default)
    try:
        return int(val) if val is not None else default
    except ValueError:
        return default

def _get_float(key: str, default: float = 0.2) -> float:
    val = _get_raw(key, default)
    try:
        return float(val) if val is not None else default
    except ValueError:
        return default

class Config:
    # --- Project Metadata ---
    PROJECT_NAME: str = _get_str("PROJECT_NAME", "Cloud SRE-NEXUS")
    APP_ENV: str = _get_str("APP_ENV", "production")
    APP_PORT: int = _get_int("APP_PORT", 8501)

    # --- LLM API Configuration (Google AI Studio Free Tier) ---
    GEMINI_API_KEY: str = _get_str("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = _get_str("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_TEMPERATURE: float = _get_float("GEMINI_TEMPERATURE", 0.2)
    GEMINI_TIMEOUT_SECONDS: int = _get_int("GEMINI_TIMEOUT_SECONDS", 30)

    # --- Provider 1: Infrastructure Provider (Operations MCP) ---
    INFRA_SOURCE_TYPE: str = _get_str("INFRA_SOURCE_TYPE", "mock").lower()  # "mock" | "live"
    INFRA_JSON_PATH: str = _get_str("INFRA_JSON_PATH", "my_infra.json")
    AZURE_MCP_ENDPOINT: str = _get_str("AZURE_MCP_ENDPOINT", "http://localhost:8000/sse")

    # --- Provider 2: Official Knowledge Provider (Learning MCP) ---
    ENABLE_MULTICLOUD: bool = _get_bool("ENABLE_MULTICLOUD", False)
    MS_LEARN_SEARCH_LIMIT: int = _get_int("MS_LEARN_SEARCH_LIMIT", 3)
    MS_LEARN_TIMEOUT_SECONDS: int = _get_int("MS_LEARN_TIMEOUT_SECONDS", 10)

    # --- Provider 3: Third-Party & Internal RAG Provider ---
    ENABLE_THIRD_PARTY_RAG: bool = _get_bool("ENABLE_THIRD_PARTY_RAG", True)

    # --- Notification Dispatchers (Alert Channels) ---
    SLACK_WEBHOOK_URL: str = _get_str("SLACK_WEBHOOK_URL", "")
    TELEGRAM_BOT_TOKEN: str = _get_str("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = _get_str("TELEGRAM_CHAT_ID", "")

    # --- Event Webhook Integration ---
    GAS_WEBHOOK_URL: str = _get_str("GAS_WEBHOOK_URL", "")

# Global Singleton Instance
settings = Config()
