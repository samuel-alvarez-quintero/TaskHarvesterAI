import requests
import os
from dotenv import load_dotenv

load_dotenv()

def extract_tasks(text):
    prompt = f"""
Analiza el mensaje y devuelve JSON válido:

{{
 "tasks": ["..."],
 "priority": "low|medium|high"
}}

Mensaje:
{text}
"""

    res = requests.post(
        f"{os.getenv('OLLAMA_URL')}/api/generate",
        json={
            "model": os.getenv("MODEL"),
            "prompt": prompt,
            "stream": False
        }
    )

    return res.json()["response"]