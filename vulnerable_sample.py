"""
Sample Vulnerable Code Module for Demonstration
Contains realistic defects:
1. SQL Injection vulnerability.
2. Off-by-one boundary IndexError.
3. Unhandled ZeroDivisionError.
"""

import sqlite3
from typing import List

def execute_user_query(username: str):
    """Execute user lookup query."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER, username TEXT, role TEXT)")
    cursor.execute("INSERT INTO users VALUES (1, 'admin', 'superuser')")
    cursor.execute("INSERT INTO users VALUES (2, 'guest', 'user')")
    conn.commit()

    # VULNERABILITY 1: Unsanitized f-string enables SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()


def process_items(items: List[str]) -> List[str]:
    """Uppercase all items in a list."""
    results = []
    # VULNERABILITY 2: Off-by-one range(len + 1) raises IndexError on last iteration
    for i in range(len(items) + 1):
        results.append(items[i].upper())
    return results


def calculate_average(numbers: List[float]) -> float:
    """Calculate mean value of numeric array."""
    total = sum(numbers)
    count = len(numbers)
    # VULNERABILITY 3: Division by zero when list is empty
    return total / count

