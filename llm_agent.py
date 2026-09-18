"""
llm_agent.py
Sends extracted file content to Groq and gets back a structured decision:
{"new_name": "...", "category": "...", "confidence": 0.0-1.0}

Key prompt-engineering choices:
- A fixed category list is given to the model so classification stays consistent
  across runs (the model can't invent new categories).
- Few-shot examples show the model the exact naming style and category mapping
  we want, which noticeably improves consistency vs. a bare instruction.
- response_format={"type": "json_object"} is passed to Groq so the API itself
  guarantees parseable JSON back, instead of us regex-parsing free text.
"""

import json
import logging
from groq import Groq

from config import GROQ_MODEL, CATEGORIES

logger = logging.getLogger("file_segregator")

client = Groq()  # reads GROQ_API_KEY from environment automatically

CATEGORY_LIST_STR = ", ".join(CATEGORIES)

SYSTEM_PROMPT = f"""You are a file organizing assistant. Given the content of a document,
you must decide on:
1. A short, descriptive, three-word file name (kebab-case, no file extension).
2. The single best-fitting category, chosen ONLY from this fixed list: {CATEGORY_LIST_STR}.
3. A confidence score between 0.0 and 1.0 representing how sure you are about the category.

Rules:
- The name must be exactly three words, lowercase, separated by hyphens (e.g. "bank-loan-statement").
- The category MUST be exactly one of: {CATEGORY_LIST_STR}. Never invent a new category.
- If the content is ambiguous or ambiguous between categories, lower your confidence score accordingly.
- Respond with ONLY a valid JSON object in this exact format, with no extra commentary:
{{"new_name": "three-word-name", "category": "CategoryName", "confidence": 0.0}}

Examples:
Content: "Invoice for Q3 consulting services, amount due $4,500, payment terms net 30."
Response: {{"new_name": "consulting-invoice-q3", "category": "Finance", "confidence": 0.95}}

Content: "Happy birthday! Hope you have an amazing day surrounded by family and cake."
Response: {{"new_name": "birthday-wishes-message", "category": "Personal", "confidence": 0.9}}

Content: "Meeting notes: sprint planning, backlog grooming, and assigning tickets for next sprint."
Response: {{"new_name": "sprint-planning-notes", "category": "Work", "confidence": 0.9}}

Content: "Course syllabus for Introduction to Machine Learning, Fall semester, includes grading rubric."
Response: {{"new_name": "ml-course-syllabus", "category": "Education", "confidence": 0.92}}

Content: "This agreement is entered into between the Landlord and Tenant, governing the lease of the property."
Response: {{"new_name": "residential-lease-agreement", "category": "Legal", "confidence": 0.93}}
"""


def classify_and_name(file_content, original_filename):
    """Send file content to Groq and return a dict: new_name, category, confidence.
    Falls back to a safe low-confidence default if the API call or parsing fails.
    """
    if not file_content.strip():
        logger.warning(f"No extractable content for {original_filename}, sending to review.")
        return {"new_name": "unreadable-file-content", "category": "Misc", "confidence": 0.0}

    user_prompt = f"Original filename: {original_filename}\n\nFile content:\n{file_content}"

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_output = response.choices[0].message.content
        result = json.loads(raw_output)

        # Basic validation - guard against a malformed or out-of-list category
        if result.get("category") not in CATEGORIES:
            logger.warning(f"LLM returned invalid category '{result.get('category')}', forcing low confidence.")
            result["category"] = "Misc"
            result["confidence"] = 0.0

        return result

    except Exception as e:
        logger.error(f"LLM call failed for {original_filename}: {e}")
        return {"new_name": "llm-processing-failed", "category": "Misc", "confidence": 0.0}
