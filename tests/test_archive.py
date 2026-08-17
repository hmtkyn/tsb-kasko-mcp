"""Tests for the monthly archive workbook reader."""

from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

from tsb_kasko.archive import parse_workbook
from tsb_kasko.exceptions import TsbParseError


def _workbook(rows: list[list[object]]) -> bytes:
    """Build an in memory workbook from raw rows.

    Args:
        rows: Rows to write into the first sheet.

    Returns:
        The workbook encoded as bytes.
    """
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


LAYOUT = [
    ["Türkiye Sigorta Birliği", None, None, None, None],
    ["Kasko Değer Listesi", None, None, None, None],
    [None, None, None, None, None],
    ["Marka Kodu", "Model Kodu", "Marka", "Tip", "Kasko Bedeli"],
    [9, 1616, "AUDI", "A3 SPORTBACK 35 TFSI", "3.695.439,00"],
    [9, 1617, "AUDI", "A5 AVANT 2.0 TDI", 4250000],
    [56, 220, "TOFAŞ", "ŞAHİN 1.6", "185.000,00"],
    [None, None, None, None, None],
]


def test_parse_workbook_reads_every_row() -> None:
    rows = parse_workbook(_workbook(LAYOUT), year=2024, month=8)
    assert len(rows) == 3
    first = rows[0]
    assert first.brand == "AUDI"
    assert first.model == "A3 SPORTBACK 35 TFSI"
    assert first.amount == 3695439.0
    assert first.vehicle_code == "9-1616"
    assert first.year == 2024
    assert first.month == 8


def test_parse_workbook_filters_by_query() -> None:
    rows = parse_workbook(_workbook(LAYOUT), year=2024, month=8, query="sahin")
    assert len(rows) == 1
    assert rows[0].brand == "TOFAŞ"


def test_parse_workbook_honours_limit() -> None:
    rows = parse_workbook(_workbook(LAYOUT), year=2024, month=8, limit=1)
    assert len(rows) == 1


def test_parse_workbook_splits_combined_brand_and_model_column() -> None:
    layout = [
        ["Araç Marka - Model", "Kasko Bedeli"],
        ["AUDI-80 2600", "125.000,00"],
        ["RENAULT-R 12 TOROS", 98500],
    ]
    rows = parse_workbook(_workbook(layout), year=2024, month=8)
    assert len(rows) == 2
    assert rows[0].brand == "AUDI"
    assert rows[0].model == "80 2600"
    assert rows[0].amount == 125000.0
    assert rows[1].brand == "RENAULT"


def test_parse_workbook_keeps_combined_label_without_separator() -> None:
    layout = [
        ["Araç Marka - Model", "Kasko Bedeli"],
        ["TOFAS SAHIN", "185.000,00"],
    ]
    rows = parse_workbook(_workbook(layout), year=2024, month=8)
    assert rows[0].brand is None
    assert rows[0].model == "TOFAS SAHIN"


def test_parse_workbook_rejects_unrecognised_sheet() -> None:
    layout = [["alpha", "beta"], ["one", "two"]]
    with pytest.raises(TsbParseError):
        parse_workbook(_workbook(layout), year=2024, month=8)


def test_parse_workbook_rejects_corrupt_bytes() -> None:
    with pytest.raises(TsbParseError):
        parse_workbook(b"not a workbook", year=2024, month=8)
