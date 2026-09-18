"""
extractor.py
Extracts readable text content from a file so it can be sent to the LLM.
Dispatches based on file extension. No OCR - PDFs are assumed to have a
real embedded text layer (not scanned images).
"""

import logging
import pdfplumber
from docx import Document

from config import MAX_CONTENT_CHARS

logger = logging.getLogger("file_segregator")


def extract_text(filepath):
    """Return extracted text content for a file, truncated to a safe length.
    Returns an empty string if extraction fails or the file type is unsupported.
    """
    suffix = filepath.suffix.lower()

    try:
        if suffix in (".txt", ".md", ".csv"):
            text = _extract_plain_text(filepath)
        elif suffix == ".pdf":
            text = _extract_pdf_text(filepath)
        elif suffix == ".docx":
            text = _extract_docx_text(filepath)
        else:
            logger.warning(f"Unsupported file type, skipping content extraction: {filepath.name}")
            return ""
    except Exception as e:
        logger.error(f"Failed to extract text from {filepath.name}: {e}")
        return ""

    return text[:MAX_CONTENT_CHARS]


def _extract_plain_text(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _extract_pdf_text(filepath):
    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_docx_text(filepath):
    doc = Document(filepath)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)
