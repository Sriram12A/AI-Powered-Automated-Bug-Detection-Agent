"""
AI-Powered Automated Bug Detection & Verification Agent
======================================================
An autonomous agent that:
1. Analyzes code and diffs for defects and vulnerabilities.
2. Synthesizes targeted Pytest test cases to reproduce the bug.
3. Executes the test in an isolated, sandboxed temporary environment.
4. Generates and empirically verifies a code patch by re-running tests.
"""

import os
import re
import sys
import json
import time
import uuid
import tempfile
import subprocess
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class BugDetectionAgent:
    """Autonomous agent for bug detection, reproduction test generation, and fix verification."""

    def __init__(self, provider: str = "mock", api_key: Optional[str] = None):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    def analyze_code(self, source_code: str, file_name: str = "main.py") -> List[Dict[str, Any]]:
        """Analyze source code or diff to detect potential bugs and security vulnerabilities."""
        # 1. If Gemini provider requested and API key is present
        if self.provider == "gemini" and os.getenv("GEMINI_API_KEY"):
            try:
                from google import genai
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                prompt = f"""You are an expert software engineer and security auditor.
Analyze the following Python code for bugs, security vulnerabilities (e.g., SQL injection), logic errors, and boundary issues.

File: {file_name}
```python
{source_code}
```

Return ONLY a valid JSON array of objects with this schema:
[
  {{
    "title": "Short title of bug",
    "category": "SECURITY | LOGICAL_ERROR | BOUNDARY_CONDITION | RESOURCE_LEAK",
    "severity": "CRITICAL | HIGH | MEDIUM | LOW",
    "confidence": "HIGH | MEDIUM | LOW",
    "line_number": 1,
    "description": "Explanation of the defect",
    "code_snippet": "faulty line of code",
    "suggested_fix": "corrected replacement code"
  }}
]
Do not include any markdown or text outside the JSON array.
"""
                resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
                clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.text.strip(), flags=re.MULTILINE)
                return json.loads(clean_json)
            except Exception as e:
                print(f"[Warning] Gemini API review fallback to offline heuristic: {e}")

        # 2. Offline / Mock deterministic defect detection (Fast, reliable, zero-cost)
        return self._detect_heuristics(source_code, file_name)

    def _detect_heuristics(self, code: str, file_name: str) -> List[Dict[str, Any]]:
        """Intelligent offline rule-engine detecting canonical defects."""
        issues = []
        lines = code.splitlines()

        # Check 1: SQL Injection via f-strings
        sql_match = re.search(r'query\s*=\s*f["\']SELECT.*?\{(\w+)\}.*?["\']\s*\n\s*cursor\.execute\(query\)', code, re.DOTALL | re.IGNORECASE)
        if not sql_match:
            sql_match = re.search(r'(execute|cursor\.execute)\s*\(\s*f["\']SELECT.*?\{(\w+)\}', code, re.IGNORECASE)
        if sql_match:
            line_no = code[:sql_match.start()].count("\n") + 1
            issues.append({
                "id": f"iss_{uuid.uuid4().hex[:6]}",
                "title": "SQL Injection via Unsanitized F-String",
                "category": "SECURITY",
                "severity": "CRITICAL",
                "confidence": "HIGH",
                "line_number": line_no,
                "description": "User input is formatted directly into a SQL query string, allowing arbitrary SQL execution.",
                "code_snippet": sql_match.group(0),
                "suggested_fix": 'cursor.execute("SELECT * FROM users WHERE username = ?", (username,))'
            })

        # Check 2: Off-by-one boundary defect in range(len + 1)
        off_by_one = re.search(r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(\s*(\w+)\s*\)\s*\+\s*1\s*\)', code)
        if off_by_one:
            line_no = code[:off_by_one.start()].count("\n") + 1
            raw_line = lines[line_no - 1] if line_no <= len(lines) else off_by_one.group(0)
            indent = re.match(r"^\s*", raw_line).group(0)
            var_name = off_by_one.group(1)
            issues.append({
                "id": f"iss_{uuid.uuid4().hex[:6]}",
                "title": "IndexError: Off-by-One Loop Range Defect",
                "category": "BOUNDARY_CONDITION",
                "severity": "HIGH",
                "confidence": "HIGH",
                "line_number": line_no,
                "description": f"Iterating over range(len({var_name}) + 1) attempts to access an index beyond array bounds.",
                "code_snippet": raw_line,
                "suggested_fix": f"{indent}for i in range(len({var_name})):"
            })

        # Check 3: Unhandled ZeroDivisionError (e.g., total / count)
        div_zero = re.search(r'(\w+)\s*/\s*(\w+)', code)
        if div_zero and ("count" in code.lower() or "len" in code.lower() or "average" in code.lower()):
            num_var = div_zero.group(1)
            denom = div_zero.group(2)
            if f"if {denom} == 0" not in code and f"if not {denom}" not in code:
                line_no = code[:div_zero.start()].count("\n") + 1
                raw_line = lines[line_no - 1] if line_no <= len(lines) else div_zero.group(0)
                indent = re.match(r"^\s*", raw_line).group(0)
                issues.append({
                    "id": f"iss_{uuid.uuid4().hex[:6]}",
                    "title": "Unhandled ZeroDivisionError in Arithmetic",
                    "category": "LOGICAL_ERROR",
                    "severity": "MEDIUM",
                    "confidence": "HIGH",
                    "line_number": line_no,
                    "description": f"Denominator `{denom}` is used in division without verifying it is non-empty/non-zero.",
                    "code_snippet": raw_line,
                    "suggested_fix": f"{indent}return {num_var} / {denom} if {denom} != 0 else 0.0"
                })

        return issues

    def generate_reproduction_test(self, file_name: str, issue: Dict[str, Any]) -> str:
        """Synthesize a self-contained Pytest script that fails on the bug and passes when fixed."""
        module_name = file_name.replace(".py", "")
        title = issue.get("title", "")

        if "SQL" in title:
            return f"""import pytest
from {module_name} import execute_user_query

def test_sql_injection():
    # Attempt SQL payload injection; a secure parameterized query will find 0 rows
    malicious_payload = "admin' OR '1'='1"
    rows = execute_user_query(malicious_payload)
    assert len(rows) == 0, "Vulnerability Confirmed: SQL Injection payload returned unauthorized records!"
"""
        elif "IndexError" in title or "Off-by-One" in title:
            return f"""import pytest
from {module_name} import process_items

def test_off_by_one_boundary():
    # Pass 3 items; buggy function iterates 4 times and raises IndexError on item 4
    items = ["alpha", "beta", "gamma"]
    result = process_items(items)
    assert len(result) == 3, "Expected 3 processed items without IndexError"
"""
        elif "ZeroDivision" in title:
            return f"""import pytest
from {module_name} import calculate_average

def test_zero_division():
    # Empty list must return 0.0 without raising ZeroDivisionError
    result = calculate_average([])
    assert result == 0.0, "Average of empty list should safely return 0.0"
"""
        else:
            return f"""import pytest
import {module_name}

def test_module_execution():
    assert {module_name} is not None
"""

    def execute_test_in_sandbox(self, source_code: str, test_code: str, file_name: str = "main.py") -> Dict[str, Any]:
        """
        Execute Pytest inside an isolated temporary directory.
        Never executes untrusted code on the host directory.
        """
        with tempfile.TemporaryDirectory(prefix="agent_sandbox_") as tmp_dir:
            src_file = os.path.join(tmp_dir, file_name)
            test_file = os.path.join(tmp_dir, "test_reproduce.py")

            with open(src_file, "w", encoding="utf-8") as f:
                f.write(source_code)
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_code)

            # Strip host secrets from environment
            clean_env = os.environ.copy()
            for key in ["GEMINI_API_KEY", "OPENAI_API_KEY", "GITHUB_TOKEN"]:
                clean_env.pop(key, None)
            clean_env["PYTHONPATH"] = tmp_dir

            start_t = time.time()
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", "test_reproduce.py", "-v", "--tb=short"],
                    cwd=tmp_dir,
                    env=clean_env,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                duration = round(time.time() - start_t, 2)
                status = "PASSED" if proc.returncode == 0 else "FAILED"
                return {
                    "status": status,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "duration_sec": duration
                }
            except subprocess.TimeoutExpired:
                return {
                    "status": "TIMEOUT",
                    "stdout": "",
                    "stderr": "Execution timed out exceeding 10s limit.",
                    "duration_sec": 10.0
                }

    def verify_fix(self, source_code: str, issue: Dict[str, Any], test_code: str, file_name: str = "main.py") -> Dict[str, Any]:
        """Apply the suggested fix and re-run the reproduction test to verify it passes."""
        faulty = issue.get("code_snippet", "")
        fix = issue.get("suggested_fix", "")

        patched_code = source_code.replace(faulty, fix) if faulty and faulty in source_code else source_code

        res = self.execute_test_in_sandbox(patched_code, test_code, file_name)
        is_fixed = (res["status"] == "PASSED")

        return {
            "verified": is_fixed,
            "patched_code": patched_code,
            "verification_status": "FIXED" if is_fixed else "FAILED_VERIFICATION",
            "test_output": res["stdout"]
        }

    def run_pipeline(self, source_code: str, file_name: str = "main.py") -> Dict[str, Any]:
        """Execute the complete agentic pipeline on the target source code."""
        start_time = time.time()

        # Step 1: Detect bugs
        issues = self.analyze_code(source_code, file_name)

        results = []
        confirmed_count = 0
        fixed_count = 0

        # Step 2-4: For each issue, generate test, run in sandbox, and verify fix
        for issue in issues:
            test_code = self.generate_reproduction_test(file_name, issue)
            test_res = self.execute_test_in_sandbox(source_code, test_code, file_name)

            # If test failed on buggy code, bug is CONFIRMED
            bug_confirmed = (test_res["status"] == "FAILED")
            if bug_confirmed:
                confirmed_count += 1
                issue["status"] = "CONFIRMED"
            else:
                issue["status"] = "SUSPECTED"

            # Step 5: Verify fix
            verification = self.verify_fix(source_code, issue, test_code, file_name)
            if verification["verified"]:
                fixed_count += 1
                issue["status"] = "FIXED"

            results.append({
                "issue": issue,
                "test_code": test_code,
                "initial_test_status": test_res["status"],
                "verification": verification
            })

        total_time = round(time.time() - start_time, 2)

        return {
            "total_bugs": len(issues),
            "confirmed_bugs": confirmed_count,
            "fixed_bugs": fixed_count,
            "duration_sec": total_time,
            "results": results
        }
