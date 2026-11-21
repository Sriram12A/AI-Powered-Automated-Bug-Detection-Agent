"""Database layer for AI Bug Detection Agent using SQLite."""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from config import config

logger = logging.getLogger(__name__)


class Database:
    """Manages SQLite storage for analysis runs, issues, generated tests, and agent telemetry."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Establish a SQLite connection with row factory enabled."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they do not already exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Analysis runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    repo_name TEXT NOT NULL,
                    repo_path TEXT NOT NULL,
                    commit_hash TEXT,
                    branch_name TEXT,
                    status TEXT DEFAULT 'PENDING',
                    total_bugs INTEGER DEFAULT 0,
                    confirmed_bugs INTEGER DEFAULT 0,
                    test_pass_rate REAL DEFAULT 0.0,
                    execution_time_sec REAL DEFAULT 0.0,
                    false_positive_rate REAL DEFAULT 0.0,
                    shadow_mode INTEGER DEFAULT 1,
                    summary TEXT
                )
            """)

            # Detected issues table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INTEGER,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    code_snippet TEXT,
                    suggested_fix TEXT,
                    status TEXT DEFAULT 'SUSPECTED',
                    github_issue_url TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                )
            """)

            # Generated tests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tests (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    issue_id TEXT,
                    test_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    test_code TEXT NOT NULL,
                    execution_status TEXT DEFAULT 'PENDING',
                    stdout TEXT,
                    stderr TEXT,
                    failure_reason TEXT,
                    duration_sec REAL DEFAULT 0.0,
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
                    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE SET NULL
                )
            """)

            # Agent telemetry / execution logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    phase TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                )
            """)

            conn.commit()
            logger.info("Database initialized at %s", self.db_path)

    def create_run(self, run_id: str, repo_name: str, repo_path: str,
                   commit_hash: str = "", branch_name: str = "",
                   shadow_mode: bool = True) -> str:
        """Create a new analysis run record."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO runs (id, created_at, repo_name, repo_path, commit_hash, branch_name, status, shadow_mode)
                VALUES (?, datetime('now'), ?, ?, ?, ?, 'RUNNING', ?)
            """, (run_id, repo_name, repo_path, commit_hash, branch_name, 1 if shadow_mode else 0))
            conn.commit()
        return run_id

    def update_run(self, run_id: str, **kwargs):
        """Update fields of an analysis run."""
        if not kwargs:
            return
        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [run_id]
        with self.get_connection() as conn:
            conn.execute(f"UPDATE runs SET {fields} WHERE id = ?", values)
            conn.commit()

    def add_issue(self, issue: Dict[str, Any]) -> str:
        """Add a detected issue to the database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO issues (
                    id, run_id, file_path, line_number, category, severity,
                    confidence, title, description, code_snippet, suggested_fix,
                    status, github_issue_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                issue["id"],
                issue["run_id"],
                issue["file_path"],
                issue.get("line_number", 0),
                issue.get("category", "LOGICAL_ERROR"),
                issue.get("severity", "MEDIUM"),
                issue.get("confidence", "HIGH"),
                issue.get("title", "Untitled Issue"),
                issue.get("description", ""),
                issue.get("code_snippet", ""),
                issue.get("suggested_fix", ""),
                issue.get("status", "SUSPECTED"),
                issue.get("github_issue_url", None)
            ))
            conn.commit()
        return issue["id"]

    def update_issue_status(self, issue_id: str, status: str, github_issue_url: Optional[str] = None):
        """Update status and optional GitHub URL for an issue."""
        with self.get_connection() as conn:
            if github_issue_url:
                conn.execute(
                    "UPDATE issues SET status = ?, github_issue_url = ? WHERE id = ?",
                    (status, github_issue_url, issue_id)
                )
            else:
                conn.execute(
                    "UPDATE issues SET status = ? WHERE id = ?",
                    (status, issue_id)
                )
            conn.commit()

    def add_test(self, test: Dict[str, Any]) -> str:
        """Record a generated test and its execution results."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO tests (
                    id, run_id, issue_id, test_name, file_path, test_code,
                    execution_status, stdout, stderr, failure_reason, duration_sec
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test["id"],
                test["run_id"],
                test.get("issue_id"),
                test["test_name"],
                test["file_path"],
                test["test_code"],
                test.get("execution_status", "PENDING"),
                test.get("stdout", ""),
                test.get("stderr", ""),
                test.get("failure_reason", ""),
                test.get("duration_sec", 0.0)
            ))
            conn.commit()
        return test["id"]

    def log(self, run_id: str, phase: str, level: str, message: str):
        """Append an execution telemetry entry."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO logs (run_id, timestamp, phase, level, message)
                VALUES (?, datetime('now'), ?, ?, ?)
            """, (run_id, phase, level, message))
            conn.commit()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a run by its ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            return dict(row) if row else None

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List historical runs ordered by creation time descending."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_issues_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve all issues identified during a run."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM issues WHERE run_id = ?", (run_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_tests_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve all tests executed during a run."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM tests WHERE run_id = ?", (run_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_logs_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve telemetry logs for a run."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM logs WHERE run_id = ? ORDER BY id ASC", (run_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Aggregate high-level metrics across all historical analysis runs."""
        with self.get_connection() as conn:
            runs_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            total_bugs = conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
            confirmed_bugs = conn.execute("SELECT COUNT(*) FROM issues WHERE status = 'CONFIRMED'").fetchone()[0]
            fixed_bugs = conn.execute("SELECT COUNT(*) FROM issues WHERE status = 'FIXED'").fetchone()[0]
            total_tests = conn.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
            passed_tests = conn.execute("SELECT COUNT(*) FROM tests WHERE execution_status = 'PASSED'").fetchone()[0]

            severity_dist = conn.execute(
                "SELECT severity, COUNT(*) as count FROM issues GROUP BY severity"
            ).fetchall()
            category_dist = conn.execute(
                "SELECT category, COUNT(*) as count FROM issues GROUP BY category"
            ).fetchall()

            avg_runtime = conn.execute(
                "SELECT AVG(execution_time_sec) FROM runs WHERE status = 'COMPLETED'"
            ).fetchone()[0] or 0.0

            pass_rate = (passed_tests / total_tests * 100.0) if total_tests > 0 else 0.0

            return {
                "total_runs": runs_count,
                "total_bugs_detected": total_bugs,
                "confirmed_bugs": confirmed_bugs,
                "fixed_bugs": fixed_bugs,
                "total_tests_generated": total_tests,
                "test_pass_rate": round(pass_rate, 1),
                "avg_runtime_sec": round(avg_runtime, 2),
                "severity_distribution": {row["severity"]: row["count"] for row in severity_dist},
                "category_distribution": {row["category"]: row["count"] for row in category_dist}
            }


# Singleton database instance
db = Database()

