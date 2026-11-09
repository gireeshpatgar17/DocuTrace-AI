from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = DATA / "docutrace.sqlite3"
MAX_UPLOAD_MB = int(os.getenv("DOCUTRACE_MAX_UPLOAD_MB", "25"))
ELA_QUALITY = int(os.getenv("DOCUTRACE_ELA_QUALITY", "90"))
for folder in (DATA, DATA / "uploads", DATA / "processed", DATA / "reports", DATA / "demo"):
    folder.mkdir(parents=True, exist_ok=True)
