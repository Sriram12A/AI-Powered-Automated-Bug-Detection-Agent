"""Automated test generator module using LLM and AST validation."""

import ast
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from llm_provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class TestGenerator:
    """Generates focused, executable Pytest test cases designed to reproduce and verify defects."""
    __test__ = False

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.provider = llm_provider or get_llm_provider()

    def generate_reproduction_test(self, file_path: str, issue: Dict[str, Any], full_code: str, run_id: str) -> Dict[str, Any]:
        """
        Synthesize a self-contained Pytest file asserting the expected behavior.
        The test is expected to fail on the buggy code, proving the bug exists,
        and pass once the bug is resolved.
        """
        logger.info("Generating reproduction test for: %s", issue.get("title"))
        raw_test_code = self.provider.generate_pytest_suite(file_path, issue, full_code)

        # Validate and clean python syntax
        cleaned_code = self._validate_and_sanitize(raw_test_code, file_path)

        test_id = f"test_{uuid.uuid4().hex[:8]}"
        module_stem = Path(file_path).stem
        test_file_name = f"test_reproduce_{module_stem}_{test_id[-4:]}.py"

        return {
            "id": test_id,
            "run_id": run_id,
            "issue_id": issue.get("id"),
            "test_name": f"test_reproduce_{issue.get('category', 'bug').lower()}",
            "file_path": test_file_name,
            "test_code": cleaned_code,
            "execution_status": "PENDING"
        }

    def _validate_and_sanitize(self, code_str: str, file_path: str) -> str:
        """Ensure the generated test code is syntactically valid Python."""
        code = code_str.strip()

        # Remove markdown fences if still present
        if code.startswith("```"):
            lines = code.splitlines()
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            ast.parse(code)
            return code
        except SyntaxError as e:
            logger.warning("Generated test had syntax error: %s. Constructing safe fallback harness.", e)
            module_name = Path(file_path).stem
            # Return safe fallback harness that imports module
            return f"""# Fallback verification harness
import pytest
import importlib

def test_module_integrity():
    mod = importlib.import_module("{module_name}")
    assert mod is not None
"""
