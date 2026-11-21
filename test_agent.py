"""
Unit Tests for BugDetectionAgent
"""

import pytest
from agent import BugDetectionAgent

SAMPLE_CODE = '''import sqlite3

def execute_user_query(username: str):
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER, username TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'admin')")
    cursor.execute("INSERT INTO users VALUES (2, 'guest')")
    conn.commit()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()

def process_items(items):
    out = []
    for i in range(len(items) + 1):
        out.append(items[i].upper())
    return out

def calculate_average(nums):
    total = sum(nums)
    count = len(nums)
    return total / count
'''

def test_detect_defects():
    agent = BugDetectionAgent(provider="mock")
    issues = agent.analyze_code(SAMPLE_CODE, "sample.py")
    assert len(issues) == 3
    titles = [i["title"] for i in issues]
    assert any("SQL Injection" in t for t in titles)
    assert any("IndexError" in t or "Off-by-One" in t for t in titles)
    assert any("ZeroDivision" in t for t in titles)

def test_sandbox_test_execution():
    agent = BugDetectionAgent(provider="mock")
    # Clean test should pass
    clean_code = "def add(a, b):\n    return a + b\n"
    test_code = "from sample import add\ndef test_add():\n    assert add(2, 2) == 4\n"
    res = agent.execute_test_in_sandbox(clean_code, test_code, "sample.py")
    assert res["status"] == "PASSED"

def test_full_agent_pipeline():
    agent = BugDetectionAgent(provider="mock")
    res = agent.run_pipeline(SAMPLE_CODE, "vulnerable_sample.py")
    assert res["total_bugs"] == 3
    assert res["confirmed_bugs"] == 3
    assert res["fixed_bugs"] == 3
    assert len(res["results"]) == 3
