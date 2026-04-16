from email.header import decode_header
from email.message import Message
from email.parser import BytesParser
from email.policy import default
from email.utils import getaddresses, parsedate_to_datetime
import imaplib
import json
import logging
import re
from datetime import datetime
from typing import cast

from app.config import settings
from app.db.sqlite.database import get_conn
from app.message_filter import (
    DEFAULT_FILTER_KEYS,
    classify_message,
    save_message_filters,
)

"""
This module connects to an IMAP email server, fetches unseen emails from a specified mailbox, and processes each email to extract its content and metadata. 
The extracted information is then stored in a SQLite database for further analysis and task extraction. 
The module handles various email formats, including multipart messages with attachments, and decodes MIME-encoded headers to ensure accurate data extraction.
It also logs the processing of each email, including any errors encountered during fetching or parsing.
"""

IMAP_HOST = settings.imap_host
IMAP_USER = settings.imap_user
IMAP_PASS = settings.imap_pass
IMAP_MAILBOX = settings.imap_mailbox

logger = logging.getLogger(__name__)


def _decode_mime_value(value: str | None) -> str:
    """Decodes MIME-encoded header values, handling multiple encoded parts and different character sets."""

    if not value:
        return ""

    decoded_chunks: list[str] = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            decoded_chunks.append(chunk.decode(encoding or "utf-8", errors="ignore"))
        else:
            decoded_chunks.append(chunk)
    return "".join(decoded_chunks).strip()


def _parse_address_header(msg: Message, header_name: str) -> list[tuple[str, str]]:
    """
    Parses email address headers (e.g., From, To, Cc) and returns a list of tuples containing display names and email addresses.
    It handles MIME-encoded display names and normalizes email addresses to lowercase.
    """

    header_value = msg.get(header_name, "")
    addresses = getaddresses([header_value])

    parsed_addresses: list[tuple[str, str]] = []
    for display_name, email_address in addresses:
        normalized_email = email_address.strip().lower()
        if not normalized_email:
            continue
        parsed_addresses.append((_decode_mime_value(display_name), normalized_email))

    return parsed_addresses


def _extract_bodies(msg: Message) -> tuple[str, str]:
    """Extracts the plain text and HTML bodies from an email message, handling multipart structures and character encodings."""

    text_parts: list[str] = []
    html_parts: list[str] = []

    if not msg.is_multipart():
        payload = msg.get_payload(decode=True)
        if payload is None:
            return "", ""

        charset = msg.get_content_charset() or "utf-8"
        decoded_payload = cast(bytes, payload).decode(charset, errors="ignore")
        if msg.get_content_type() == "text/html":
            return "", decoded_payload.strip()
        return decoded_payload.strip(), ""

    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            continue

        payload = part.get_payload(decode=True)
        if payload is None:
            continue

        charset = part.get_content_charset() or "utf-8"
        decoded_payload = cast(bytes, payload).decode(charset, errors="ignore")

        if part.get_content_type() == "text/plain":
            text_parts.append(decoded_payload)
        elif part.get_content_type() == "text/html":
            html_parts.append(decoded_payload)

    return "\n".join(text_parts).strip(), "\n".join(html_parts).strip()


def _extract_attachments(msg: Message) -> list[dict[str, object]]:
    """Extracts attachment information from an email message."""

    attachments: list[dict[str, object]] = []

    for index, part in enumerate(msg.walk()):
        disposition = part.get_content_disposition()
        filename = _decode_mime_value(part.get_filename())
        content_type = part.get_content_type()
        content_id = part.get("Content-ID")

        is_attachment = disposition == "attachment"
        is_inline_file = disposition == "inline" and (
            filename or content_id or not content_type.startswith("text/")
        )
        if not is_attachment and not is_inline_file:
            continue

        payload = part.get_payload(decode=True) or b""
        attachments.append(
            {
                "part_index": index,
                "content_id": content_id,
                "filename": filename or None,
                "filename_normalized": filename.lower() if filename else None,
                "mime_type": content_type,
                "disposition": disposition,
                "is_inline": 1 if disposition == "inline" else 0,
                "size_bytes": len(payload),
            }
        )

    return attachments


def _serialize_headers(msg: Message) -> str:
    """Serializes email headers into a JSON string."""

    headers = [
        {"name": key, "value": _decode_mime_value(value)} for key, value in msg.items()
    ]
    return json.dumps(headers, ensure_ascii=True)


def _raw_headers_text(msg: Message) -> str:
    """Returns the raw header text of an email message."""

    return "".join(f"{key}: {value}\n" for key, value in msg.raw_items())


