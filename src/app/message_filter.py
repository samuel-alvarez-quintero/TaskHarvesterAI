import json
import logging
import re
from datetime import datetime
from typing import Any

from app.db.sqlite.database import get_conn
from app.llm import get_llm

logger = logging.getLogger(__name__)

FILTER_DEFINITIONS: dict[str, dict[str, str]] = {
    "spam": {
        "description": "Clasificar como correo no deseado o spam.",
        "definition": "spam: correo no deseado, publicitario o no solicitado.",
    },
    "phishing": {
        "description": "Clasificar intentos de suplantación de identidad o robo de credenciales.",
        "definition": "phishing: intenta robar credenciales, información financiera o suplantar identidad.",
    },
    "malware": {
        "description": "Clasificar correos con enlaces o adjuntos maliciosos.",
        "definition": "malware: contiene adjuntos o enlaces maliciosos que pueden infectar el equipo.",
    },
    "important": {
        "description": "Clasificar como correo importante para generar tareas.",
        "definition": "important: requiere seguimiento y puede generar tareas o acciones.",
    },
}
DEFAULT_FILTER_KEYS = list(FILTER_DEFINITIONS)


def _build_filter_prompt(
    sender: str,
    subject: str,
    message_text: str,
    filter_keys: list[str],
) -> str:
    active_definitions = [FILTER_DEFINITIONS[key]["definition"] for key in filter_keys]
    prompt_filters = "\n".join(f"- {definition}" for definition in active_definitions)
    expected_keys = ", ".join(f'"{key}"' for key in filter_keys)

    return f"""
Responde en español.
Devuelve únicamente JSON válido y no agregues texto fuera del objeto JSON.
Analiza el siguiente correo y determina si corresponde a cada uno de estos indicadores:
{prompt_filters}

La respuesta debe ser un objeto JSON con claves: {expected_keys}.
Cada valor debe ser true o false.

Remitente: {sender}
Asunto: {subject}
Mensaje:
{message_text}
""".strip()


def _parse_filter_response(
    response: str, filter_keys: list[str]
) -> dict[str, bool] | None:
    if not response:
        return None

    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.S)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    results: dict[str, bool] = {}
    for key in filter_keys:
        value = payload.get(key)
        results[key] = bool(value) if isinstance(value, (bool, int, str)) else False
        if isinstance(value, str):
            lower_value = value.strip().lower()
            results[key] = lower_value in ("true", "1", "sí", "si", "verdadero")

    return results


def classify_message(
    msg_id: int,
    sender: str,
    subject: str,
    message_text: str,
    filter_keys: list[str] | None = None,
) -> dict[str, Any] | None:
    filter_keys = filter_keys or DEFAULT_FILTER_KEYS
    filter_keys = [key for key in filter_keys if key in FILTER_DEFINITIONS]
    if not filter_keys:
        return None

    prompt = _build_filter_prompt(sender, subject, message_text, filter_keys)

    try:
        result = get_llm().generate(prompt, msg_id, operation="classify_message")
    except ValueError as exc:
        logger.error("Error clasificando mensaje %s: %s", msg_id, exc)
        return None

    filter_response = _parse_filter_response(result.get("response", ""), filter_keys)
    if filter_response is None:
        logger.error(
            "No se pudo parsear la respuesta de clasificación para el mensaje %s",
            msg_id,
        )
        return None

    return {
        "msg_id": msg_id,
        "ai_log_id": result.get("ai_log_id"),
        "filters": filter_response,
    }


def save_message_filters(
    message_row_id: int,
    filter_values: dict[str, bool],
    ai_log_id: int | None = None,
) -> None:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    with get_conn() as conn:
        c = conn.cursor()
        for filter_name, filter_value in filter_values.items():
            if filter_name not in FILTER_DEFINITIONS:
                continue

            c.execute(
                """
                INSERT INTO message_filters (
                    message_row_id,
                    filter_name,
                    filter_value,
                    confidence,
                    reason,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_row_id, filter_name) DO UPDATE SET
                    filter_value = excluded.filter_value,
                    confidence = excluded.confidence,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (
                    message_row_id,
                    filter_name,
                    1 if filter_value else 0,
                    None,
                    None,
                    now,
                    now,
                ),
            )

        conn.commit()


def filter_messages(
    filter_keys: list[str] | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    selected_filters = filter_keys or DEFAULT_FILTER_KEYS
    selected_filters = [key for key in selected_filters if key in FILTER_DEFINITIONS]
    summary = {
        "selected": 0,
        "filtered": 0,
        "errors": 0,
    }

    rows: list[tuple[int, str, str, str]] = []
    with get_conn() as conn:
        c = conn.cursor()
        query = """
            SELECT id, COALESCE(from_email, ''), COALESCE(subject, ''),
                   COALESCE(body_text_clean, body_text_raw, body_html_raw, '')
            FROM messages
            WHERE status IN ('pending', 'processing', 'error')
            ORDER BY received_on DESC
        """
        if limit is not None:
            query += " LIMIT ?"
            c.execute(query, (limit,))
        else:
            c.execute(query)
        rows = c.fetchall()

    summary["selected"] = len(rows)

    for msg_id, sender, subject, message_text in rows:
        if not message_text.strip():
            summary["errors"] += 1
            continue

        classification = classify_message(
            msg_id, sender or "", subject or "", message_text, selected_filters
        )
        if classification is None:
            summary["errors"] += 1
            continue

        save_message_filters(
            msg_id, classification["filters"], classification.get("ai_log_id")
        )
        summary["filtered"] += 1

    return summary
