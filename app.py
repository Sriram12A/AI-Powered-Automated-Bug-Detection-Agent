"""
Streamlit Web Dashboard for AI Bug Detection & Verification Agent
"""

import os
import streamlit as st
from agent import BugDetectionAgent

st.set_page_config(
    page_title="Argus-AI | Bug Detection Agent",
    page_icon="🛡️",
    layout="wide"
)

# Header
st.title("🛡️ Argus-AI: Automated Bug Detection Agent")
st.caption("Autonomous Agentic AI that detects defects, synthesizes reproduction Pytest cases, and verifies fixes in a safe sandbox.")

# Sidebar Settings
st.sidebar.header("⚙️ Agent Settings")
provider = st.sidebar.selectbox(
    "AI Provider",
    ["mock", "gemini", "openai"],
    index=0,
    help="'mock' works immediately offline with zero API keys. 'gemini' uses Google Gemini API."
)
st.sidebar.markdown("---")
st.sidebar.markdown("""
### 🧠 How It Works
1. **Analyze Code:** LLM detects defects & vulnerabilities.
2. **Generate Tests:** Auto-creates targeted Pytest scripts.
3. **Sandbox Execution:** Runs tests in an isolated temp environment.
4. **Fix Verification:** Applies patch & re-tests to prove bug elimination.
""")

# Main Workspace
col_code, col_actions = st.columns([3, 1])

with col_actions:
    st.subheader("Presets")
    load_sample = st.button("📁 Load Vulnerable Sample", use_container_width=True)
    run_agent = st.button("🚀 Run Agent Pipeline", type="primary", use_container_width=True)

# Sample Code Loader
sample_code = ""
sample_file_path = "vulnerable_sample.py"
if os.path.exists(sample_file_path):
    with open(sample_file_path, "r", encoding="utf-8") as f:
        sample_code = f.read()

if "source_input" not in st.session_state:
    st.session_state["source_input"] = sample_code

if load_sample:
    st.session_state["source_input"] = sample_code
    st.rerun()

with col_code:
    code_text = st.text_area(
        "Python Code to Analyze:",
        value=st.session_state["source_input"],
        height=320,
        key="editor"
    )

st.markdown("---")

# Execution trigger
if run_agent:
    if not code_text.strip():
        st.error("Please enter or paste Python code to analyze.")
    else:
        with st.spinner("🤖 Agent analyzing code, generating tests, and verifying fixes in sandbox..."):
            agent = BugDetectionAgent(provider=provider)
            results = agent.run_pipeline(code_text, file_name="vulnerable_sample.py")

        st.success(f"Execution complete in {results['duration_sec']}s!")

        # Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bugs Detected", results["total_bugs"])
        m2.metric("Confirmed via Test", results["confirmed_bugs"])
        m3.metric("Verified Fixes", results["fixed_bugs"])
        m4.metric("Pipeline Duration", f"{results['duration_sec']}s")

        st.markdown("### 🐞 Detected Issues & Autonomous Verification")

        for i, item in enumerate(results["results"], 1):
            issue = item["issue"]
            verification = item["verification"]
            sev = issue.get("severity", "MEDIUM")

            badge_color = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🔵"
            }.get(sev, "⚪")

            with st.expander(f"{badge_color} Issue #{i}: [{sev}] {issue.get('title')} (Line {issue.get('line_number')})", expanded=True):
                st.markdown(f"**Category:** `{issue.get('category')}` | **Status:** `{issue.get('status')}`")
                st.write(issue.get("description"))

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**⚠️ Faulty Code:**")
                    st.code(issue.get("code_snippet"), language="python")
                with c2:
                    st.markdown("**💡 Suggested Patch:**")
                    st.code(issue.get("suggested_fix"), language="python")

                st.markdown("---")
                st.markdown(f"**🧪 Reproduction Pytest Suite:** (Initial Test Result: `{item['initial_test_status']}`)")
                st.code(item["test_code"], language="python")

                if verification.get("verified"):
                    st.success("✅ **Fix Empirically Verified:** Sandboxed re-test passed with 0 errors!")
                else:
                    st.warning("⚠️ **Fix Requires Manual Review:** Automated patch did not satisfy all test assertions.")

        # Download Report
        st.markdown("---")
        report_md = f"# Bug Detection Report\n\n- Total Bugs: {results['total_bugs']}\n- Confirmed Bugs: {results['confirmed_bugs']}\n- Verified Fixes: {results['fixed_bugs']}\n\n"
        for r in results["results"]:
            iss = r["issue"]
            report_md += f"## [{iss.get('severity')}] {iss.get('title')}\n{iss.get('description')}\n\n```python\n{iss.get('suggested_fix')}\n```\n\n"

        st.download_button("📥 Download Markdown Report", data=report_md, file_name="bug_report.md", mime="text/markdown")
