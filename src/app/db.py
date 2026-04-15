import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "data/tasks.db")


def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        source TEXT,
        received_on DATETIME,
        external_id TEXT,
        from_address TEXT,
        to_address TEXT,
        subject TEXT,
        content TEXT,
        processed INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS ai_log (
        id INTEGER PRIMARY KEY,
        provider TEXT(50),
        model TEXT(50),
        http_status TEXT(5) DEFAULT '102',
        status TEXT(20) DEFAULT 'pending',
        prompt TEXT,
        response TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        message_id INTEGER,
        FOREIGN KEY (message_id) REFERENCES messages(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS client (
        id INTEGER PRIMARY KEY,
        name TEXT,
        emails TEXT,
        phone_numbers TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS task_groups (
        id INTEGER PRIMARY KEY,
        name TEXT,
        requested_on DATETIME,
        expected_delivery_date DATETIME,
        priority TEXT(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        client_id INTEGER,
        FOREIGN KEY (client_id) REFERENCES client(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        requested_on DATETIME,
        expected_delivery_date DATETIME,
        priority TEXT(20),
        content TEXT,
        status TEXT(20) DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        task_group_id INTEGER,
        ai_log_id INTEGER,
        FOREIGN KEY (task_group_id) REFERENCES task_groups(id),
        FOREIGN KEY (ai_log_id) REFERENCES ai_log(id)
    )
    """)

    conn.commit()
    conn.close()
