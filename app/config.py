import os
from pathlib import Path
from typing import Dict, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):

    # OpenAI Configuration
    OPENAI_API_KEY: str

    # GitLab Configuration
    GITLAB_URL: str = "http://192.168.2.201"
    GITLAB_TOKEN: str
    GITLAB_WEBHOOK_SECRET: str

    # Redmine Configuration
    REDMINE_URL: str = "http://192.168.2.201:3000"
    REDMINE_API_KEY: str

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    PROJECT_MAPPING: Dict[str, str] = Field(default_factory=dict)
    REDMINE_PROJECT_SUFFIX: str = "::AI"

    # Ignored file patterns for diff filtering
    IGNORED_PATTERNS: List[str] = Field(default_factory=lambda: [
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        "Pipfile.lock",
        "*.min.js",
        "*.min.css",
        "dist/*",
        "build/*",
        "node_modules/*",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.svg",
        "*.ico",
        "*.woff",
        "*.woff2",
        "*.ttf",
        "*.eot",
    ])

    # Diff size limits
    MAX_DIFF_LINES: int = 500  # Full diff까지 허용하는 최대 라인 수
    MAX_SUMMARY_LINES: int = 2000  # Summary로 처리하는 최대 라인 수

    # LLM optimization
    MAX_ISSUES_FOR_LLM: int = 15  # LLM에게 전달할 최대 issue 개수

    # Redmine status IDs (일반적인 값, 실제 환경에 맞게 조정 필요)
    REDMINE_STATUS_IN_PROGRESS: int = 2  # 진행중
    REDMINE_STATUS_RESOLVED: int = 3  # 해결

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create logs directory if not exists
LOGS_DIR.mkdir(exist_ok=True)
