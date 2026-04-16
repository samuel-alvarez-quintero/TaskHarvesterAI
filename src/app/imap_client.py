from email.header import decode_header
import imaplib
import email
import logging
import os
from datetime import datetime
from typing import cast

from app.db_schema import get_conn

IMAP_HOST = os.getenv("IMAP_HOST", None)
IMAP_USER = os.getenv("IMAP_USER", None)
IMAP_PASS = os.getenv("IMAP_PASS", None)

logger = logging.getLogger(__name__)


def fetch_unseen() -> None:
    if not all([IMAP_HOST, IMAP_USER, IMAP_PASS]):
        logger.warning("IMAP credentials are not fully set. Skipping email fetch.")
        return

    mail = imaplib.IMAP4_SSL(str(IMAP_HOST))
    mail.login(str(IMAP_USER), str(IMAP_PASS))
    mail.select("inbox")

    status, messages = mail.search(None, "UNSEEN")

    conn = get_conn()
    c = conn.cursor()

    for num in messages[0].split():
        _, msg_data = mail.fetch(num, "(RFC822)")

        if (
            msg_data is not None
            and len(msg_data) > 0
            and isinstance(msg_data[0], tuple)
            and len(msg_data[0]) > 1
            and isinstance(msg_data[0][1], bytes)
        ):
            msg = email.message_from_bytes(msg_data[0][1])

            content = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        content = cast(bytes, part.get_payload(decode=True)).decode(
                            errors="ignore"
                        )
            else:
                content = cast(bytes, msg.get_payload(decode=True)).decode(
                    errors="ignore"
                )

            msg_date = msg.get("Date")

            if msg_date is not None:
                received_on = datetime.strptime(
                    str(msg.get("Date")), "%a, %d %b %Y %H:%M:%S %z"
                )
                external_id = f"{num.decode()}-{msg.get('Message-ID', 'null')}-{received_on.timestamp()}"

                # Check if the email has already been processed
                c.execute(
                    "SELECT id FROM messages WHERE external_id = ?", (external_id,)
                )
                existing_message = c.fetchone()

                if existing_message:
                    logger.info(
                        "Email with external ID %s has already been processed.",
                        external_id,
                    )
                    continue

                msg_from = msg.get("From", "")
                msg_from_decoded = decode_header(msg_from)
                msg_from = msg_from_decoded[0][0]
                if isinstance(msg_from, bytes):
                    msg_from = msg_from.decode(msg_from_decoded[0][1] or "utf-8")

                msg_to = msg.get("To", "")
                msg_to_decoded = decode_header(msg_to)
                msg_to = msg_to_decoded[0][0]
                if isinstance(msg_to, bytes):
                    msg_to = msg_to.decode(msg_to_decoded[0][1] or "utf-8")

                msg_subject = msg.get("Subject", "")
                msg_subject_decoded = decode_header(msg_subject)
                msg_subject = msg_subject_decoded[0][0]
                if isinstance(msg_subject, bytes):
                    msg_subject = msg_subject.decode(
                        msg_subject_decoded[0][1] or "utf-8"
                    )

                # Insert the email into the database if it hasn't been processed
                c.execute(
                    """
                    INSERT INTO messages (source, received_on, external_id, from_address, to_address, subject, content, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "email",
                        received_on.astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                        external_id,
                        msg_from,
                        msg_to,
                        msg_subject,
                        content,
                        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                    ),
                )

    conn.commit()
    conn.close()
    mail.logout()
