"""Streamlit Interactive Dashboard for the AI-Powered Automated Bug Detection Agent."""

import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

from config import config
from database import db
from agent import BugDetectionAgent
from report_generator import report_generator
from github_integration import GitHubIntegration

# Configure page layout
st.set_page_config(
    page_title="Argus-AI | Automated Bug Detection Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .badge-critical { background-color: #dc2626; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-high { background-color: #ea580c; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-medium { background-color: #d97706; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-low { background-color: #2563eb; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-fixed { background-color: #16a34a; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
    .badge-confirmed { background-color: #b91c1c; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }
</style>
""", unsafe_allow_html=True)


def get_sample_repo_path() -> str:
    """Return absolute path to built-in sample demo repo."""
    sample_dir = Path(__file__).resolve().parent / "sample_repos" / "vulnerable_app"
    return str(sample_dir) if sample_dir.exists() else str(Path(__file__).resolve().parent)


# Sidebar Configuration
st.sidebar.title("🛡️ Argus-AI Agent")
st.sidebar.caption("Autonomous Bug Detection & Verification")

menu = st.sidebar.radio(
    "Navigation",
    ["🚀 Run Analysis", "🐞 Detected Defects", "🧪 Test Execution Lab", "📊 Telemetry & History", "📑 Reports & GitHub Sync"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Agent Configuration")
selected_provider = st.sidebar.selectbox(
    "LLM Provider",
    ["mock", "gemini", "openai"],
    index=0 if not config.GEMINI_API_KEY else 1,
    help="Select 'mock' for instant offline demonstration without API keys, or 'gemini'/'openai' with an API key."
)

shadow_mode_toggle = st.sidebar.checkbox(
    "Shadow Workspace Mode",
    value=True,
    help="Clones repo into isolated workspace before analysis so original commits are never modified."
)

auto_verify_toggle = st.sidebar.checkbox(
    "Auto-Verify Fixes",
    value=True,
    help="Autonomously patches code and re-runs sandbox tests to verify fixes."
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Agentic AI Architecture**\n- Autonomous Git Diff Analysis\n- LLM Code Review & Defect Hypotheses\n- Dynamic Pytest Synthesis\n- Sandboxed Test Execution\n- Empirical Fix Verification Loop")


# -----------------------------------------------------------------------------
# TAB 1: RUN ANALYSIS CONSOLE
# -----------------------------------------------------------------------------
if menu == "🚀 Run Analysis":
    st.markdown('<div class="main-header">Autonomous Agent Run Console</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Trigger the multi-stage bug detection agent against a local Git repository.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        default_repo = get_sample_repo_path()
        target_repo_path = st.text_input(
            "Repository Path",
            value=default_repo,
            help="Path to any local Git repository"
        )
        commit_to_analyze = st.text_input(
            "Commit Hash (Optional)",
            value="",
            placeholder="Leave empty to analyze latest uncommitted/HEAD changes"
        )

    with col2:
        st.markdown("**Quick Preset Actions:**")
        if st.button("📁 Load Built-in Vulnerable Demo Repo", use_container_width=True):
            st.session_state["target_repo"] = get_sample_repo_path()
            st.rerun()

    st.markdown("---")

    col_btn, col_gh = st.columns([1, 1])
    with col_btn:
        start_analysis = st.button("🚀 Start Autonomous Agent Analysis", type="primary", use_container_width=True)
    with col_gh:
        sync_gh = st.checkbox("Create GitHub Issues for Confirmed Bugs", value=False)
        gh_repo_name = st.text_input("GitHub Target Repo (e.g. owner/repo)", value="Sriram12A/vulnerable-app", disabled=not sync_gh)

    if start_analysis:
        if not os.path.exists(target_repo_path):
            st.error(f"Directory does not exist: {target_repo_path}")
        else:
            status_container = st.status("🤖 Agent actively executing autonomous workflow...", expanded=True)
            log_placeholder = status_container.empty()
            logs_collected = []

            def progress_callback(phase: str, msg: str):
                logs_collected.append(f"**[{phase}]** {msg}")
                log_placeholder.markdown("\n\n".join(logs_collected[-8:]))

            agent = BugDetectionAgent(
                llm_provider_name=selected_provider,
                shadow_mode=shadow_mode_toggle,
                auto_verify=auto_verify_toggle,
                on_progress=progress_callback
            )

            result = agent.run(
                repo_path=target_repo_path,
                commit_hash=commit_to_analyze.strip() or None,
                sync_github_issues=sync_gh,
                github_repo=gh_repo_name if sync_gh else None
            )

            if result.get("status") == "COMPLETED":
                status_container.update(label="✅ Autonomous Agent Run Completed Successfully!", state="complete", expanded=False)
                st.session_state["active_run_id"] = result["run_id"]
                st.success(f"Run `{result['run_id']}` finished in {result['execution_time_sec']}s!")

                # Summary metric badges
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Bugs Detected", result["total_bugs"])
                m2.metric("Confirmed Bugs", result["confirmed_bugs"])
                m3.metric("Verified Fixes", result["fixed_bugs"])
                m4.metric("Test Pass Rate", f"{result['test_pass_rate']}%")
                m5.metric("Runtime", f"{result['execution_time_sec']}s")

            else:
                status_container.update(label="❌ Agent Run Failed", state="error")
                st.error(f"Error during execution: {result.get('error')}")


# -----------------------------------------------------------------------------
# TAB 2: DETECTED DEFECTS EXPLORER
# -----------------------------------------------------------------------------
elif menu == "🐞 Detected Defects":
    st.markdown('<div class="main-header">Detected Defects & Security Vulnerabilities</div>', unsafe_allow_html=True)

    runs = db.list_runs(20)
    if not runs:
        st.info("No analysis runs recorded yet. Execute a run from the 'Run Analysis' tab!")
    else:
        run_options = {f"{r['id']} ({r['repo_name']} - {r['created_at'][:16]})": r['id'] for r in runs}
        selected_run_label = st.selectbox("Select Analysis Run", list(run_options.keys()))
        selected_run_id = run_options[selected_run_label]

        issues = db.get_issues_by_run(selected_run_id)

        # Filters
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            severity_filter = st.multiselect("Filter by Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        with fcol2:
            status_filter = st.multiselect("Filter by Status", ["CONFIRMED", "FIXED", "SUSPECTED"], default=["CONFIRMED", "FIXED", "SUSPECTED"])
        with fcol3:
            search_query = st.text_input("Search Keyword", "")

        filtered = [
            i for i in issues
            if i["severity"] in severity_filter
            and i["status"] in status_filter
            and (search_query.lower() in i["title"].lower() or search_query.lower() in i["description"].lower())
        ]

        st.caption(f"Showing {len(filtered)} of {len(issues)} identified defect(s).")

        if not filtered:
            st.warning("No defects match current filters.")
        else:
            for issue in filtered:
                sev = issue["severity"]
                stat = issue["status"]
                badge_class = f"badge-{sev.lower()}"
                status_class = f"badge-{stat.lower()}"

                with st.expander(f"[{sev}] {issue['title']} — {issue['file_path']} (Line {issue['line_number']})", expanded=(sev in ["CRITICAL", "HIGH"])):
                    st.markdown(f"""
                    <span class="{badge_class}">{sev}</span>
                    <span class="{status_class}">{stat}</span>
                    <span style="color:#64748b; font-size:12px; margin-left:8px;">Category: <b>{issue['category']}</b> | Confidence: <b>{issue['confidence']}</b></span>
                    """, unsafe_allow_html=True)

                    st.markdown(f"\n**Description:**\n{issue['description']}")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**⚠️ Faulty Code:**")
                        st.code(issue.get("code_snippet") or "# No snippet available", language="python")
                    with c2:
                        st.markdown("**💡 Suggested Patch:**")
                        st.code(issue.get("suggested_fix") or "# No fix provided", language="python")

                    if issue.get("github_issue_url"):
                        st.markdown(f"🔗 [View Synced GitHub Issue]({issue['github_issue_url']})")


# -----------------------------------------------------------------------------
# TAB 3: TEST EXECUTION LAB
# -----------------------------------------------------------------------------
elif menu == "🧪 Test Execution Lab":
    st.markdown('<div class="main-header">Sandboxed Pytest Execution Telemetry</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Inspect auto-generated Pytest reproduction suites and isolated sandbox execution telemetry.</div>', unsafe_allow_html=True)

    runs = db.list_runs(20)
    if not runs:
        st.info("No runs available.")
    else:
        run_options = {f"{r['id']} ({r['repo_name']})": r['id'] for r in runs}
        selected_run_id = run_options[st.selectbox("Select Run", list(run_options.keys()))]

        tests = db.get_tests_by_run(selected_run_id)

        if not tests:
            st.warning("No automated tests recorded for this run.")
        else:
            tcol1, tcol2, tcol3, tcol4 = st.columns(4)
            passed = sum(1 for t in tests if t["execution_status"] == "PASSED")
            failed = sum(1 for t in tests if t["execution_status"] == "FAILED")
            errors = sum(1 for t in tests if t["execution_status"] == "ERROR")

            tcol1.metric("Total Tests", len(tests))
            tcol2.metric("Reproduced Failures (Confirmed Bugs)", failed)
            tcol3.metric("Passed Tests", passed)
            tcol4.metric("Errors / Timeouts", errors)

            st.markdown("---")

            for t in tests:
                icon = "❌" if t["execution_status"] in ("FAILED", "ERROR") else "✅"
                with st.expander(f"{icon} {t['test_name']} — Status: {t['execution_status']} ({t['duration_sec']}s)"):
                    st.markdown(f"**Target Test File:** `{t['file_path']}`")
                    if t.get("failure_reason"):
                        st.error(f"**Failure Reason:** {t['failure_reason']}")

                    st.markdown("**Generated Pytest Script:**")
                    st.code(t["test_code"], language="python")

                    if t.get("stdout"):
                        st.markdown("**Pytest Stdout:**")
                        st.code(t["stdout"], language="text")


# -----------------------------------------------------------------------------
# TAB 4: TELEMETRY & HISTORY
# -----------------------------------------------------------------------------
elif menu == "📊 Telemetry & History":
    st.markdown('<div class="main-header">Execution Metrics & History Analytics</div>', unsafe_allow_html=True)

    metrics = db.get_metrics_summary()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Runs", metrics["total_runs"])
    m2.metric("Total Bugs Detected", metrics["total_bugs_detected"])
    m3.metric("Confirmed Bugs", metrics["confirmed_bugs"])
    m4.metric("Verified Fixes", metrics["fixed_bugs"])

    st.markdown("---")

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Bugs by Severity")
        sev_data = metrics.get("severity_distribution", {})
        if sev_data:
            df_sev = pd.DataFrame(list(sev_data.items()), columns=["Severity", "Count"])
            st.bar_chart(df_sev.set_index("Severity"))
        else:
            st.caption("No severity data available.")

    with col_chart2:
        st.subheader("Bugs by Category")
        cat_data = metrics.get("category_distribution", {})
        if cat_data:
            df_cat = pd.DataFrame(list(cat_data.items()), columns=["Category", "Count"])
            st.bar_chart(df_cat.set_index("Category"))
        else:
            st.caption("No category data available.")

    st.markdown("---")
    st.subheader("Historical Runs Table")
    runs = db.list_runs(50)
    if runs:
        df_runs = pd.DataFrame(runs)
        columns_to_show = ["id", "created_at", "repo_name", "status", "total_bugs", "confirmed_bugs", "test_pass_rate", "execution_time_sec", "shadow_mode"]
        st.dataframe(df_runs[[c for c in columns_to_show if c in df_runs.columns]], use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 5: REPORTS & GITHUB SYNC
# -----------------------------------------------------------------------------
elif menu == "📑 Reports & GitHub Sync":
    st.markdown('<div class="main-header">Audit Reports & GitHub Synchronization</div>', unsafe_allow_html=True)

    runs = db.list_runs(20)
    if not runs:
        st.info("No runs available.")
    else:
        run_options = {f"{r['id']} ({r['repo_name']})": r['id'] for r in runs}
        selected_run_id = run_options[st.selectbox("Select Run for Export", list(run_options.keys()))]

        run = db.get_run(selected_run_id)
        issues = db.get_issues_by_run(selected_run_id)
        tests = db.get_tests_by_run(selected_run_id)

        md_text = report_generator.generate_markdown(run, issues, tests)
        html_text = report_generator.generate_html(run, issues, tests)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                label="📥 Download Markdown Report (.md)",
                data=md_text,
                file_name=f"audit_report_{selected_run_id}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with c2:
            st.download_button(
                label="📥 Download HTML Report (.html)",
                data=html_text,
                file_name=f"audit_report_{selected_run_id}.html",
                mime="text/html",
                use_container_width=True
            )

        st.markdown("---")
        st.subheader("Report Live Preview")
        st.markdown(md_text)

