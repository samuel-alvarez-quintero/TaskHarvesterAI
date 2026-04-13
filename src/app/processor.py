import json
from datetime import datetime
from src.app.db import get_conn
from src.app.ollama_client import extract_tasks

def process():
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT id, content FROM messages WHERE processed = 0")
    rows = c.fetchall()

    for row in rows:
        msg_id, content = row

        try:
            result = extract_tasks(content)
            data = json.loads(result)

            for task in data.get("tasks", []):
                c.execute("""
                INSERT INTO tasks (content, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """, (task, data.get("priority"), datetime.now(), datetime.now()))

            c.execute("UPDATE messages SET processed = 1 WHERE id = ?", (msg_id,))
        except Exception as e:
            print("Error:", e)

    conn.commit()
    conn.close()