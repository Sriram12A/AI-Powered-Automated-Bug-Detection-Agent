"""Report generation module producing Markdown, HTML, and JSON audit artifacts."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from database import db
from config import config


class ReportGenerator:
    """Compiles multi-format audit reports for completed agentic bug detection runs."""

    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = reports_dir or config.REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, run_id: str) -> Dict[str, str]:
        """Compile and save Markdown, HTML, and JSON reports."""
        run = db.get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found.")

        issues = db.get_issues_by_run(run_id)
        tests = db.get_tests_by_run(run_id)

        md_content = self.generate_markdown(run, issues, tests)
        html_content = self.generate_html(run, issues, tests)
        json_content = self.generate_json(run, issues, tests)

        md_file = self.reports_dir / f"report_{run_id}.md"
        html_file = self.reports_dir / f"report_{run_id}.html"
        json_file = self.reports_dir / f"report_{run_id}.json"

        md_file.write_text(md_content, encoding="utf-8")
        html_file.write_text(html_content, encoding="utf-8")
        json_file.write_text(json.dumps(json_content, indent=2), encoding="utf-8")

        return {
            "markdown": str(md_file),
            "html": str(html_file),
            "json": str(json_file)
        }

    def generate_markdown(self, run: Dict[str, Any], issues: List[Dict[str, Any]], tests: List[Dict[str, Any]]) -> str:
        """Construct a GitHub-flavored Markdown audit report."""
        lines = [
            f"# 🛡️ AI Bug Detection & Autonomous Verification Report",
            f"",
            f"**Run ID:** `{run.get('id')}`  ",
            f"**Repository:** `{run.get('repo_name')}`  ",
            f"**Commit:** `{run.get('commit_hash', 'N/A')}`  ",
            f"**Timestamp:** `{run.get('created_at')}`  ",
            f"**Status:** `{run.get('status')}`  ",
            f"",
            f"## 📊 Executive Summary & Metrics",
            f"",
            f"| Metric | Value |",
            f"| :--- | :--- |",
            f"| **Total Bugs Detected** | {run.get('total_bugs', 0)} |",
            f"| **Confirmed via Sandbox Test** | {run.get('confirmed_bugs', 0)} |",
            f"| **Automated Tests Generated** | {len(tests)} |",
            f"| **Test Pass Rate** | {run.get('test_pass_rate', 0.0)}% |",
            f"| **Total Execution Duration** | {run.get('execution_time_sec', 0.0)}s |",
            f"| **Shadow Workspace Mode** | {'Enabled (Safe)' if run.get('shadow_mode') else 'Disabled'} |",
            f"",
            f"---",
            f"",
            f"## 🐞 Identified Defects & Vulnerabilities ({len(issues)})",
            f""
        ]

        if not issues:
            lines.append("✅ *No defects or vulnerabilities detected in this analysis.*")
        else:
            for i, issue in enumerate(issues, 1):
                lines.extend([
                    f"### {i}. [{issue.get('severity')}] {issue.get('title')}",
                    f"",
                    f"- **File:** `{issue.get('file_path')}` (Line {issue.get('line_number')})",
                    f"- **Category:** `{issue.get('category')}`",
                    f"- **Confidence:** `{issue.get('confidence')}`",
                    f"- **Status:** `{issue.get('status')}`",
                    f"",
                    f"**Description:**  ",
                    f"{issue.get('description')}",
                    f"",
                    f"**Faulty Code:**",
                    f"```python",
                    f"{issue.get('code_snippet', '# Not available')}",
                    f"```",
                    f"",
                    f"**Suggested Patch / Fix:**",
                    f"```python",
                    f"{issue.get('suggested_fix', '# Not available')}",
                    f"```",
                    f""
                ])

        lines.extend([
            f"---",
            f"",
            f"## 🧪 Generated Test Execution Results ({len(tests)})",
            f""
        ])

        if not tests:
            lines.append("*No automated tests were executed for this run.*")
        else:
            for t in tests:
                status_icon = "✅" if t.get("execution_status") == "PASSED" else "❌"
                lines.extend([
                    f"#### {status_icon} `{t.get('test_name')}` ({t.get('execution_status')})",
                    f"- **Target File:** `{t.get('file_path')}`",
                    f"- **Duration:** {t.get('duration_sec', 0.0)}s",
                    f"- **Failure Details:** {t.get('failure_reason') or 'None (Passed)'}",
                    f"",
                    f"<details><summary>View Generated Pytest Code</summary>",
                    f"",
                    f"```python",
                    f"{t.get('test_code')}",
                    f"```",
                    f"</details>",
                    f""
                ])

        lines.append(f"\n*Generated autonomously by Argus-AI Bug Detection Agent.*")
        return "\n".join(lines)

    def generate_html(self, run: Dict[str, Any], issues: List[Dict[str, Any]], tests: List[Dict[str, Any]]) -> str:
        """Construct a standalone, styled HTML report."""
        issues_html = ""
        for i, issue in enumerate(issues, 1):
            severity = issue.get('severity', 'MEDIUM')
            badge_color = {
                "CRITICAL": "#dc2626",
                "HIGH": "#ea580c",
                "MEDIUM": "#d97706",
                "LOW": "#2563eb"
            }.get(severity, "#4b5563")

            issues_html += f"""
            <div class="card">
                <div class="card-header">
                    <span class="badge" style="background:{badge_color}">{severity}</span>
                    <span class="category">{issue.get('category')}</span>
                    <h3>{i}. {issue.get('title')}</h3>
                </div>
                <p><strong>File:</strong> <code>{issue.get('file_path')}:{issue.get('line_number')}</code> | <strong>Status:</strong> {issue.get('status')}</p>
                <p>{issue.get('description')}</p>
                <h4>Faulty Snippet:</h4>
                <pre><code>{issue.get('code_snippet')}</code></pre>
                <h4>Suggested Fix:</h4>
                <pre class="fix"><code>{issue.get('suggested_fix')}</code></pre>
            </div>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Bug Detection Report - {run.get('id')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; color: #1e293b; background: #f8fafc; }}
        .container {{ max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
        h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
        .metric-box {{ background: #f1f5f9; padding: 15px; border-radius: 6px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: 700; color: #1e3a8a; }}
        .card {{ border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin-bottom: 16px; }}
        .badge {{ color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .category {{ color: #64748b; font-size: 12px; margin-left: 8px; font-weight: 600; }}
        pre {{ background: #1e293b; color: #f8fafc; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
        pre.fix {{ background: #064e3b; color: #ecfdf5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ AI Bug Detection Report</h1>
        <p><strong>Run ID:</strong> {run.get('id')} | <strong>Repo:</strong> {run.get('repo_name')} | <strong>Date:</strong> {run.get('created_at')}</p>
        
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-value">{run.get('total_bugs', 0)}</div>
                <div>Bugs Detected</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{run.get('confirmed_bugs', 0)}</div>
                <div>Confirmed Bugs</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{len(tests)}</div>
                <div>Tests Generated</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{run.get('test_pass_rate', 0)}%</div>
                <div>Pass Rate</div>
            </div>
        </div>

        <h2>Identified Defects</h2>
        {issues_html if issues else "<p>No defects identified.</p>"}
    </div>
</body>
</html>
"""

    def generate_json(self, run: Dict[str, Any], issues: List[Dict[str, Any]], tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Produce structured JSON payload."""
        return {
            "run": run,
            "issues": issues,
            "tests": tests,
            "summary": {
                "total_bugs": run.get("total_bugs", 0),
                "confirmed_bugs": run.get("confirmed_bugs", 0),
                "total_tests": len(tests),
                "pass_rate": run.get("test_pass_rate", 0.0),
                "execution_time_sec": run.get("execution_time_sec", 0.0)
            }
        }


# Singleton report generator instance
report_generator = ReportGenerator()

