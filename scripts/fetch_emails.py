from app.imap_client import fetch_unseen
from app.db import init_db

init_db()
fetch_unseen()