"""Git repository and diff analyzer module using GitPython."""

import os
import stat
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import git
from git import Repo, Diff

from config import config

logger = logging.getLogger(__name__)


def _remove_readonly(func, path, excinfo):
    """Clear the read-only bit and retry removal on Windows."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _safe_rmtree(path: Path):
    """Safely delete a directory tree on Windows handling read-only git metadata."""
    if path.exists():
        shutil.rmtree(str(path), onerror=_remove_readonly)


class GitAnalyzer:
    """Analyzes Git repositories, commit histories, and unified diffs in shadow mode."""

    def __init__(self, repo_path: str, shadow_mode: bool = True, run_id: Optional[str] = None):
        self.original_path = Path(repo_path).resolve()
        self.shadow_mode = shadow_mode
        self.run_id = run_id or f"run_{int(os.times().elapsed * 1000)}"
        self.work_dir = self._setup_workspace()
        self.repo = Repo(self.work_dir)

    def _setup_workspace(self) -> Path:
        """Establish the working directory (shadow clone or original)."""
        if not self.original_path.exists():
            raise FileNotFoundError(f"Target repository path does not exist: {self.original_path}")

        if not self.shadow_mode:
            return self.original_path

        shadow_path = config.SHADOW_DIR / self.run_id
        _safe_rmtree(shadow_path)
        config.SHADOW_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Initializing shadow clone at: %s", shadow_path)

        # Clone locally without fetching over network (git clone creates shadow_path)
        Repo.clone_from(str(self.original_path), str(shadow_path))
        return shadow_path

    def get_repo_info(self) -> Dict[str, Any]:
        """Fetch general repository metadata."""
        try:
            head_commit = self.repo.head.commit
            branch_name = self.repo.active_branch.name if not self.repo.head.is_detached else "DETACHED"
            return {
                "repo_name": self.original_path.name,
                "repo_path": str(self.original_path),
                "work_dir": str(self.work_dir),
                "branch": branch_name,
                "commit_hash": head_commit.hexsha,
                "commit_short": head_commit.hexsha[:8],
                "author": f"{head_commit.author.name} <{head_commit.author.email}>",
                "message": head_commit.message.strip(),
                "date": head_commit.committed_datetime.isoformat(),
                "is_dirty": self.repo.is_dirty(),
                "shadow_mode": self.shadow_mode
            }
        except Exception as e:
            logger.error("Failed to fetch repository information: %s", e)
            return {
                "repo_name": self.original_path.name,
                "repo_path": str(self.original_path),
                "error": str(e)
            }

    def list_recent_commits(self, limit: int = 15) -> List[Dict[str, Any]]:
        """List recent commits on the current branch."""
        commits = []
        try:
            for c in list(self.repo.iter_commits(max_count=limit)):
                commits.append({
                    "hash": c.hexsha,
                    "short_hash": c.hexsha[:8],
                    "message": c.message.strip().split("\n")[0],
                    "author": c.author.name,
                    "date": c.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception as e:
            logger.warning("Error reading commits: %s", e)
        return commits

    def analyze_commit_diff(self, commit_hash: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract detailed diffs for a given commit against its parent,
        or for uncommitted working tree changes if commit_hash is omitted and repo is dirty.
        """
        changed_files = []

        try:
            if commit_hash:
                target_commit = self.repo.commit(commit_hash)
                parent_commit = target_commit.parents[0] if target_commit.parents else git.NULL_TREE
                diff_index = parent_commit.diff(target_commit, create_patch=True)
            else:
                # Check uncommitted working directory changes
                if self.repo.is_dirty(untracked_files=True):
                    diff_index = self.repo.head.commit.diff(None, create_patch=True)
                elif self.repo.head.commit.parents:
                    diff_index = self.repo.head.commit.parents[0].diff(self.repo.head.commit, create_patch=True)
                else:
                    diff_index = []

            for diff_item in diff_index:
                file_path = diff_item.b_path or diff_item.a_path
                # Filter for Python source files
                if not file_path or not file_path.endswith(".py"):
                    continue

                change_type = "MODIFIED"
                if diff_item.new_file:
                    change_type = "ADDED"
                elif diff_item.deleted_file:
                    change_type = "DELETED"
                elif diff_item.renamed:
                    change_type = "RENAMED"

                diff_text = diff_item.diff.decode("utf-8", errors="replace") if diff_item.diff else ""

                full_path = self.work_dir / file_path
                current_content = full_path.read_text(encoding="utf-8", errors="replace") if full_path.exists() else ""

                changed_files.append({
                    "file_path": file_path,
                    "full_path": str(full_path),
                    "change_type": change_type,
                    "diff_text": diff_text,
                    "full_content": current_content,
                    "lines_added": diff_text.count("\n+"),
                    "lines_deleted": diff_text.count("\n-")
                })

        except Exception as e:
            logger.error("Diff extraction failed: %s", e)

        return changed_files

    def cleanup(self):
        """Clean up temporary shadow workspace if created."""
        if self.shadow_mode and self.work_dir != self.original_path and self.work_dir.exists():
            try:
                # Close git repo handles before deleting directory
                self.repo.close()
                _safe_rmtree(self.work_dir)
                logger.info("Cleaned up shadow workspace: %s", self.work_dir)
            except Exception as e:
                logger.warning("Error cleaning shadow workspace: %s", e)
