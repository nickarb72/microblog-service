from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
ALLOWED_TYPES = ["image/jpeg", "image/png"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
