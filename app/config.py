import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=False)


class Config:
    BACKEND = os.environ.get("DDMRP_BACKEND", "sqlite").lower()
    SQLITE_PATH = os.environ.get("SQLITE_PATH", str(PROJECT_ROOT / "app" / "data" / "ddmrp.db"))
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
    SAMPLE_CSV_PATH = str(PROJECT_ROOT / "static" / "uploads" / "sample" / "seed.csv")
