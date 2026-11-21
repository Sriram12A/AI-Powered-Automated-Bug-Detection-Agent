"""Unit tests for GitAnalyzer."""

import pytest
from pathlib import Path
from git_analyzer import GitAnalyzer

SAMPLE_REPO_PATH = Path(__file__).resolve().parent.parent / "sample_repos" / "vulnerable_app"

def test_git_analyzer_info():
    analyzer = GitAnalyzer(str(SAMPLE_REPO_PATH), shadow_mode=False)
    info = analyzer.get_repo_info()
    assert info["repo_name"] == "vulnerable_app"
    assert "commit_hash" in info
    assert info["commit_hash"] is not None

def test_git_analyzer_commits_list():
    analyzer = GitAnalyzer(str(SAMPLE_REPO_PATH), shadow_mode=False)
    commits = analyzer.list_recent_commits(5)
    assert len(commits) >= 2
    assert "hash" in commits[0]
    assert "message" in commits[0]

def test_git_analyzer_diff_extraction():
    analyzer = GitAnalyzer(str(SAMPLE_REPO_PATH), shadow_mode=False)
    commits = analyzer.list_recent_commits(5)
    head_hash = commits[0]["hash"]
    
    diffs = analyzer.analyze_commit_diff(head_hash)
    assert isinstance(diffs, list)
    assert len(diffs) > 0
    assert diffs[0]["file_path"].endswith(".py")
    assert "diff_text" in diffs[0]
    assert "full_content" in diffs[0]

def test_shadow_workspace_creation(tmp_path):
    analyzer = GitAnalyzer(str(SAMPLE_REPO_PATH), shadow_mode=True, run_id="test_shadow_run")
    assert analyzer.work_dir != analyzer.original_path
    assert analyzer.work_dir.exists()
    assert (analyzer.work_dir / ".git").exists()
    analyzer.cleanup()

