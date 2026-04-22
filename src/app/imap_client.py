import imaplib
import json
import logging
import re

from email.header import decode_header
from email.message import Message
from email.parser import BytesParser
from email.policy import default
from email.utils import getaddresses, parsedate_to_datetime
from datetime import datetime
from typing import cast

from app.db.database import session_scope
from app.message_filter import (
    DEFAULT_FILTER_KEYS,
    classify_message,
    save_message_filters,
)
from app.repository import (
    MessageAddressRepository,
    MessageAttachmentRepository,
    MessageRepository,
    RawMessageRepository,
)
from app.services import ServiceConfiguration

"""
This module connects to an IMAP email server, fetches unseen emails from a specified mailbox, and processes each email to extract its content and metadata. 
The extracted information is then stored in a SQLite database for further analysis and task extraction. 
The module handles various email formats, including multipart messages with attachments, and decodes MIME-encoded headers to ensure accurate data extraction.
It also logs the processing of each email, including any errors encountered during fetching or parsing.
"""

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
    return json.dumps(headers, ensure_ascii=True, default=str)


def _raw_headers_text(msg: Message) -> str:
    """Returns the raw header text of an email message."""

    return "".join(f"{key}: {value}\n" for key, value in msg.raw_items())


def _parse_internal_date(fetch_response: bytes | str) -> datetime | None:
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

    return internal_date.astimezone()


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

    mailbox_cfg = ServiceConfiguration().get_mailbox_runtime_config()
    if not all([mailbox_cfg.imap_host, mailbox_cfg.imap_username, mailbox_cfg.imap_password]):
        logger.warning("IMAP credentials are not fully set. Skipping email fetch.")
        return summary

    mail = imaplib.IMAP4_SSL(mailbox_cfg.imap_host, mailbox_cfg.imap_port)

    try:
        mail.login(mailbox_cfg.imap_username, mailbox_cfg.imap_password)
        mail.select(mailbox_cfg.mailbox_name)

        status, message_numbers = mail.search(None, "UNSEEN")
        if status != "OK":
            logger.error("IMAP search failed with status: %s", status)
            return summary

        candidate_numbers = message_numbers[0].split()
        if limit is not None:
            candidate_numbers = candidate_numbers[:limit]
        summary["selected"] = len(candidate_numbers)

        with session_scope() as session:
            with MessageRepository(session) as message_repo:
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
                    account_id = mailbox_cfg.account_id or mailbox_cfg.imap_username
                    mailbox = mailbox_cfg.mailbox_name
                    imap_uid = _parse_uid(response_metadata) or num.decode()

                    # Check for duplicates
                    existing_message = message_repo.get_message_by_message_id_or_uid(
                        message_id=message_id,
                        account_id=account_id,
                        mailbox=mailbox,
                        imap_uid=imap_uid,
                    )
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
                        message_date if message_date is not None else datetime.now()
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

                    # Insert message
                    message_data = message_repo.create_message(
                        source="email",
                        account_id=account_id,
                        mailbox=mailbox,
                        imap_uid=imap_uid,
                        external_id=external_id,
                        message_id=message_id,
                        thread_key=thread_key,
                        in_reply_to=_decode_mime_value(msg.get("In-Reply-To")) or None,
                        references_header=_decode_mime_value(msg.get("References"))
                        or None,
                        from_name=from_name or None,
                        from_email=from_email or None,
                        subject=subject or None,
                        received_on=received_on,
                        message_date=received_on if message_date is not None else None,
                        imap_internal_date=internal_date,
                        importance=importance,
                        flags_json=json.dumps(flags, ensure_ascii=True, default=str),
                        has_attachments=1 if attachments else 0,
                        attachment_count=len(attachments),
                        size_bytes=len(raw_rfc822),
                        body_text_raw=body_text_raw or None,
                        body_html_raw=body_html_raw or None,
                        body_text_clean=body_text_clean or None,
                        headers_json=header_json,
                        status="pending",
                    )
                    message_row_id = message_data["id"]

                    # Insert raw message
                    with RawMessageRepository(session) as raw_repo:
                        raw_repo.create_raw_message(
                            message_id=message_row_id,
                            raw_rfc822=raw_rfc822,
                            raw_headers=raw_headers,
                        )

                    # Insert addresses
                    address_groups = {
                        "from": from_addresses,
                        "sender": _parse_address_header(msg, "Sender"),
                        "to": _parse_address_header(msg, "To"),
                        "cc": _parse_address_header(msg, "Cc"),
                        "bcc": _parse_address_header(msg, "Bcc"),
                        "reply_to": _parse_address_header(msg, "Reply-To"),
                    }
                    with MessageAddressRepository(session) as addr_repo:
                        for role, addresses in address_groups.items():
                            for display_name, email_address in addresses:
                                addr_repo.create_address(
                                    message_id=message_row_id,
                                    address_role=role,
                                    display_name=display_name or None,
                                    email_address=email_address,
                                )

                    # Insert attachments
                    with MessageAttachmentRepository(session) as attach_repo:
                        for attachment in attachments:
                            attach_repo.create_attachment(
                                message_id=message_row_id,
                                part_index=cast(int, attachment["part_index"] or 0),
                                content_id=str(attachment["content_id"]),
                                filename=str(attachment["filename"]),
                                filename_normalized=str(
                                    attachment["filename_normalized"]
                                ),
                                mime_type=str(attachment["mime_type"]),
                                disposition=str(attachment["disposition"]),
                                is_inline=bool(attachment["is_inline"]),
                                size_bytes=cast(int, attachment["size_bytes"] or 0),
                                extraction_method="none",
                                extraction_status="pending",
                            )

                    summary["fetched"] += 1

                    if filter_messages and message_row_id is not None:
                        selected_filters = filter_keys or DEFAULT_FILTER_KEYS
                        classification = classify_message(
                            message_row_id,
                            from_email or "",
                            subject or "",
                            body_text_clean or body_text_raw or body_html_raw or "",
                            selected_filters,
                            account_id=account_id,
                            mailbox_name=mailbox,
                        )
                        if classification is None:
                            summary["filter_errors"] += 1
                        else:
                            save_message_filters(
                                message_row_id,
                                classification["filters"],
                            )
                            summary["filtered"] += 1
    finally:
        mail.logout()

    return summary
