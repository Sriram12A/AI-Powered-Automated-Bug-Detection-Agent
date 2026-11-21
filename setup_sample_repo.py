"""Script to generate a sample vulnerable repository with realistic Git history."""

import os
import shutil
from pathlib import Path
import git

def setup_vulnerable_sample_repo():
    target_dir = Path(__file__).resolve().parent / "sample_repos" / "vulnerable_app"
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)

    target_dir.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.init(target_dir)

    # Configure committer
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Demo Engineer")
        cw.set_value("user", "email", "engineer@example.com")

    # Commit 1: Initial clean base
    base_file = target_dir / "calculator.py"
    base_file.write_text("""# Standard utility calculator
def add(a: int, b: int) -> int:
    return a + b

def subtract(a: int, b: int) -> int:
    return a - b
""", encoding="utf-8")

    repo.index.add(["calculator.py"])
    repo.index.commit("Initial commit: Add standard arithmetic utilities")

    # Commit 2: Added authentication service with SQL injection & None dereference
    auth_file = target_dir / "auth_service.py"
    auth_file.write_text('''import sqlite3

def init_mock_db():
    conn = sqlite3.connect(":memory:")
    c = conn.cursor()
    c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, role TEXT)")
    c.execute("INSERT INTO users VALUES (1, 'admin', 'superuser')")
    c.execute("INSERT INTO users VALUES (2, 'john', 'user')")
    conn.commit()
    return conn

def execute_user_query(username: str):
    conn = init_mock_db()
    cursor = conn.cursor()
    # VULNERABILITY: Raw f-string SQL query allows SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    rows = cursor.fetchall()
    return rows

def get_user_profile(user_id: int):
    # Potential None dereference if user is not found
    user = None if user_id < 0 else {"name": "Alice", "role": "admin"}
    # Faulty: does not verify user is not None
    return user["name"] if user else None
''', encoding="utf-8")

    repo.index.add(["auth_service.py"])
    repo.index.commit("feat(auth): add user query execution and profile fetching")

    # Commit 3: Added data processor with boundary condition error and division by zero
    data_file = target_dir / "data_processor.py"
    data_file.write_text('''from typing import List, Dict, Any

def process_items(items: List[str]) -> List[str]:
    processed = []
    # DEFECT: Off-by-one boundary condition in range len + 1 causes IndexError
    for i in range(len(items) + 1):
        processed.append(items[i].upper())
    return processed

def calculate_average(numbers: List[float]) -> float:
    total = sum(numbers)
    count = len(numbers)
    # DEFECT: Unhandled ZeroDivisionError when numbers list is empty
    return total / count
''', encoding="utf-8")

    repo.index.add(["data_processor.py"])
    repo.index.commit("feat(analytics): add batch item processor and metric calculations")

    print(f"Sample vulnerable repository successfully initialized at: {target_dir}")
    print(f"Total commits: {len(list(repo.iter_commits()))}")

if __name__ == "__main__":
    setup_vulnerable_sample_repo()

