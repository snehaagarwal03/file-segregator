"""
config.py
Central place for all settings: folder paths, fixed category list,
confidence threshold, polling interval, and model name.

All path settings can be overridden via environment variables in .env
so nobody has to edit code after cloning.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env FIRST — before any os.getenv() calls below, so overrides apply
load_dotenv()

# ---- Base paths ----
BASE_DIR = Path(__file__).resolve().parent

# Folder the agent watches for new downloads.
# Default: the real ~/Downloads folder (cross-platform).
# Override by setting WATCH_FOLDER=/your/path in .env
WATCH_FOLDER = Path(os.getenv("WATCH_FOLDER", Path.home() / "Downloads"))

# Root folder where category subfolders are created (e.g. Resume/, Finance/).
# Default: ~/Downloads — category folders appear directly inside Downloads.
# Override by setting CATEGORIES_ROOT=/your/path in .env
CATEGORIES_ROOT = Path(os.getenv("CATEGORIES_ROOT", Path.home() / "Downloads"))

# SQLite database file used for dedup / processed-file tracking
DB_PATH = BASE_DIR / "state.db"

# Log file
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "activity.log"

# ---- Category hints for the LLM (not a fixed list — LLM can create new ones) ----
# These are examples shown in the prompt to guide naming style and conventions.
CATEGORY_HINTS = [
    "Resume", "JobDescription", "Finance", "Invoice", "Certificate",
    "Education", "Legal", "Personal", "Work", "ProjectReport", "Misc"
]

# Files below this confidence go to Needs-Review instead of their predicted category
CONFIDENCE_THRESHOLD = 0.70

# Name of the folder for low-confidence classifications
NEEDS_REVIEW_FOLDER = "Needs-Review"

# ---- Watcher behaviour ----
POLL_INTERVAL_SECONDS = 5           # how often we scan the watch folder
STABILITY_CHECKS = 1                # how many consecutive equal-size polls before a file is "stable"

# ---- LLM settings ----
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_CONTENT_CHARS = 8000            # truncate long documents before sending to the LLM

# ---- Supported file extensions ----
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf", ".docx"}


def ensure_folders_exist():
    """Create the log folder if missing.
    Category folders (Resume/, Finance/, etc.) are created on the spot
    when the first file is classified into that category.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORIES_ROOT.mkdir(parents=True, exist_ok=True)
