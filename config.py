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

# Root folder where sorted files end up (Finance/, Personal/, etc. created under here).
# Default: ~/Downloads/sorted/
# Override by setting SORTED_ROOT=/your/path in .env
SORTED_ROOT = Path(os.getenv("SORTED_ROOT", Path.home() / "Downloads" / "sorted"))

# SQLite database file used for dedup / processed-file tracking
DB_PATH = BASE_DIR / "state.db"

# Log file
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "activity.log"

# ---- Fixed category list (must match what the LLM is told to choose from) ----
CATEGORIES = ["Finance", "Personal", "Work", "Education", "Legal", "Misc"]

# Files below this confidence go to Needs-Review instead of their predicted category
CONFIDENCE_THRESHOLD = 0.70

# Name of the "quarantine" folder for low-confidence classifications
NEEDS_REVIEW_FOLDER = "Needs-Review"

# ---- Watcher behaviour ----
POLL_INTERVAL_SECONDS = 10          # how often we scan the watch folder
STABILITY_CHECKS = 1                # how many consecutive equal-size polls before a file is "stable"

# ---- LLM settings ----
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_CONTENT_CHARS = 8000            # truncate long documents before sending to the LLM

# ---- Supported file extensions ----
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf", ".docx"}


def ensure_folders_exist():
    """Create the sorted category folders and log folder if missing."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SORTED_ROOT.mkdir(parents=True, exist_ok=True)
    for category in CATEGORIES + [NEEDS_REVIEW_FOLDER]:
        (SORTED_ROOT / category).mkdir(parents=True, exist_ok=True)
