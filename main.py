"""
main.py
Entry point for the File Segregator agent.

Pipeline per file (Approach A - deterministic pipeline):
  watcher.scan_for_stable_files()   -> perceive
  state_store (hash + dedup check)  -> avoid reprocessing
  extractor.extract_text()          -> understand
  llm_agent.classify_and_name()     -> reason
  file_actions.move_file()          -> act
  state_store.mark_processed()      -> remember

Run with:
  uv run python main.py
  uv run python main.py --interval 15
  uv run python main.py --dry-run
  uv run python main.py --watch-folder /custom/path
"""

# load_dotenv() must be called BEFORE importing local modules (config.py reads
# env vars at import time, so the .env overrides must already be in the
# environment when config is first imported).
from dotenv import load_dotenv
load_dotenv()

import argparse
import logging
import time
from pathlib import Path

import schedule

import config
import state_store
from watcher import scan_for_stable_files
from extractor import extract_text
from llm_agent import classify_and_name
from file_actions import move_file


def setup_logging():
    logger = logging.getLogger("file_segregator")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(config.LOG_FILE)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def process_file(filepath, dry_run, logger):
    """Run one file through the full perceive -> reason -> act pipeline."""
    file_hash = state_store.get_file_hash(filepath)

    if state_store.is_already_processed(file_hash):
        logger.info(f"Skipping '{filepath.name}' - already processed (duplicate content).")
        return

    logger.info(f"Processing new file: {filepath.name}")

    content = extract_text(filepath)
    llm_result = classify_and_name(content, filepath.name)

    logger.info(
        f"LLM decision for '{filepath.name}': "
        f"name='{llm_result.get('new_name')}', "
        f"category='{llm_result.get('category')}', "
        f"confidence={llm_result.get('confidence')}"
    )

    original_name = filepath.name
    destination_path, final_category = move_file(filepath, llm_result, dry_run=dry_run)

    if not dry_run:
        state_store.mark_processed(
            file_hash=file_hash,
            original_name=original_name,
            new_name=destination_path.name,
            category=final_category,
            confidence=llm_result.get("confidence", 0.0),
        )


def run_cycle(dry_run, logger):
    """One polling tick: scan for stable files and process each one."""
    stable_files = scan_for_stable_files()
    if not stable_files:
        return
    for filepath in stable_files:
        try:
            process_file(filepath, dry_run, logger)
        except Exception as e:
            logger.error(f"Unexpected error processing '{filepath.name}': {e}")


def main():
    parser = argparse.ArgumentParser(description="File Segregator - AI-powered download folder organizer")
    parser.add_argument("--watch-folder", type=str, default=None, help="Folder to watch (overrides config/env)")
    parser.add_argument("--interval", type=int, default=None, help="Polling interval in seconds (overrides config/env)")
    parser.add_argument("--dry-run", action="store_true", help="Log decisions without actually moving files")
    args = parser.parse_args()

    # CLI flag takes highest priority over .env / config defaults
    if args.watch_folder:
        config.WATCH_FOLDER = Path(args.watch_folder)

    interval = args.interval or config.POLL_INTERVAL_SECONDS

    config.ensure_folders_exist()
    state_store.init_db()
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("File Segregator agent starting")
    logger.info(f"Watching:      {config.WATCH_FOLDER}")
    logger.info(f"Sorted output: {config.SORTED_ROOT}")
    logger.info(f"Polling every {interval} seconds | dry_run={args.dry_run}")
    logger.info("=" * 60)

    schedule.every(interval).seconds.do(run_cycle, dry_run=args.dry_run, logger=logger)

    # Run one cycle immediately on startup, then let the scheduler take over
    run_cycle(dry_run=args.dry_run, logger=logger)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("File Segregator agent stopped by user.")


if __name__ == "__main__":
    main()
