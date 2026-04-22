FILTER_JSON_SCHEMA = """{
  "spam": true|false,
  "phishing": true|false,
  "malware": true|false,
  "important": true|false
}"""

FILTER_CONTEXT_TEMPLATE = "Sender: {sender}\\nSubject: {subject}"
FILTER_MESSAGE_TEMPLATE = "{message_text}"
FILTER_DEFAULT_INSTRUCTIONS = (
    "Classify the message according to the configured indicators and return only valid JSON."
)

EXTRACT_JSON_SCHEMA = """{
  "task_group_info": {
    "name": "...",
    "name_slug": "...",
    "requested_on": "%Y-%m-%d %H:%M:%S%z",
    "expected_delivery_date": "%Y-%m-%d %H:%M:%S%z or null",
    "priority": "low|medium|high",
    "status": "pending|in_progress|completed"
  },
  "client_info": {
    "name": "...",
    "name_slug": "...",
    "emails": ["..."],
    "phone_numbers": ["..."]
  },
  "tasks": [
    {
      "content": "...",
      "requested_on": "%Y-%m-%d %H:%M:%S%z",
      "expected_delivery_date": "%Y-%m-%d %H:%M:%S%z or null",
      "priority": "low|medium|high",
      "status": "pending|in_progress|completed"
    }
  ]
}"""

EXTRACT_CONTEXT_TEMPLATE = "{context_json}\\nSender: {sender}\\nSubject: {subject}"
EXTRACT_MESSAGE_TEMPLATE = "{message_text}"
EXTRACT_DEFAULT_INSTRUCTIONS = (
    "Extract actionable tasks, avoid duplicates already present in context, and return only valid JSON."
)
