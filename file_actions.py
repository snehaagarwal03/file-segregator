"""
file_actions.py
The only module that mutates the filesystem: sanitizes the LLM-generated name,
resolves filename collisions, and moves the file into the correct category
folder - or into Needs-Review if the LLM's confidence was too low.
"""

import re
import shutil
import logging

from config import CATEGORIES_ROOT, NEEDS_REVIEW_FOLDER, CONFIDENCE_THRESHOLD

logger = logging.getLogger("file_segregator")


def sanitize_name(name):
    """Lowercase, strip anything that isn't a-z, 0-9, or hyphen."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "unnamed-file"


def resolve_collision(destination_folder, base_name, extension):
    """If base_name already exists in the destination, append -1, -2, etc."""
    candidate = destination_folder / f"{base_name}{extension}"
    counter = 1
    while candidate.exists():
        candidate = destination_folder / f"{base_name}-{counter}{extension}"
        counter += 1
    return candidate


def move_file(filepath, llm_result, dry_run=False):
    """Move filepath into the correct sorted folder based on the LLM decision.
    Returns (destination_path, final_category) for logging/state purposes.
    """
    confidence = llm_result.get("confidence", 0.0)
    category = llm_result.get("category", "Misc")
    raw_name = llm_result.get("new_name", filepath.stem)

    # Confidence gate: uncertain classifications go to Needs-Review instead
    # of being filed under a possibly-wrong category.
    if confidence < CONFIDENCE_THRESHOLD:
        final_category = NEEDS_REVIEW_FOLDER
        logger.info(
            f"Confidence {confidence:.2f} below threshold ({CONFIDENCE_THRESHOLD}) "
            f"-> routing '{filepath.name}' to {NEEDS_REVIEW_FOLDER}"
        )
    else:
        final_category = category

    clean_name = sanitize_name(raw_name)
    destination_folder = CATEGORIES_ROOT / final_category
    # Create the category folder on the spot if it doesn't exist yet
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination_path = resolve_collision(destination_folder, clean_name, filepath.suffix.lower())

    if dry_run:
        logger.info(f"[DRY RUN] Would move '{filepath.name}' -> '{destination_path}'")
    else:
        shutil.move(str(filepath), str(destination_path))
        logger.info(f"Moved '{filepath.name}' -> '{destination_path}'")

    return destination_path, final_category
