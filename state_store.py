"""
state_store.py
Tracks which files have already been processed, keyed by content hash
(not filename), so the agent never re-renames/re-moves the same file twice.
Uses SQLite - a single local .db file, no separate server needed.
"""

import sqlite3
import hashlib
from datetime import datetime

from config import DB_PATH


def init_db():
    """Create the processed_files table if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_files (
            file_hash TEXT PRIMARY KEY,
            original_name TEXT,
            new_name TEXT,
            category TEXT,
            confidence REAL,
            processed_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_file_hash(filepath):
    """Return a SHA-256 hash of the file's content, used as a unique fingerprint."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_already_processed(file_hash):
    """Return True if a file with this content hash has already been handled."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT 1 FROM processed_files WHERE file_hash = ?", (file_hash,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def mark_processed(file_hash, original_name, new_name, category, confidence):
    """Record a file as processed so it's never picked up again."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT OR REPLACE INTO processed_files
        (file_hash, original_name, new_name, category, confidence, processed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (file_hash, original_name, new_name, category, confidence, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
