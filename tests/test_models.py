"""Tests for the guarantees the domain models make to callers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tsb_kasko.models import ArchiveFile, ArchiveMonth, ArchiveRow, Brand, KaskoValue, VehicleModel


def test_models_are_immutable() -> None:
    brand = Brand(brand_id=607, name="AUDI")
    with pytest.raises(ValidationError):
        brand.name = "BMW"  # type: ignore[misc]


def test_unknown_fields_are_dropped_rather_than_rejected() -> None:
    # TSB adds fields to its payloads without notice; that must not break callers.
    brand = Brand.model_validate({"brand_id": 607, "name": "AUDI", "LanguageId": 1})
    assert not hasattr(brand, "LanguageId")


def test_kasko_value_defaults_currency_to_lira() -> None:
    value = KaskoValue(model_year=2025, model_id=138933, amount=3695439)
    assert value.currency == "TRY"
    assert value.vehicle_code is None


def test_kasko_value_rejects_a_negative_amount() -> None:
    with pytest.raises(ValidationError):
        KaskoValue(model_year=2025, model_id=1, amount=-1)


@pytest.mark.parametrize("month", [0, 13, -1])
def test_archive_models_reject_months_outside_the_calendar(month: int) -> None:
    with pytest.raises(ValidationError):
        ArchiveMonth(month_id=2, month=month, name="Ocak")
    with pytest.raises(ValidationError):
        ArchiveFile(year=2025, month=month, filename="a.xlsx", url="https://example.com/a.xlsx")


def test_archive_file_starts_with_an_unknown_size() -> None:
    archive = ArchiveFile(
        year=2024, month=8, filename="202408R4.xlsx", url="https://example.com/202408R4.xlsx"
    )
    assert archive.size_bytes == 0
    assert archive.saved_path is None


def test_archive_row_tolerates_a_sheet_that_omits_columns() -> None:
    row = ArchiveRow(year=2024, month=8)
    assert row.amount == 0.0
    assert row.brand is None


def test_model_copy_carries_the_brand_name_onto_a_match() -> None:
    model = VehicleModel(model_id=138933, name="A3 SPORTBACK", brand_id=607)
    # This is how the client attaches the brand while scanning several lists.
    assert model.model_copy(update={"brand_name": "AUDI"}).brand_name == "AUDI"


def test_field_aliases_accept_the_canonical_names() -> None:
    value = KaskoValue.model_validate(
        {
            "model_year": 2025,
            "model_id": 138933,
            "brand_code": 9,
            "model_code": 1616,
            "vehicle_code": "9-1616",
            "amount": 3695439.0,
        }
    )
    assert value.vehicle_code == "9-1616"
    assert value.model_dump()["brand_code"] == 9
