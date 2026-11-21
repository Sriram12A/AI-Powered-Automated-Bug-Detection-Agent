"""FastAPI REST API Service for the Automated Bug Detection Agent."""

from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent import BugDetectionAgent
from database import db
from config import config

app = FastAPI(
    title="Argus-AI Automated Bug Detection API",
    description="Agentic REST API for automated Git code review, test generation, sandboxed execution, and bug verification.",
    version="1.0.0"
)


class AnalysisRequest(BaseModel):
    repo_path: str = Field(..., description="Path to local or cloned repository")
    commit_hash: Optional[str] = Field(None, description="Optional commit hash to analyze")
    provider: Optional[str] = Field("mock", description="LLM provider: 'mock', 'gemini', or 'openai'")
    shadow_mode: bool = Field(True, description="Enable shadow workspace isolation")
    auto_verify: bool = Field(True, description="Autonomously patch code and re-test")
    sync_github: bool = Field(False, description="Create GitHub issues for confirmed bugs")
    github_repo: Optional[str] = Field(None, description="Target repository as 'owner/repo'")


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Argus-AI Bug Detector", "version": "1.0.0"}


@app.post("/api/v1/analyze")
def trigger_analysis(req: AnalysisRequest):
    """Trigger an autonomous bug detection and verification pipeline."""
    try:
        agent = BugDetectionAgent(
            llm_provider_name=req.provider,
            shadow_mode=req.shadow_mode,
            auto_verify=req.auto_verify
        )
        result = agent.run(
            repo_path=req.repo_path,
            commit_hash=req.commit_hash,
            sync_github_issues=req.sync_github,
            github_repo=req.github_repo
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/runs")
def list_runs(limit: int = 50):
    """List historical analysis runs."""
    return db.list_runs(limit)


@app.get("/api/v1/runs/{run_id}")
def get_run_details(run_id: str):
    """Fetch full details, detected issues, and test telemetry for a run."""
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    issues = db.get_issues_by_run(run_id)
    tests = db.get_tests_by_run(run_id)
    logs = db.get_logs_by_run(run_id)
    return {
        "run": run,
        "issues": issues,
        "tests": tests,
        "logs": logs
    }


@app.get("/api/v1/metrics")
def get_metrics():
    """Retrieve system-wide aggregated telemetry and defect metrics."""
    return db.get_metrics_summary()

