"""Unit tests for the Database layer."""

import pytest
from pathlib import Path
from database import Database

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_detector.db"
    return Database(db_path=db_file)

def test_run_lifecycle(test_db):
    run_id = "test_run_123"
    test_db.create_run(run_id, "my_repo", "/path/to/repo", "abc1234", "main", shadow_mode=True)
    
    run = test_db.get_run(run_id)
    assert run is not None
    assert run["repo_name"] == "my_repo"
    assert run["status"] == "RUNNING"
    assert run["shadow_mode"] == 1

    test_db.update_run(run_id, status="COMPLETED", total_bugs=3, confirmed_bugs=2)
    updated = test_db.get_run(run_id)
    assert updated["status"] == "COMPLETED"
    assert updated["total_bugs"] == 3
    assert updated["confirmed_bugs"] == 2

def test_issue_operations(test_db):
    run_id = "run_abc"
    test_db.create_run(run_id, "demo", "/demo")
    
    issue_data = {
        "id": "iss_1",
        "run_id": run_id,
        "file_path": "auth.py",
        "line_number": 15,
        "category": "SECURITY",
        "severity": "CRITICAL",
        "confidence": "HIGH",
        "title": "SQL Injection",
        "description": "Raw input in SQL",
        "code_snippet": "f'SELECT * FROM users'",
        "suggested_fix": "use parameterized query",
        "status": "SUSPECTED"
    }
    
    test_db.add_issue(issue_data)
    issues = test_db.get_issues_by_run(run_id)
    assert len(issues) == 1
    assert issues[0]["title"] == "SQL Injection"
    assert issues[0]["severity"] == "CRITICAL"

    test_db.update_issue_status("iss_1", "CONFIRMED", "https://github.com/org/repo/issues/42")
    issues = test_db.get_issues_by_run(run_id)
    assert issues[0]["status"] == "CONFIRMED"
    assert issues[0]["github_issue_url"] == "https://github.com/org/repo/issues/42"

def test_metrics_summary(test_db):
    run_id = "run_metrics"
    test_db.create_run(run_id, "demo", "/demo")
    test_db.add_issue({
        "id": "iss_m1",
        "run_id": run_id,
        "file_path": "a.py",
        "category": "SECURITY",
        "severity": "HIGH",
        "title": "Bug A",
        "status": "CONFIRMED"
    })
    test_db.add_test({
        "id": "test_m1",
        "run_id": run_id,
        "test_name": "test_bug_a",
        "file_path": "test_a.py",
        "test_code": "assert True",
        "execution_status": "PASSED"
    })
    
    metrics = test_db.get_metrics_summary()
    assert metrics["total_runs"] == 1
    assert metrics["total_bugs_detected"] == 1
    assert metrics["confirmed_bugs"] == 1
    assert metrics["test_pass_rate"] == 100.0

