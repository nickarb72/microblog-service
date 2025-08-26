import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

UPLOADS_DIR = (PROJECT_ROOT / Path(os.getenv("UPLOADS_DIR", "uploads"))).resolve()

ALLOWED_TYPES = os.getenv("ALLOWED_TYPES")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))

MAX_TEXT_SIZE = 280
MAX_FILE_SIZE_MB = MAX_FILE_SIZE // 1024 // 1024