def _parse_internal_date(fetch_response: bytes | str) -> str | None:
    """Parses the internal date from an IMAP fetch response."""

    response_text = (
        fetch_response.decode("utf-8", errors="ignore")
        if isinstance(fetch_response, bytes)
        else fetch_response
    )
    match = re.search(r'INTERNALDATE "([^"]+)"', response_text)
    if not match:
        return None

    try:
        internal_date = parsedate_to_datetime(match.group(1))
    except (TypeError, ValueError):
        return None

    return internal_date.astimezone().strftime("%Y-%m-%d %H:%M:%S%z")


def _parse_flags(fetch_response: bytes | str) -> list[str]:
    """Parses the flags from an IMAP fetch response."""

    response_text = (
        fetch_response.decode("utf-8", errors="ignore")
        if isinstance(fetch_response, bytes)
        else fetch_response
    )
    match = re.search(r"FLAGS \(([^)]*)\)", response_text)
    if not match:
        return []

    flags = [flag.strip() for flag in match.group(1).split() if flag.strip()]
    return flags


def _parse_uid(fetch_response: bytes | str) -> str | None:
    """Parses the UID from an IMAP fetch response."""

    response_text = (
        fetch_response.decode("utf-8", errors="ignore")
        if isinstance(fetch_response, bytes)
        else fetch_response
    )
    match = re.search(r"UID (\d+)", response_text)
    if not match:
        return None
    return match.group(1)


