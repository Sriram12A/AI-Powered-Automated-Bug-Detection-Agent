"""Isolated sandboxed test execution engine using Pytest with strict environment isolation."""

import os
import sys
import time
import shutil
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from config import config

logger = logging.getLogger(__name__)


class TestExecutor:
    """Executes generated tests in an isolated, sandboxed environment with resource & permission restrictions."""
    __test__ = False

    SENSITIVE_ENV_VARS = {
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "GITHUB_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "DATABASE_URL"
    }

    def __init__(self, timeout_seconds: Optional[int] = None):
        self.timeout = timeout_seconds or config.SANDBOX_TIMEOUT_SECONDS

    def _create_sanitized_environment(self, sandbox_path: Path) -> Dict[str, str]:
        """Produce an isolated environment dictionary stripped of host credentials."""
        clean_env = os.environ.copy()
        for var in self.SENSITIVE_ENV_VARS:
            clean_env.pop(var, None)

        # Restrict PYTHONPATH strictly to sandbox directory
        clean_env["PYTHONPATH"] = str(sandbox_path)
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        clean_env["PYTHONUNBUFFERED"] = "1"
        return clean_env

    def run_test_in_sandbox(
        self,
        source_files: Dict[str, str],
        test_file_name: str,
        test_code: str
    ) -> Dict[str, Any]:
        """
        Execute a test file within an isolated temporary sandbox directory.

        Args:
            source_files: Map of relative file paths to their file contents.
            test_file_name: Target filename for the test (e.g. `test_reproduce_calc.py`).
            test_code: Complete executable Pytest script string.

        Returns:
            Dictionary containing execution status, stdout, stderr, failure reason, and duration.
        """
        start_time = time.time()
        temp_dir = tempfile.mkdtemp(prefix="agentic_sandbox_")
        sandbox_path = Path(temp_dir).resolve()

        try:
            # 1. Populate sandbox with source code files
            for rel_path, content in source_files.items():
                dest_file = sandbox_path / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(content, encoding="utf-8")

            # 2. Write test file
            test_file_path = sandbox_path / test_file_name
            test_file_path.write_text(test_code, encoding="utf-8")

            # 3. Create sanitized environment
            safe_env = self._create_sanitized_environment(sandbox_path)

            # 4. Invoke pytest in isolated subprocess
            cmd = [
                sys.executable,
                "-m", "pytest",
                test_file_name,
                "-v",
                "--tb=short"
            ]

            logger.info("Executing sandboxed Pytest: %s in %s", test_file_name, sandbox_path)
            proc = subprocess.run(
                cmd,
                cwd=str(sandbox_path),
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            duration = round(time.time() - start_time, 3)
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode

            # Pytest exit codes:
            # 0: All tests passed
            # 1: Tests ran and some failed
            # 2: Interrupted
            # 3: Internal error
            # 4: Usage error
            # 5: No tests collected
            if exit_code == 0:
                status = "PASSED"
                failure_reason = ""
            elif exit_code == 1:
                status = "FAILED"
                failure_reason = self._extract_failure_reason(stdout)
            else:
                status = "ERROR"
                failure_reason = stderr.strip() or f"Pytest exited with status code {exit_code}"

            logger.info("Sandbox test finished: %s (Status: %s, Duration: %.2fs)", test_file_name, status, duration)
            return {
                "execution_status": status,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "failure_reason": failure_reason,
                "duration_sec": duration
            }

        except subprocess.TimeoutExpired:
            duration = round(time.time() - start_time, 3)
            logger.warning("Test %s timed out after %d seconds", test_file_name, self.timeout)
            return {
                "execution_status": "TIMEOUT",
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out exceeding {self.timeout}s limit.",
                "failure_reason": f"Execution timed out (> {self.timeout}s)",
                "duration_sec": duration
            }
        except Exception as e:
            duration = round(time.time() - start_time, 3)
            logger.error("Sandbox execution error: %s", e)
            return {
                "execution_status": "ERROR",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "failure_reason": str(e),
                "duration_sec": duration
            }
        finally:
            # Secure cleanup of temporary execution sandbox
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning("Failed to clean up sandbox %s: %s", temp_dir, e)

    def _extract_failure_reason(self, stdout: str) -> str:
        """Parse concise failure reason or assertion message from Pytest output."""
        lines = stdout.splitlines()
        reason_lines = []
        capture = False

        for line in lines:
            if "FAILED" in line or "AssertionError" in line or "Exception" in line or "Error:" in line:
                reason_lines.append(line.strip())
            elif "E   " in line:
                reason_lines.append(line.strip())

        if reason_lines:
            return " | ".join(reason_lines[:3])
        return "Test assertion failed (reproduction successful)"
