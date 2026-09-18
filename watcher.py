"""
watcher.py
Polls the watch folder on each tick and returns files that are:
1. Of a supported type
2. "Stable" - their size hasn't changed since the previous poll, meaning
   the download has finished (avoids grabbing a half-downloaded file).

This module only detects and reports files - it never reads content or
touches the filesystem beyond checking size, keeping "perceive" separate
from "reason" and "act".
"""

import logging

from config import WATCH_FOLDER, SUPPORTED_EXTENSIONS

logger = logging.getLogger("file_segregator")

# Tracks the last-seen size of each candidate file across polls: {path_str: size}
_last_seen_sizes = {}


def scan_for_stable_files():
    """Return a list of Path objects for files that are stable and ready to process."""
    stable_files = []
    current_files = [
        f for f in WATCH_FOLDER.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    current_paths = {str(f) for f in current_files}

    # Forget files that disappeared (already moved, or deleted) since last poll
    for tracked_path in list(_last_seen_sizes.keys()):
        if tracked_path not in current_paths:
            del _last_seen_sizes[tracked_path]

    for filepath in current_files:
        path_str = str(filepath)
        try:
            current_size = filepath.stat().st_size
        except FileNotFoundError:
            continue  # file vanished mid-scan, skip safely

        previous_size = _last_seen_sizes.get(path_str)

        if previous_size is not None and previous_size == current_size:
            # Size unchanged since last poll -> download/write has finished
            stable_files.append(filepath)
            del _last_seen_sizes[path_str]  # stop tracking, it's about to be processed
        else:
            # First time seeing it, or still growing -> track and wait one more poll
            _last_seen_sizes[path_str] = current_size
            logger.info(f"Waiting for '{filepath.name}' to finish writing (size check)...")

    return stable_files
