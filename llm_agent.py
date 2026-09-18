"""
llm_agent.py
Sends extracted file content to Groq and gets back a structured decision:
{"new_name": "...", "category": "...", "confidence": 0.0-1.0}

Key prompt-engineering choices:
- OPEN category system: the LLM is free to create any category that fits the
  file (e.g. "Resume", "JobDescription", "Certificate") — not limited to a
  fixed list. This handles the real variety of a Downloads folder.
- CATEGORY_HINTS guide naming style and consistency (PascalCase, 1-2 words,
  specific over broad) without restricting what the LLM can create.
- Few-shot examples teach the naming convention so the LLM says "Resume" every
  time — not "Resumes", "CV", or "my-resume-folder".
- response_format={"type": "json_object"} is passed to Groq so the API itself
  guarantees parseable JSON back, instead of us regex-parsing free text.
"""

import json
import logging
from groq import Groq

from config import GROQ_MODEL, CATEGORY_HINTS

logger = logging.getLogger("file_segregator")

client = Groq()  # reads GROQ_API_KEY from environment automatically

HINTS_STR = ", ".join(CATEGORY_HINTS)

SYSTEM_PROMPT = f"""You are a file organizing assistant. Given the content of a document, you must decide:

1. A short, descriptive 3-word file name in kebab-case (no file extension).
2. A category that best describes what kind of document this is.
3. A confidence score between 0.0 and 1.0 for how certain you are.

--- Naming rules (3-word name) ---
- Exactly 3 words, lowercase, separated by hyphens (e.g. "bank-loan-statement", "google-offer-letter").
- Make it descriptive of the actual content, not the file type.

--- Category rules ---
- Use 1-2 words in PascalCase (e.g. "Resume", "JobDescription", "Finance", "Certificate").
- Be SPECIFIC: prefer "Resume" over "Document", "Invoice" over "Finance" if it's clearly an invoice.
- Be CONSISTENT: the same kind of document should always get the same category name.
- You may use any category that fits — do not limit yourself to a fixed list.
- Common categories for reference (use these or create your own as needed):
  {HINTS_STR}

--- Confidence rules ---
- Score 0.9+ if the document type is obvious and unambiguous.
- Score 0.5-0.89 if there is some ambiguity about the category.
- Score below 0.5 if the content is unclear or mixed.

Respond with ONLY a valid JSON object in this exact format, no extra commentary:
{{"new_name": "three-word-name", "category": "CategoryName", "confidence": 0.0}}

--- Examples ---

Content: "Sneha Agarwal | Software Engineer | Skills: Python, React | Experience: XYZ Corp intern"
Response: {{"new_name": "sneha-agarwal-resume", "category": "Resume", "confidence": 0.97}}

Content: "Company: XYZ Corp. Role: Software Engineering Intern. Responsibilities: Build REST APIs. Requirements: Python, 1yr exp."
Response: {{"new_name": "xyz-sde-jd", "category": "JobDescription", "confidence": 0.95}}

Content: "Invoice #1042. Consulting services for Q3. Amount due: $4,500. Payment terms: Net 30."
Response: {{"new_name": "consulting-invoice-q3", "category": "Invoice", "confidence": 0.96}}

Content: "This is to certify that Sneha Agarwal has successfully completed the Python Bootcamp."
Response: {{"new_name": "python-bootcamp-certificate", "category": "Certificate", "confidence": 0.95}}

Content: "Course syllabus for Introduction to Machine Learning. Topics: regression, neural networks."
Response: {{"new_name": "ml-course-syllabus", "category": "Education", "confidence": 0.93}}

Content: "This lease agreement is between Landlord and Tenant for property at 12 Main St. Rent: 15,000/month."
Response: {{"new_name": "residential-lease-agreement", "category": "Legal", "confidence": 0.94}}

Content: "Sprint planning notes. Velocity: 42 pts. Tickets assigned: auth module, dashboard redesign."
Response: {{"new_name": "sprint-planning-notes", "category": "Work", "confidence": 0.91}}

"""


def classify_and_name(file_content, original_filename):
    """Send file content to Groq and return a dict: new_name, category, confidence.
    Falls back to a safe low-confidence default if the API call or parsing fails.
    """
    if not file_content.strip():
        logger.warning(f"No extractable content for {original_filename}, sending to Needs-Review.")
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

        # Soft validation — just make sure the fields are present and category is a non-empty string
        if not result.get("category") or not isinstance(result["category"], str):
            logger.warning(f"LLM returned invalid category for '{original_filename}', forcing low confidence.")
            result["category"] = "Misc"
            result["confidence"] = 0.0

        # Sanitize category name: strip spaces, enforce PascalCase-safe characters only
        result["category"] = result["category"].strip().replace(" ", "")

        return result

    except Exception as e:
        logger.error(f"LLM call failed for {original_filename}: {e}")
        return {"new_name": "llm-processing-failed", "category": "Misc", "confidence": 0.0}
