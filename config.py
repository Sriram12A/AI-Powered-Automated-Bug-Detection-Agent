"""Configuration manager for the AI-Powered Automated Bug Detection Agent."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration parameters."""

    # Project Root
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent)

    # Database
    DATABASE_PATH: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "bug_detector.db"
    )

    # LLM Settings
    # Supported providers: "gemini", "openai", "mock" (offline demo mode)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # GitHub Settings
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    GITHUB_API_BASE: str = os.getenv("GITHUB_API_BASE", "https://api.github.com")

    # Sandbox & Execution Settings
    SANDBOX_TIMEOUT_SECONDS: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "15"))
    SHADOW_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / ".shadow_workspace"
    )
    REPORTS_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "reports"
    )

    # Agent Behavior
    MAX_ITERATIONS: int = int(os.getenv("AGENT_MAX_ITERATIONS", "3"))
    AUTO_GENERATE_TESTS: bool = os.getenv("AUTO_GENERATE_TESTS", "true").lower() == "true"
    AUTO_VERIFY_FIX: bool = os.getenv("AUTO_VERIFY_FIX", "true").lower() == "true"

    def __post_init__(self):
        """Ensure necessary directories exist."""
        self.SHADOW_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# Global configuration instance
config = Config()

