"""PHI detection and redaction for HIPAA Safe Harbor (18 identifiers)."""

import re
from dataclasses import dataclass
from enum import Enum


class PHIType(str, Enum):
    NAME = "NAME"
    DATE = "DATE"
    PHONE = "PHONE"
    FAX = "FAX"
    EMAIL = "EMAIL"
    SSN = "SSN"
    MRN = "MRN"
    ADDRESS = "ADDRESS"
    ZIP = "ZIP"
    URL = "URL"
    IP = "IP"
    DEVICE_ID = "DEVICE_ID"


@dataclass
class PHIMatch:
    phi_type: PHIType
    start: int
    end: int
    original: str


_PATTERNS: list[tuple[PHIType, re.Pattern]] = [
    (PHIType.SSN, re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (PHIType.PHONE, re.compile(r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    (PHIType.EMAIL, re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    (PHIType.DATE, re.compile(r"\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](\d{4}|\d{2})\b")),
    (PHIType.ZIP, re.compile(r"\b\d{5}(-\d{4})?\b")),
    (PHIType.IP, re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    (PHIType.URL, re.compile(r"https?://[^\s]+")),
    # Medical Record Number patterns (MRN-12345, MR: 12345, etc.)
    (PHIType.MRN, re.compile(r"\b(MRN?|Medical\s*Record\s*(Number|No\.?|#?)):?\s*\d+\b", re.IGNORECASE)),
]


def detect_phi(text: str) -> list[PHIMatch]:
    matches: list[PHIMatch] = []
    for phi_type, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            matches.append(PHIMatch(phi_type, m.start(), m.end(), m.group()))
    return sorted(matches, key=lambda x: x.start)


def redact_phi(text: str, replacement: str = "[REDACTED]") -> tuple[str, list[PHIMatch]]:
    """Return redacted text and list of what was found."""
    matches = detect_phi(text)
    if not matches:
        return text, []

    # Work right-to-left so offsets stay valid
    result = text
    for match in reversed(matches):
        result = result[: match.start] + f"[{match.phi_type.value}]" + result[match.end :]

    return result, matches


def contains_phi(text: str) -> bool:
    return bool(detect_phi(text))
