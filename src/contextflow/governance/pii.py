"""PII and secret detection: pattern-based, not ML-based.

Catches common structured PII (emails, phone numbers, SSNs, credit card
numbers validated via the Luhn check) and common secret formats (AWS
access keys, generic API-key-shaped tokens). This is a first pass, not
a complete solution — it will miss unstructured PII (names, addresses in
prose) and anything that doesn't match a known pattern. A model-based
second pass (NER) is a good v0.2+ contribution — see CONTRIBUTING.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_AWS_KEY_RE = re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")
_GENERIC_SECRET_RE = re.compile(
    r"\b(?:sk|pk|api|key|token|secret)[-_][A-Za-z0-9]{16,}\b", re.IGNORECASE
)


@dataclass
class PIIMatch:
    kind: str
    """One of: email, phone, ssn, credit_card, aws_key, secret."""
    value: str
    start: int
    end: int


def _luhn_valid(digits: str) -> bool:
    total = 0
    reversed_digits = digits[::-1]
    for i, ch in enumerate(reversed_digits):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_pii(text: str) -> list[PIIMatch]:
    matches: list[PIIMatch] = []

    for m in _EMAIL_RE.finditer(text):
        matches.append(PIIMatch("email", m.group(), m.start(), m.end()))
    for m in _SSN_RE.finditer(text):
        matches.append(PIIMatch("ssn", m.group(), m.start(), m.end()))
    for m in _PHONE_RE.finditer(text):
        matches.append(PIIMatch("phone", m.group(), m.start(), m.end()))
    for m in _AWS_KEY_RE.finditer(text):
        matches.append(PIIMatch("aws_key", m.group(), m.start(), m.end()))
    for m in _GENERIC_SECRET_RE.finditer(text):
        matches.append(PIIMatch("secret", m.group(), m.start(), m.end()))
    for m in _CREDIT_CARD_RE.finditer(text):
        digits = re.sub(r"[ -]", "", m.group())
        if len(digits) in (13, 14, 15, 16, 17, 18, 19) and _luhn_valid(digits):
            matches.append(PIIMatch("credit_card", m.group(), m.start(), m.end()))

    return matches


def contains_pii(text: str) -> bool:
    return len(find_pii(text)) > 0


def redact_pii(text: str, replacement: str = "[REDACTED:{kind}]") -> str:
    matches = sorted(find_pii(text), key=lambda m: m.start, reverse=True)
    for match in matches:
        text = text[: match.start] + replacement.format(kind=match.kind.upper()) + text[match.end :]
    return text
