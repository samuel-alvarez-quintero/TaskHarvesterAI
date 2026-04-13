import imaplib
import email
import os
from dotenv import load_dotenv
from datetime import datetime
from src.app.db import get_conn

load_dotenv()

def fetch_unseen():
    mail = imaplib.IMAP4_SSL(os.getenv("IMAP_HOST"))
    mail.login(os.getenv("IMAP_USER"), os.getenv("IMAP_PASS"))
    mail.select("inbox")

    status, messages = mail.search(None, 'UNSEEN')

    conn = get_conn()
    c = conn.cursor()

    for num in messages[0].split():
        _, msg_data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])

        content = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    content = part.get_payload(decode=True).decode(errors="ignore")
        else:
            content = msg.get_payload(decode=True).decode(errors="ignore")

        c.execute("""
        INSERT INTO messages (source, external_id, content, created_at)
        VALUES (?, ?, ?, ?)
        """, ("email", num.decode(), content, datetime.now()))

    conn.commit()
    conn.close()
    mail.logout()