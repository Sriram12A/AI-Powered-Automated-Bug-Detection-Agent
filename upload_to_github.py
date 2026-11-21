"""
1-Click Automated GitHub Uploader for Argus-AI Bug Detection Agent
"""

import subprocess
import sys

REPO_URL = "https://github.com/Sriram12A/AI-Powered-Automated-Bug-Detection-Agent.git"

def run_cmd(cmd):
    print(f"--> Running: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(res.stderr.strip())
    return res.returncode

def main():
    print("==========================================================")
    print("🚀 Uploading Argus-AI Bug Detection Agent to GitHub")
    print(f"Target: {REPO_URL}")
    print("==========================================================\n")

    # 1. Initialize if needed
    run_cmd("git init -b main")

    # 2. Stage all files
    print("\n📦 Staging project files...")
    run_cmd("git add .")

    # 3. Commit
    print("\n📝 Creating commit...")
    run_cmd('git commit -m "feat: complete AI-powered bug detection agent"')

    # 4. Configure remote
    print("\n🔗 Configuring GitHub remote...")
    run_cmd(f"git remote remove origin")
    run_cmd(f"git remote add origin {REPO_URL}")
    run_cmd("git branch -M main")

    # 5. Push to GitHub
    print("\n⬆️ Pushing to GitHub main branch...")
    code = run_cmd("git push -u origin main")

    if code == 0:
        print("\n" + "=" * 58)
        print("🎉 SUCCESS! Your project is now live on GitHub:")
        print(REPO_URL.replace(".git", ""))
        print("=" * 58)
    else:
        print("\n⚠️ Note: If GitHub prompted for login or the remote repo was not yet created,")
        print("please ensure the repository exists at:")
        print(f"https://github.com/Sriram12A/AI-Powered-Automated-Bug-Detection-Agent")
        print("Then re-run this script.")

if __name__ == "__main__":
    main()

