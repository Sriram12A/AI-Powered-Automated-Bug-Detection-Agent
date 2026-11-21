"""Autonomous Agentic Bug Detection and Verification Engine."""

import os
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from config import config
from database import db
from git_analyzer import GitAnalyzer
from ai_reviewer import AIReviewer
from test_generator import TestGenerator
from test_executor import TestExecutor
from report_generator import report_generator
from github_integration import GitHubIntegration
from llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


class BugDetectionAgent:
    """
    Autonomous multi-stage agentic workflow:
    1. Shadow Workspace Setup -> 2. Git Diff Extraction -> 3. AI Code Review ->
    4. Pytest Generation -> 5. Sandboxed Test Execution -> 6. Fix Verification ->
    7. Metrics & Report Generation.
    """

    def __init__(
        self,
        llm_provider_name: Optional[str] = None,
        shadow_mode: bool = True,
        auto_verify: bool = True,
        on_progress: Optional[Callable[[str, str], None]] = None
    ):
        self.provider_name = llm_provider_name or config.LLM_PROVIDER
        self.llm_provider = get_llm_provider(self.provider_name)
        self.shadow_mode = shadow_mode
        self.auto_verify = auto_verify
        self.on_progress = on_progress or (lambda phase, msg: None)

        self.reviewer = AIReviewer(self.llm_provider)
        self.test_generator = TestGenerator(self.llm_provider)
        self.test_executor = TestExecutor()
        self.github = GitHubIntegration()

    def _notify(self, run_id: str, phase: str, message: str, level: str = "INFO"):
        """Emit telemetry to database, console logger, and user UI callback."""
        logger.info("[%s] [%s] %s", run_id, phase, message)
        db.log(run_id, phase, level, message)
        self.on_progress(phase, message)

    def run(
        self,
        repo_path: str,
        commit_hash: Optional[str] = None,
        sync_github_issues: bool = False,
        github_repo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete autonomous bug detection, reproduction, and verification pipeline.

        Args:
            repo_path: Path to target git repository.
            commit_hash: Specific commit hash to inspect (or latest changes if None).
            sync_github_issues: Whether to create GitHub issues for confirmed bugs.
            github_repo: Target GitHub repo formatted as "owner/repo".

        Returns:
            Dictionary containing run summary, detected issues, test telemetry, and metrics.
        """
        start_time = time.time()
        run_id = f"run_{uuid.uuid4().hex[:8]}"

        # Phase 1: Shadow Workspace Resolution
        self._notify(run_id, "INIT", f"Initializing Agentic Bug Detection run {run_id}")
        git_analyzer = None

        try:
            git_analyzer = GitAnalyzer(repo_path, shadow_mode=self.shadow_mode, run_id=run_id)
            repo_info = git_analyzer.get_repo_info()
            target_commit = commit_hash or repo_info.get("commit_hash", "HEAD")

            db.create_run(
                run_id=run_id,
                repo_name=repo_info.get("repo_name", "unknown_repo"),
                repo_path=str(repo_path),
                commit_hash=target_commit,
                branch_name=repo_info.get("branch", "main"),
                shadow_mode=self.shadow_mode
            )

            # Phase 2: Git Diff Analysis
            self._notify(run_id, "DIFF_ANALYSIS", f"Analyzing code changes for commit: {target_commit[:8] if target_commit else 'HEAD'}")
            changed_files = git_analyzer.analyze_commit_diff(commit_hash)

            if not changed_files:
                self._notify(run_id, "DIFF_ANALYSIS", "No Python code changes detected in target commit/workspace.")
                db.update_run(
                    run_id,
                    status="COMPLETED",
                    summary="No Python changes detected.",
                    execution_time_sec=round(time.time() - start_time, 2)
                )
                return {"run_id": run_id, "status": "COMPLETED", "issues": [], "tests": []}

            self._notify(run_id, "DIFF_ANALYSIS", f"Extracted {len(changed_files)} modified Python file(s).")

            # Phase 3: AI Code Review & Defect Identification
            all_detected_issues: List[Dict[str, Any]] = []
            source_file_cache: Dict[str, str] = {}

            for file_data in changed_files:
                rel_path = file_data["file_path"]
                diff_text = file_data["diff_text"]
                full_code = file_data["full_content"]
                source_file_cache[rel_path] = full_code

                self._notify(run_id, "AI_REVIEW", f"Conducting semantic AI code review on: {rel_path}")
                issues = self.reviewer.review_file_changes(rel_path, diff_text, full_code, run_id)

                for issue in issues:
                    db.add_issue(issue)
                    all_detected_issues.append(issue)

            self._notify(run_id, "AI_REVIEW", f"Identified {len(all_detected_issues)} potential defect(s).")

            # Phase 4 & 5: Automated Test Generation & Sandboxed Execution
            executed_tests: List[Dict[str, Any]] = []
            confirmed_bug_count = 0
            fixed_bug_count = 0

            for issue in all_detected_issues:
                rel_path = issue["file_path"]
                full_code = source_file_cache.get(rel_path, "")

                self._notify(run_id, "TEST_GEN", f"Synthesizing reproduction Pytest for: {issue['title']}")
                test_meta = self.test_generator.generate_reproduction_test(rel_path, issue, full_code, run_id)

                # Execute in isolated sandbox against the buggy code
                self._notify(run_id, "TEST_EXEC", f"Running sandboxed test: {test_meta['file_path']}")
                exec_result = self.test_executor.run_test_in_sandbox(
                    source_files=source_file_cache,
                    test_file_name=test_meta["file_path"],
                    test_code=test_meta["test_code"]
                )

                test_record = {
                    **test_meta,
                    **exec_result
                }
                db.add_test(test_record)
                executed_tests.append(test_record)

                # Evaluate execution feedback:
                # If test FAILED or threw expected AssertionError/Exception, bug is CONFIRMED!
                if exec_result["execution_status"] in ("FAILED", "ERROR"):
                    issue["status"] = "CONFIRMED"
                    confirmed_bug_count += 1
                    db.update_issue_status(issue["id"], "CONFIRMED")
                    self._notify(run_id, "VERIFICATION", f"Bug CONFIRMED via test reproduction: {issue['title']}")

                    # Phase 6: Autonomous Fix & Verification Loop
                    if self.auto_verify:
                        self._notify(run_id, "FIX_VERIFY", f"Attempting autonomous patch & re-verification for: {issue['title']}")
                        fix_data = self.reviewer.generate_fix(rel_path, issue, full_code)
                        patched_source = fix_data.get("full_fixed_file", full_code)

                        # Re-run the same reproduction test against the patched source
                        patched_sources = {**source_file_cache, rel_path: patched_source}
                        verify_exec = self.test_executor.run_test_in_sandbox(
                            source_files=patched_sources,
                            test_file_name=f"verify_{test_meta['file_path']}",
                            test_code=test_meta["test_code"]
                        )

                        if verify_exec["execution_status"] == "PASSED":
                            issue["status"] = "FIXED"
                            fixed_bug_count += 1
                            db.update_issue_status(issue["id"], "FIXED")
                            self._notify(run_id, "FIX_VERIFY", f"Fix VERIFIED! Test passed on patched code.")
                        else:
                            self._notify(run_id, "FIX_VERIFY", "Patch did not fully resolve test failure; flagged for manual review.")

                else:
                    # Test passed unexpectedly or couldn't trigger failure
                    issue["status"] = "SUSPECTED"
                    db.update_issue_status(issue["id"], "SUSPECTED")
                    self._notify(run_id, "VERIFICATION", f"Defect not reproduced by test harness (marked SUSPECTED): {issue['title']}")

            # Phase 7: Optional GitHub Issue Synchronization
            if sync_github_issues and github_repo and "/" in github_repo:
                owner, repo = github_repo.split("/", 1)
                for issue in all_detected_issues:
                    if issue["status"] in ("CONFIRMED", "FIXED"):
                        res = self.github.create_github_issue(owner, repo, issue, dry_run=not self.github.is_authenticated())
                        if res.get("issue_url"):
                            db.update_issue_status(issue["id"], issue["status"], res.get("issue_url"))

            # Phase 8: Metrics, Finalization & Reporting
            total_duration = round(time.time() - start_time, 2)
            passed_tests_count = sum(1 for t in executed_tests if t.get("execution_status") == "PASSED")
            test_pass_rate = round((passed_tests_count / len(executed_tests) * 100.0), 1) if executed_tests else 0.0

            # False positive approximation: suspected issues that couldn't be confirmed
            suspected_count = sum(1 for i in all_detected_issues if i["status"] == "SUSPECTED")
            fp_rate = round((suspected_count / len(all_detected_issues) * 100.0), 1) if all_detected_issues else 0.0

            db.update_run(
                run_id,
                status="COMPLETED",
                total_bugs=len(all_detected_issues),
                confirmed_bugs=confirmed_bug_count,
                test_pass_rate=test_pass_rate,
                execution_time_sec=total_duration,
                false_positive_rate=fp_rate,
                summary=f"Detected {len(all_detected_issues)} issues ({confirmed_bug_count} confirmed, {fixed_bug_count} verified fixes)."
            )

            # Generate exportable reports
            report_paths = report_generator.generate_all(run_id)
            self._notify(run_id, "COMPLETE", f"Analysis complete in {total_duration}s. Reports generated.")

            return {
                "run_id": run_id,
                "status": "COMPLETED",
                "repo_info": repo_info,
                "total_bugs": len(all_detected_issues),
                "confirmed_bugs": confirmed_bug_count,
                "fixed_bugs": fixed_bug_count,
                "test_pass_rate": test_pass_rate,
                "false_positive_rate": fp_rate,
                "execution_time_sec": total_duration,
                "issues": all_detected_issues,
                "tests": executed_tests,
                "reports": report_paths
            }

        except Exception as e:
            logger.error("Agent execution failed on run %s: %s", run_id, e, exc_info=True)
            db.update_run(run_id, status="FAILED", summary=str(e))
            self._notify(run_id, "ERROR", f"Agent run failed: {e}", level="ERROR")
            return {
                "run_id": run_id,
                "status": "FAILED",
                "error": str(e)
            }
        finally:
            if git_analyzer:
                git_analyzer.cleanup()

