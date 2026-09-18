# File Segregator 🗂️

An AI-powered agent that watches your **Downloads folder**, reads each new file's content, uses an LLM to generate a concise 3-word descriptive name, and automatically moves it into the right category folder — **Finance, Work, Education, Personal, Legal, or Misc**.

Built with Python + [Groq](https://console.groq.com) (LLaMA 3.3 70B).

---

## How it works

```
~/Downloads (watched every 10s)
        │
        ▼
[Stability check] — wait for file size to stop changing (avoids half-downloads)
        │
        ▼
[Content extraction] — reads .txt / .md / .csv / .pdf / .docx
        │
        ▼
[LLM reasoning] — Groq / LLaMA-3.3-70b returns:
                   { "new_name": "bank-loan-statement",
                     "category": "Finance",
                     "confidence": 0.95 }
        │
        ├─ confidence ≥ 0.70 → ~/Downloads/sorted/Finance/bank-loan-statement.pdf
        └─ confidence < 0.70 → ~/Downloads/sorted/Needs-Review/  (human reviews)
```

**Key engineering choices:**
- **Structured JSON output** — `response_format={"type": "json_object"}` enforced at the API level, so no regex parsing
- **Fixed category taxonomy** with few-shot examples in the system prompt for consistent classification
- **Hash-based dedup** in SQLite — the agent never reprocesses a file it's already handled
- **File-stability check** — waits for file size to stabilise before reading (safe for active downloads)
- **Confidence gate** — low-confidence files go to `Needs-Review` instead of being silently misfiled

---

## Prerequisites

| Tool | Install |
|---|---|
| Python 3.11+ | Pre-installed on most Macs, or `uv python install 3.11` |
| [uv](https://docs.astral.sh/uv/) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Groq API key | Free at [console.groq.com/keys](https://console.groq.com/keys) |

---

## Setup (copy-paste)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/file-segregator.git
cd file-segregator

# 2. Create the virtual environment and install dependencies
uv sync

# 3. Set up your API key
cp .env.example .env
# Open .env and replace 'your_groq_api_key_here' with your actual key
```

That's it. No other config needed — the agent watches `~/Downloads` by default.

---

## Running

```bash
# Dry run — shows what it WOULD do, no files are actually moved (great for testing)
uv run python main.py --dry-run

# Normal run — watches ~/Downloads and organises files in real time
uv run python main.py

# Override the poll interval (default: 10 seconds)
uv run python main.py --interval 5

# Watch a different folder (overrides .env setting)
uv run python main.py --watch-folder /path/to/folder
```

Press `Ctrl+C` to stop the agent.

---

## Configuration

All settings can be changed in `.env` — **no code editing needed**:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `WATCH_FOLDER` | `~/Downloads` | Folder the agent monitors |
| `SORTED_ROOT` | `~/Downloads/sorted` | Root folder for organised output |

Example `.env`:
```bash
GROQ_API_KEY=gsk_abc123...
WATCH_FOLDER=/Users/yourname/Downloads
SORTED_ROOT=/Users/yourname/Downloads/sorted
```

---

## Output structure

After running, sorted files appear in:

```
~/Downloads/sorted/
├── Finance/          # invoices, bank statements, tax docs
├── Work/             # meeting notes, reports, presentations
├── Education/        # syllabi, lecture notes, research papers
├── Personal/         # letters, photos descriptions, personal docs
├── Legal/            # contracts, agreements, forms
├── Misc/             # anything that doesn't fit cleanly
└── Needs-Review/     # low-confidence classifications for you to check
```

---

## Supported file types

| Extension | Extraction method |
|---|---|
| `.txt` `.md` `.csv` | Direct text read |
| `.pdf` | `pdfplumber` (text-layer PDFs) |
| `.docx` | `python-docx` |

---

## Project structure

```
file-segregator/
├── .env.example        # Copy to .env and add your API key
├── pyproject.toml      # uv project manifest + dependencies
├── config.py           # All settings (paths, categories, thresholds)
├── main.py             # Entry point — CLI args, scheduler loop
├── watcher.py          # Polls the watch folder; stability check
├── extractor.py        # File → text (dispatches by extension)
├── llm_agent.py        # Builds prompt, calls Groq, parses JSON
├── file_actions.py     # Renames + moves files (only fs-mutating module)
├── state_store.py      # SQLite dedup tracking
└── logs/               # activity.log auto-created at runtime
```

---

## Activity log

Every decision is logged to `logs/activity.log` and the console:

```
2024-01-15 10:32:01 [INFO] Processing new file: invoice_dec.pdf
2024-01-15 10:32:03 [INFO] LLM decision: name='december-consulting-invoice', category='Finance', confidence=0.95
2024-01-15 10:32:03 [INFO] Moved 'invoice_dec.pdf' -> '/Users/you/Downloads/sorted/Finance/december-consulting-invoice.pdf'
```

---

## Tech stack

| Layer | Tool |
|---|---|
| Language | Python 3.11+ |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| LLM | Groq — `llama-3.3-70b-versatile` |
| Scheduling | `schedule` (polling every N seconds) |
| PDF extraction | `pdfplumber` |
| Word extraction | `python-docx` |
| State tracking | `sqlite3` (built-in, no server) |
| Config | `python-dotenv` |
