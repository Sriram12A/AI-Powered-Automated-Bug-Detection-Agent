import sqlite3

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
