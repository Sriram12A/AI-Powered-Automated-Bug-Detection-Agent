"""Unit tests for AIReviewer and MockLLMProvider."""

import pytest
from ai_reviewer import AIReviewer
from llm_provider import MockLLMProvider

def test_mock_reviewer_sql_injection():
    provider = MockLLMProvider()
    reviewer = AIReviewer(provider)
    
    code = """
def execute_query(user_id):
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    cursor.execute(query)
"""
    diff = "+ query = f\"SELECT * FROM users WHERE id = '{user_id}'\""
    issues = reviewer.review_file_changes("db.py", diff, code, "run_test")
    
    assert len(issues) >= 1
    sql_issues = [i for i in issues if i["category"] == "SECURITY"]
    assert len(sql_issues) == 1
    assert "SQL Injection" in sql_issues[0]["title"]
    assert sql_issues[0]["severity"] == "CRITICAL"

def test_mock_reviewer_boundary_condition():
    provider = MockLLMProvider()
    reviewer = AIReviewer(provider)
    
    code = """
def process(items):
    for i in range(len(items) + 1):
        print(items[i])
"""
    diff = "+ for i in range(len(items) + 1):"
    issues = reviewer.review_file_changes("items.py", diff, code, "run_test")
    
    boundary_issues = [i for i in issues if i["category"] == "BOUNDARY_CONDITION"]
    assert len(boundary_issues) == 1
    assert "Off-By-One" in boundary_issues[0]["title"] or "IndexError" in boundary_issues[0]["title"]

def test_generate_fix():
    provider = MockLLMProvider()
    reviewer = AIReviewer(provider)
    
    code = "for i in range(len(items) + 1):\n    print(items[i])"
    issue = {
        "title": "IndexError",
        "code_snippet": "for i in range(len(items) + 1):",
        "suggested_fix": "for i in range(len(items)):"
    }
    
    fix_data = reviewer.generate_fix("items.py", issue, code)
    assert "fixed_snippet" in fix_data
    assert "for i in range(len(items)):" in fix_data["full_fixed_file"]

