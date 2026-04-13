from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    from src.app.imap_client import fetch_unseen
    from src.app.db import init_db

    init_db()
    fetch_unseen()
