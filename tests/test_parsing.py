"""Tests for payload unwrapping, Turkish number handling and text folding."""

from __future__ import annotations

import pytest

from tsb_kasko.exceptions import TsbParseError, TsbServiceError
from tsb_kasko.parsing import (
    fold,
    format_amount,
    matches_all_terms,
    parse_amount,
    split_terms,
    unwrap,
)


def test_unwrap_returns_result() -> None:
    assert unwrap({"HasError": False, "Message": "", "Result": [1, 2]}) == [1, 2]


def test_unwrap_raises_on_service_error() -> None:
    with pytest.raises(TsbServiceError):
        unwrap({"HasError": True, "Message": "hata", "Result": None})


def test_unwrap_raises_without_result_field() -> None:
    with pytest.raises(TsbParseError):
        unwrap({"HasError": False, "Message": ""})


def test_unwrap_raises_on_non_object() -> None:
    with pytest.raises(TsbParseError):
        unwrap([1, 2, 3])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (3695439, 3695439.0),
        ("3.695.439,00", 3695439.0),
        ("1.234,56 TL", 1234.56),
        ("₺2.500", 2500.0),
        ("1234.56", 1234.56),
        ("", 0.0),
        (None, 0.0),
        ("not a number", 0.0),
    ],
)
def test_parse_amount(raw: object, expected: float) -> None:
    assert parse_amount(raw) == expected


def test_format_amount_uses_turkish_separators() -> None:
    assert format_amount(3695439.0) == "3.695.439,00 TL"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ŞAHİN", "sahin"),
        ("Doğan SLX", "dogan slx"),
        ("ÇİÇEK", "cicek"),
        ("Ünlü", "unlu"),
        ("IŞIK", "isik"),
    ],
)
def test_fold_normalises_turkish_letters(text: str, expected: str) -> None:
    assert fold(text) == expected


def test_split_terms_drops_empty_tokens() -> None:
    assert split_terms("  Audi   A3  ") == ["audi", "a3"]


def test_matches_all_terms_requires_every_term() -> None:
    haystack = fold("AUDI A3 SPORTBACK 35 TFSI")
    assert matches_all_terms(haystack, ["audi", "sportback"])
    assert not matches_all_terms(haystack, ["audi", "avant"])
