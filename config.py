"""
=============================================================================
Project       : Cloud SRE-NEXUS (Autonomous Cloud Operations & Architecture Copilot)
File Path     : cloud_sre_nexus/config.py
File Name     : config.py
Description   : 중앙 환경 변수 및 멀티클라우드 MCP 설정 로더 모듈 (.env, st.secrets, os.environ)
Last Modified : 2026-10-23 15:30:00 KST (Asia/Seoul)
Version       : v1.5.0 (RAG 1단계 동적 PDF/TXT 문서 인덱싱 및 가이드 탑재)
Author/Owner  : Cloud SRE Team
=============================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=False)
else:
    load_dotenv(override=False)

def _get_raw(key: str, default=None):
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
    PROJECT_NAME: str = _get_str("PROJECT_NAME", "Cloud SRE-NEXUS")
    APP_ENV: str = _get_str("APP_ENV", "production")
    APP_PORT: int = _get_int("APP_PORT", 8501)

    # Google 2026 공식 표준 모델
    GEMINI_API_KEY: str = _get_str("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = _get_str("GEMINI_MODEL", "gemini-3.8-flash")
    GEMINI_TEMPERATURE: float = _get_float("GEMINI_TEMPERATURE", 0.2)
    GEMINI_TIMEOUT_SECONDS: int = _get_int("GEMINI_TIMEOUT_SECONDS", 30)

    # 운영 인프라 MCP (Mock / Live Azure)
    INFRA_SOURCE_TYPE: str = _get_str("INFRA_SOURCE_TYPE", "mock").lower()
    INFRA_JSON_PATH: str = _get_str("INFRA_JSON_PATH", "my_infra.json")
    AZURE_MCP_ENDPOINT: str = _get_str("AZURE_MCP_ENDPOINT", "http://localhost:8000/sse")

    # 멀티클라우드 MCP 확장 (AWS / GCP)
    ENABLE_MULTICLOUD: bool = _get_bool("ENABLE_MULTICLOUD", False)
    AWS_MCP_ENDPOINT: str = _get_str("AWS_MCP_ENDPOINT", "http://localhost:8001/sse")
    GCP_MCP_ENDPOINT: str = _get_str("GCP_MCP_ENDPOINT", "http://localhost:8002/sse")

    # 공식 지식 프로바이더 (MS Learn)
    MS_LEARN_SEARCH_LIMIT: int = _get_int("MS_LEARN_SEARCH_LIMIT", 3)
    MS_LEARN_TIMEOUT_SECONDS: int = _get_int("MS_LEARN_TIMEOUT_SECONDS", 10)

    # 서드파티 RAG
    ENABLE_THIRD_PARTY_RAG: bool = _get_bool("ENABLE_THIRD_PARTY_RAG", True)

    # 알림 채널
    SLACK_WEBHOOK_URL: str = _get_str("SLACK_WEBHOOK_URL", "")
    TELEGRAM_BOT_TOKEN: str = _get_str("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = _get_str("TELEGRAM_CHAT_ID", "")

    GAS_WEBHOOK_URL: str = _get_str("GAS_WEBHOOK_URL", "")

settings = Config()
