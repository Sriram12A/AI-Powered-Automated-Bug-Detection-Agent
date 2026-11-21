"""Pytest configuration and global fixtures."""

import pytest
from pathlib import Path
from setup_sample_repo import setup_vulnerable_sample_repo

@pytest.fixture(scope="session", autouse=True)
def ensure_sample_repo():
    """Ensure the sample vulnerable repository exists and has valid commits."""
    sample_dir = Path(__file__).resolve().parent.parent / "sample_repos" / "vulnerable_app"
    if not (sample_dir / ".git").exists():
        setup_vulnerable_sample_repo()
