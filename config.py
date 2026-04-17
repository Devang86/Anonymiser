"""
Configuration: regex patterns, pseudonym templates, and settings.
"""

import re

# ---------------------------------------------------------------------------
# spaCy model
# ---------------------------------------------------------------------------
SPACY_MODEL = "en_core_web_sm"

# ---------------------------------------------------------------------------
# Regex patterns for Indian financial identifiers and contact details
# ---------------------------------------------------------------------------
REGEX_PATTERNS: dict[str, re.Pattern] = {
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "GSTIN": re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"),
    "CIN": re.compile(r"\b[UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b"),
    "IFSC": re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    "BANK_ACCOUNT": re.compile(r"\b[0-9]{9,18}\b"),
    "PHONE": re.compile(
        r"\b(?:\+91[\s\-]?)?[6-9][0-9]{9}\b"
        r"|\b0[1-9][0-9]{1,2}[\s\-]?[0-9]{6,8}\b"
    ),
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    ),
}

# Context words required near a BANK_ACCOUNT match to reduce false positives
BANK_ACCOUNT_CONTEXT_WORDS = [
    "account", "a/c", "bank", "credit", "debit", "savings",
    "current", "neft", "rtgs", "imps", "upi", "beneficiary",
]
BANK_ACCOUNT_CONTEXT_WINDOW = 60  # characters on each side

# ---------------------------------------------------------------------------
# Pseudonym templates  — {n} will be replaced with a counter
# ---------------------------------------------------------------------------
PSEUDONYM_TEMPLATES: dict[str, str] = {
    "PERSON": "Person {n}",
    "ORG": "Company {n}",
    "GPE": "Location {n}",
    "PAN": "PAN-{n:05d}",
    "GSTIN": "GSTIN-{n:05d}",
    "CIN": "CIN-{n:05d}",
    "IFSC": "IFSC-{n:05d}",
    "BANK_ACCOUNT": "ACCT-{n:09d}",
    "PHONE": "PHONE-{n:05d}",
    "EMAIL": "email{n}@example.com",
}

# NER entity labels from spaCy that we care about
SPACY_ENTITY_LABELS = {"PERSON", "ORG", "GPE"}
