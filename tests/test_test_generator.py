"""Unit tests for TestGenerator and TestExecutor."""

import pytest
from test_generator import TestGenerator
from test_executor import TestExecutor
from llm_provider import MockLLMProvider

def test_test_generation_reproduction():
    generator = TestGenerator(MockLLMProvider())
    issue = {
        "id": "iss_123",
        "title": "IndexError (Off-By-One Boundary Error in Loop Range)",
        "category": "BOUNDARY_CONDITION",
        "code_snippet": "for i in range(len(items) + 1):",
        "description": "Loop exceeds bounds"
    }
    code = "def process_items(items):\n    return [items[i] for i in range(len(items) + 1)]"
    
    test_record = generator.generate_reproduction_test("data_processor.py", issue, code, "run_test_gen")
    assert test_record["issue_id"] == "iss_123"
    assert "test_reproduce_" in test_record["file_path"]
    assert "assert" in test_record["test_code"]
    assert "pytest" in test_record["test_code"]

def test_test_executor_isolated_pass():
    executor = TestExecutor(timeout_seconds=10)
    source_files = {
        "calculator.py": "def add(a, b):\n    return a + b\n"
    }
    test_code = """
import pytest
from calculator import add

def test_addition():
    assert add(2, 3) == 5
"""
    result = executor.run_test_in_sandbox(
        source_files=source_files,
        test_file_name="test_calc.py",
        test_code=test_code
    )
    
    assert result["execution_status"] == "PASSED"
    assert result["exit_code"] == 0
    assert result["duration_sec"] > 0

def test_test_executor_isolated_failure():
    executor = TestExecutor(timeout_seconds=10)
    source_files = {
        "faulty.py": "def broken():\n    raise IndexError('list index out of range')\n"
    }
    test_code = """
import pytest
from faulty import broken

def test_should_fail():
    broken()
"""
    result = executor.run_test_in_sandbox(
        source_files=source_files,
        test_file_name="test_broken.py",
        test_code=test_code
    )
    
    assert result["execution_status"] == "FAILED"
    assert result["exit_code"] == 1
    assert "IndexError" in result["failure_reason"] or "FAILED" in result["stdout"]

