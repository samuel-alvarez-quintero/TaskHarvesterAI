import sqlite3

DB_PATH = "data/tasks.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        source TEXT,
        external_id TEXT,
        content TEXT,
        processed INTEGER DEFAULT 0,
        created_at DATETIME
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        content TEXT,
        priority TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME,
        updated_at DATETIME
    )
    """)

    conn.commit()
    conn.close()