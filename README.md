# 🛡️ Argus-AI: AI-Powered Automated Bug Detection Agent

A clean, production-ready **Agentic AI** system that autonomously detects bugs in Python code, synthesizes reproduction Pytest test cases, executes them in an isolated sandbox, and verifies code fixes.

Built for a **Software Intern – Agentic AI / AI Automation Engineering** portfolio.

---

## 🌟 What This Agent Does

1. **Automated Defect & Vulnerability Detection:**  
   Uses LLMs (Google Gemini / OpenAI / Built-in Heuristics) to analyze code for SQL Injection, off-by-one boundary bugs, and logic flaws.
2. **Dynamic Pytest Synthesis:**  
   Automatically writes a Pytest reproduction suite asserting expected behavior against the identified bug.
3. **Isolated Sandboxed Execution:**  
   Safely executes the test inside an ephemeral temporary directory to confirm the bug reproduces (`FAILED`).
4. **Empirical Fix Verification:**  
   Generates a patch, applies it, and re-executes tests in the sandbox to verify the fix passes with zero errors (`FIXED`).

---

## 📂 Simplified File Structure

```text
├── agent.py               # Core Agent: analyze, generate tests, run sandbox, verify fixes
├── app.py                 # Interactive Streamlit Web Dashboard
├── vulnerable_sample.py   # Demonstration code containing realistic bugs
├── test_agent.py          # Automated unit test suite for the agent
├── upload_to_github.py    # 1-Click automated GitHub upload script
├── upload_to_github.bat   # Double-clickable Windows uploader
├── requirements.txt       # Minimal, clean dependencies
├── .env.example           # API keys configuration template
└── README.md              # Project documentation
```

---

## 🚀 Quickstart: Run in 2 Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser:
- Click **"Load Vulnerable Sample"**.
- Click **"Run Agent Pipeline"**.
- Watch the agent identify defects, generate tests, and verify fixes in real time!

---

## 🧪 Run Automated Tests
```bash
pytest test_agent.py -v
```

---

## 📤 1-Click Upload to GitHub

To push this project to your GitHub repository:
- Double-click **`upload_to_github.bat`**, OR
- Run in terminal:
  ```bash
  python upload_to_github.py
  ```

---

## 👨‍💻 Author

**BATCHU HANUMATH VENKATA NAGA SRIRAM**  
*SRM Institute of Science and Technology*  
- **Email:** [nagasriram2006@gmail.com](mailto:nagasriram2006@gmail.com)  
- **LinkedIn:** [linkedin.com/in/sri-ram-353422330](https://www.linkedin.com/in/sri-ram-353422330)  
- **GitHub:** [github.com/Sriram12A](https://github.com/Sriram12A)
