from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
UPLOAD_DIR = BACKEND_DIR / "uploads"


def ensure_env_loaded() -> None:
    load_dotenv(dotenv_path=ENV_FILE)
