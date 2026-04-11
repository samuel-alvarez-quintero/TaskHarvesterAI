import sys
from app.db import get_conn

def list_tasks():
    conn = get_conn()
    c = conn.cursor()

    for row in c.execute("SELECT id, content, priority, status FROM tasks"):
        print(row)

    conn.close()

def complete(task_id):
    conn = get_conn()
    c = conn.cursor()

    c.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    cmd = sys.argv[1]

    if cmd == "list":
        list_tasks()
    elif cmd == "done":
        complete(sys.argv[2])