def fetch_unseen(
    limit: int | None = None,
    filter_messages: bool = False,
    filter_keys: list[str] | None = None,
) -> dict[str, int]:
    """Connects to the IMAP server, fetches unseen emails from the specified mailbox, and stores their content and metadata in the database."""

    summary = {
        "selected": 0,
        "fetched": 0,
        "duplicates": 0,
        "fetch_errors": 0,
        "invalid_payloads": 0,
        "filtered": 0,
        "filter_errors": 0,
    }

    if not all([IMAP_HOST, IMAP_USER, IMAP_PASS]):
        logger.warning("IMAP credentials are not fully set. Skipping email fetch.")
        return summary

    mail = imaplib.IMAP4_SSL(str(IMAP_HOST))

    try:
        mail.login(str(IMAP_USER), str(IMAP_PASS))
        mail.select(IMAP_MAILBOX)

        status, message_numbers = mail.search(None, "UNSEEN")
        if status != "OK":
            logger.error("IMAP search failed with status: %s", status)
            return summary

        candidate_numbers = message_numbers[0].split()
        if limit is not None:
            candidate_numbers = candidate_numbers[:limit]
        summary["selected"] = len(candidate_numbers)

        with get_conn() as conn:
            c = conn.cursor()

            for num in candidate_numbers:
                fetch_status, msg_data = mail.fetch(
                    num, "(UID RFC822 FLAGS INTERNALDATE)"
                )
                if fetch_status != "OK":
                    logger.warning("Failed to fetch email number %s", num.decode())
                    summary["fetch_errors"] += 1
                    continue

                if (
                    msg_data is None
                    or len(msg_data) == 0
                    or not isinstance(msg_data[0], tuple)
                    or len(msg_data[0]) < 2
                    or not isinstance(msg_data[0][1], bytes)
                ):
                    logger.warning(
                        "Unexpected IMAP payload for email number %s", num.decode()
                    )
                    summary["invalid_payloads"] += 1
                    continue

                response_metadata = msg_data[0][0]
                raw_rfc822 = msg_data[0][1]
                msg = BytesParser(policy=default).parsebytes(raw_rfc822)

                message_id = _decode_mime_value(msg.get("Message-ID")) or None
                account_id = str(IMAP_USER)
                mailbox = IMAP_MAILBOX
                imap_uid = _parse_uid(response_metadata) or num.decode()

                if message_id:
                    c.execute(
                        "SELECT id FROM messages WHERE message_id = ?",
                        (message_id,),
                    )
                else:
                    c.execute(
                        """
                        SELECT id FROM messages
                        WHERE account_id = ? AND mailbox = ? AND imap_uid = ?
                        """,
                        (account_id, mailbox, imap_uid),
                    )
                conn.commit()

                existing_message = c.fetchone()
                if existing_message:
                    logger.info(
                        "Email already ingested | message_id=%s | imap_uid=%s",
                        message_id,
                        imap_uid,
                    )
                    summary["duplicates"] += 1
                    continue

                body_text_raw, body_html_raw = _extract_bodies(msg)
                body_text_clean = body_text_raw.strip()
                attachments = _extract_attachments(msg)
                header_json = _serialize_headers(msg)
                raw_headers = _raw_headers_text(msg)

                try:
                    message_date = (
                        parsedate_to_datetime(str(msg.get("Date")))
                        if msg.get("Date")
                        else None
                    )
                except (TypeError, ValueError):
                    message_date = None

                received_on = (
                    message_date.astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
                    if message_date is not None
                    else datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
                )

                internal_date = _parse_internal_date(response_metadata)
                flags = _parse_flags(response_metadata)
                subject = _decode_mime_value(msg.get("Subject"))

                from_addresses = _parse_address_header(msg, "From")
                from_name, from_email = (
                    from_addresses[0] if from_addresses else ("", "")
                )
                importance = (
                    _decode_mime_value(msg.get("Importance"))
                    or _decode_mime_value(msg.get("X-Priority"))
                    or None
                )

                thread_key = (
                    _decode_mime_value(msg.get("Thread-Topic"))
                    or _decode_mime_value(msg.get("In-Reply-To"))
                    or message_id
                    or subject
                    or f"{account_id}:{mailbox}:{imap_uid}"
                )
                external_id = f"{account_id}:{mailbox}:{imap_uid}"

                c.execute(
                    """
                    INSERT INTO messages (
                        source,
                        account_id,
                        mailbox,
                        imap_uid,
                        external_id,
                        message_id,
                        thread_key,
                        in_reply_to,
                        references_header,
                        from_name,
                        from_email,
                        subject,
                        received_on,
                        message_date,
                        imap_internal_date,
                        importance,
                        flags_json,
                        has_attachments,
                        attachment_count,
                        size_bytes,
                        body_text_raw,
                        body_html_raw,
                        body_text_clean,
                        headers_json,
                        status,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "email",
                        account_id,
                        mailbox,
                        imap_uid,
                        external_id,
                        message_id,
                        thread_key,
                        _decode_mime_value(msg.get("In-Reply-To")) or None,
                        _decode_mime_value(msg.get("References")) or None,
                        from_name or None,
                        from_email or None,
                        subject or None,
                        received_on,
                        received_on if message_date is not None else None,
                        internal_date,
                        importance,
                        json.dumps(flags, ensure_ascii=True),
                        1 if attachments else 0,
                        len(attachments),
                        len(raw_rfc822),
                        body_text_raw or None,
                        body_html_raw or None,
                        body_text_clean or None,
                        header_json,
                        "pending",
                        datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
                    ),
                )
                message_row_id = c.lastrowid

                c.execute(
                    """
                    INSERT INTO raw_messages (message_row_id, raw_rfc822, raw_headers)
                    VALUES (?, ?, ?)
                    """,
                    (message_row_id, raw_rfc822, raw_headers),
                )

                address_groups = {
                    "from": from_addresses,
                    "sender": _parse_address_header(msg, "Sender"),
                    "to": _parse_address_header(msg, "To"),
                    "cc": _parse_address_header(msg, "Cc"),
                    "bcc": _parse_address_header(msg, "Bcc"),
                    "reply_to": _parse_address_header(msg, "Reply-To"),
                }
                for role, addresses in address_groups.items():
                    for display_name, email_address in addresses:
                        c.execute(
                            """
                            INSERT INTO message_addresses (
                                message_row_id,
                                address_role,
                                display_name,
                                email_address
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (message_row_id, role, display_name or None, email_address),
                        )

                for attachment in attachments:
                    c.execute(
                        """
                        INSERT INTO message_attachments (
                            message_row_id,
                            part_index,
                            content_id,
                            filename,
                            filename_normalized,
                            mime_type,
                            disposition,
                            is_inline,
                            size_bytes,
                            extraction_method,
                            extraction_status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            message_row_id,
                            attachment["part_index"],
                            attachment["content_id"],
                            attachment["filename"],
                            attachment["filename_normalized"],
                            attachment["mime_type"],
                            attachment["disposition"],
                            attachment["is_inline"],
                            attachment["size_bytes"],
                            "none",
                            "pending",
                        ),
                    )
                summary["fetched"] += 1

                conn.commit()

                if filter_messages and message_row_id is not None:
                    selected_filters = filter_keys or DEFAULT_FILTER_KEYS
                    classification = classify_message(
                        message_row_id,
                        from_email or "",
                        subject or "",
                        body_text_clean or body_text_raw or body_html_raw or "",
                        selected_filters,
                    )
                    if classification is None:
                        summary["filter_errors"] += 1
                    else:
                        save_message_filters(
                            message_row_id,
                            classification["filters"],
                        )
                        summary["filtered"] += 1

            conn.commit()
    finally:
        mail.logout()

    return summary
