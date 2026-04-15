import os
import sys

from pathlib import Path
from dotenv import load_dotenv

load_dotenv("../.env", override=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    from app.processor import process
    from app.logging_config import setup_logging

    setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

    process()
