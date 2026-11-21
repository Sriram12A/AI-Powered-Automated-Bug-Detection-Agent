"""Unit tests for the autonomous BugDetectionAgent and ReportGenerator."""

import pytest
from pathlib import Path
from agent import BugDetectionAgent
from report_generator import ReportGenerator

SAMPLE_REPO = Path(__file__).resolve().parent.parent / "sample_repos" / "vulnerable_app"

def test_full_agentic_workflow_execution():
    agent = BugDetectionAgent(
        llm_provider_name="mock",
        shadow_mode=True,
        auto_verify=True
    )
    
    result = agent.run(repo_path=str(SAMPLE_REPO))
    
    assert result["status"] == "COMPLETED"
    assert "run_id" in result
    assert result["total_bugs"] >= 1
    assert "execution_time_sec" in result
    assert "reports" in result
    assert Path(result["reports"]["markdown"]).exists()
    assert Path(result["reports"]["html"]).exists()
    assert Path(result["reports"]["json"]).exists()

def test_report_generation(tmp_path):
    generator = ReportGenerator(reports_dir=tmp_path)
    run_meta = {
        "id": "run_rep_test",
        "repo_name": "demo_repo",
        "created_at": "2026-11-21 10:00:00",
        "status": "COMPLETED",
        "total_bugs": 2,
        "confirmed_bugs": 1,
        "test_pass_rate": 50.0,
        "execution_time_sec": 3.2
    }
    issues = [
        {
            "id": "iss_1",
            "title": "SQL Injection",
            "file_path": "auth.py",
            "line_number": 10,
            "category": "SECURITY",
            "severity": "CRITICAL",
            "confidence": "HIGH",
            "status": "CONFIRMED",
            "description": "SQL vulnerability",
            "code_snippet": "query = ...",
            "suggested_fix": "use params"
        }
    ]
    tests = [
        {
            "id": "t_1",
            "test_name": "test_sql",
            "file_path": "test_sql.py",
            "execution_status": "FAILED",
            "duration_sec": 0.4,
            "failure_reason": "SQL Injection succeeded",
            "test_code": "assert False"
        }
    ]
    
    md = generator.generate_markdown(run_meta, issues, tests)
    assert "# 🛡️ AI Bug Detection" in md
    assert "SQL Injection" in md
    assert "CRITICAL" in md
    
    html = generator.generate_html(run_meta, issues, tests)
    assert "<!DOCTYPE html>" in html
    assert "SQL Injection" in html
    
    js = generator.generate_json(run_meta, issues, tests)
    assert js["summary"]["total_bugs"] == 2

