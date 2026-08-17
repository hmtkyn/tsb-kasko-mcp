"""Helpers for reading TSB payloads and matching Turkish text.

TSB wraps every JSON response in a ``HasError`` / ``Message`` / ``Result``
envelope. Unwrapping it in one place keeps the client free of repeated checks,
and keeps a service side error from being mistaken for an empty result.
"""

from __future__ import annotations

import re
from typing import Any

from .exceptions import TsbParseError, TsbServiceError

_TURKISH_FOLD = str.maketrans(
    {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ç": "c",
        "ç": "c",
        "Ğ": "g",
        "ğ": "g",
        "Ö": "o",
        "ö": "o",
        "Ş": "s",
        "ş": "s",
        "Ü": "u",
        "ü": "u",
        "Â": "a",
        "â": "a",
    }
)


def unwrap(payload: Any) -> Any:
    """Read the ``Result`` field out of a TSB response envelope.

    Args:
        payload: Decoded JSON returned by TSB.

    Returns:
        The value carried in ``Result``.

    Raises:
        TsbServiceError: When TSB reports an error through ``HasError``.
        TsbParseError: When the payload does not look like a TSB envelope.
    """
    if not isinstance(payload, dict):
        raise TsbParseError(f"Expected a TSB envelope object but received {type(payload).__name__}")
    if payload.get("HasError"):
        raise TsbServiceError(str(payload.get("Message") or "TSB reported an unspecified error"))
    if "Result" not in payload:
        raise TsbParseError("TSB envelope carries no Result field")
    return payload["Result"]


def unwrap_list(payload: Any) -> list[Any]:
    """Read the ``Result`` field and guarantee a list.

    Args:
        payload: Decoded JSON returned by TSB.

    Returns:
        The records carried in ``Result``, or an empty list when it is null.

    Raises:
        TsbParseError: When ``Result`` is neither a list nor null.
    """
    result = unwrap(payload)
    if result is None:
        return []
    if not isinstance(result, list):
        raise TsbParseError(f"Expected a list in Result but received {type(result).__name__}")
    return result


def parse_amount(raw: Any) -> float:
    """Convert a Turkish formatted monetary value into a float.

    TSB mixes machine readable numbers with strings formatted for Turkish
    readers, where the dot groups thousands and the comma marks decimals. A dot
    is read as a grouping separator when it is followed by exactly three digits
    and no comma is present, which is how ``2.500`` becomes two thousand five
    hundred rather than two and a half.

    Args:
        raw: Value as returned by TSB.

    Returns:
        The amount as a float, or ``0.0`` when the value cannot be interpreted.
    """
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    text = re.sub(r"[^\d.,-]", "", str(raw).strip())
    if not text:
        return 0.0
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "." in text:
        groups = text.split(".")
        if len(groups) > 2 or len(groups[-1]) == 3:
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def format_amount(value: float) -> str:
    """Render an amount using Turkish grouping and decimal separators.

    Args:
        value: Amount in Turkish lira.

    Returns:
        The amount formatted as ``1.234.567,89 TL``.
    """
    formatted = f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{formatted} TL"


def fold(text: str) -> str:
    """Fold a Turkish string for case insensitive and accent insensitive matching.

    Args:
        text: Input string.

    Returns:
        A lowercase ASCII approximation suitable for substring matching.
    """
    return text.translate(_TURKISH_FOLD).lower().strip()


def matches_all_terms(haystack: str, terms: list[str]) -> bool:
    """Report whether every search term appears in the folded haystack.

    Args:
        haystack: Text to search within, already folded.
        terms: Folded search terms.

    Returns:
        True when every term is a substring of the haystack.
    """
    return all(term in haystack for term in terms)


def split_terms(query: str) -> list[str]:
    """Split a free text query into folded search terms.

    Args:
        query: Raw user query.

    Returns:
        The folded, non empty terms of the query.
    """
    return [term for term in fold(query).split() if term]
