"""GitHub REST API integration for repository analysis and automated issue reporting."""

import logging
from typing import Dict, Any, List, Optional
import requests
from config import config

logger = logging.getLogger(__name__)


class GitHubIntegration:
    """Manages GitHub API interactions including repository fetching and issue synchronization."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or config.GITHUB_TOKEN
        self.base_url = config.GITHUB_API_BASE
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Argus-AI-Bug-Detector"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def is_authenticated(self) -> bool:
        """Check if a valid GitHub personal access token is configured."""
        return bool(self.token)

    def get_repo_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch remote repository details from GitHub."""
        if not self.is_authenticated():
            return {
                "owner": owner,
                "repo": repo,
                "url": f"https://github.com/{owner}/{repo}",
                "mode": "unauthenticated"
            }

        url = f"{self.base_url}/repos/{owner}/{repo}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning("GitHub API returned status %d: %s", resp.status_code, resp.text)
                return {"error": f"Status {resp.status_code}", "message": resp.text}
        except Exception as e:
            logger.error("Failed to connect to GitHub API: %s", e)
            return {"error": str(e)}

    def create_github_issue(
        self,
        owner: str,
        repo: str,
        issue_data: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Create a formatted issue on GitHub for a confirmed defect.
        If dry_run=True or no token is present, returns a simulated response.
        """
        title = f"[AI Bug Detector] [{issue_data.get('severity', 'MEDIUM')}] {issue_data.get('title')}"

        body = f"""### 🤖 AI-Powered Automated Bug Detection Report

**File:** `{issue_data.get('file_path')}` (Line {issue_data.get('line_number', 'N/A')})  
**Category:** `{issue_data.get('category', 'LOGICAL_ERROR')}`  
**Severity:** `{issue_data.get('severity', 'MEDIUM')}`  
**Confidence:** `{issue_data.get('confidence', 'HIGH')}`  
**Verification Status:** `{issue_data.get('status', 'CONFIRMED')}`  

---

#### 📝 Defect Description
{issue_data.get('description', 'No description provided.')}

#### ⚠️ Faulty Code Snippet
```python
{issue_data.get('code_snippet', '# No snippet available')}
```

#### 💡 Suggested Fix / Patch
```python
{issue_data.get('suggested_fix', '# No fix provided')}
```

---
*Reported autonomously by Argus AI Automated Bug Detection Agent.*
"""

        if dry_run or not self.token:
            simulated_issue_number = abs(hash(issue_data.get("id", "issue"))) % 900 + 100
            simulated_url = f"https://github.com/{owner}/{repo}/issues/{simulated_issue_number}"
            logger.info("Simulated GitHub issue created (dry-run): %s", simulated_url)
            return {
                "success": True,
                "simulated": True,
                "issue_url": simulated_url,
                "issue_number": simulated_issue_number,
                "title": title
            }

        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        payload = {
            "title": title,
            "body": body,
            "labels": [
                "bug",
                "ai-detected",
                f"severity:{issue_data.get('severity', 'medium').lower()}"
            ]
        }

        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=10)
            if resp.status_code == 201:
                data = resp.json()
                logger.info("Created GitHub issue: %s", data.get("html_url"))
                return {
                    "success": True,
                    "simulated": False,
                    "issue_url": data.get("html_url"),
                    "issue_number": data.get("number"),
                    "title": title
                }
            else:
                logger.error("Failed to create GitHub issue: %s", resp.text)
                return {
                    "success": False,
                    "error": resp.text,
                    "status_code": resp.status_code
                }
        except Exception as e:
            logger.error("Exception creating GitHub issue: %s", e)
            return {"success": False, "error": str(e)}

