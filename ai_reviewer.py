"""AI-powered code reviewer module for bug detection, security, and logic analysis."""

import uuid
import logging
from typing import Dict, List, Any, Optional
from llm_provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class AIReviewer:
    """Orchestrates LLM-based static and semantic analysis of code changes."""

    VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    VALID_CONFIDENCES = {"HIGH", "MEDIUM", "LOW"}
    VALID_CATEGORIES = {
        "SECURITY",
        "LOGICAL_ERROR",
        "RESOURCE_LEAK",
        "BOUNDARY_CONDITION",
        "PERFORMANCE"
    }

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.provider = llm_provider or get_llm_provider()

    def review_file_changes(self, file_path: str, diff_text: str, full_code: str, run_id: str) -> List[Dict[str, Any]]:
        """
        Analyze code diff and full file context with the LLM to identify defects.
        Returns a list of structured, validated issue records.
        """
        logger.info("Initiating AI code review on: %s", file_path)
        try:
            raw_issues = self.provider.review_code_diff(file_path, diff_text, full_code)
        except Exception as e:
            logger.error("AI review exception for %s: %s", file_path, e)
            raw_issues = []

        validated_issues = []
        for raw in raw_issues:
            issue_id = f"issue_{uuid.uuid4().hex[:8]}"

            # Normalize severity and category
            severity = str(raw.get("severity", "MEDIUM")).upper()
            if severity not in self.VALID_SEVERITIES:
                severity = "MEDIUM"

            confidence = str(raw.get("confidence", "HIGH")).upper()
            if confidence not in self.VALID_CONFIDENCES:
                confidence = "HIGH"

            category = str(raw.get("category", "LOGICAL_ERROR")).upper()
            if category not in self.VALID_CATEGORIES:
                category = "LOGICAL_ERROR"

            validated = {
                "id": issue_id,
                "run_id": run_id,
                "file_path": file_path,
                "line_number": int(raw.get("line_number", 1)),
                "title": raw.get("title", "Detected Code Defect").strip(),
                "description": raw.get("description", "").strip(),
                "category": category,
                "severity": severity,
                "confidence": confidence,
                "code_snippet": raw.get("code_snippet", "").strip(),
                "suggested_fix": raw.get("suggested_fix", "").strip(),
                "status": "SUSPECTED",
                "github_issue_url": None
            }
            validated_issues.append(validated)

        logger.info("Found %d candidate issues in %s", len(validated_issues), file_path)
        return validated_issues

    def generate_fix(self, file_path: str, issue: Dict[str, Any], full_code: str) -> Dict[str, Any]:
        """Request a complete, syntactically correct code fix from the LLM."""
        try:
            return self.provider.suggest_fix(file_path, issue, full_code)
        except Exception as e:
            logger.error("Fix generation failed for %s: %s", issue.get("title"), e)
            return {
                "explanation": "Default automated fix",
                "fixed_snippet": issue.get("suggested_fix", ""),
                "full_fixed_file": full_code
            }

