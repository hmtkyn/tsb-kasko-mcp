"""Domain models returned by the TSB kasko client.

These models describe the shape this package guarantees to its callers. They are
deliberately decoupled from the raw TSB payloads, which are undocumented and may
change without notice; translation happens in :mod:`tsb_kasko.client`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TsbModel(BaseModel):
    """Base model applying shared serialisation settings."""

    model_config = ConfigDict(populate_by_name=True, frozen=True, extra="ignore")


class Brand(TsbModel):
    """A vehicle brand offered by the kasko value list.

    Attributes:
        brand_id: Internal TSB identifier used to list the models of the brand.
            It is not the brand code printed on insurance policies.
        name: Display name of the brand, for example ``AUDI``.
    """

    brand_id: int
    name: str


class VehicleModel(TsbModel):
    """A vehicle model belonging to a brand.

    Attributes:
        model_id: Internal TSB identifier used to read the kasko value.
        name: Display name of the model including trim and gearbox information.
        brand_id: Identifier of the owning brand, when known.
        brand_name: Display name of the owning brand, when known.
    """

    model_id: int
    name: str
    brand_id: int | None = None
    brand_name: str | None = None


class KaskoValue(TsbModel):
    """The kasko valuation of one vehicle in one model year.

    Attributes:
        model_year: Model year the valuation applies to.
        brand_id: Internal TSB brand identifier, when known.
        brand_name: Display name of the brand, when known.
        model_id: Internal TSB model identifier.
        model_name: Display name of the model, when known.
        brand_code: Brand segment of the official vehicle code.
        model_code: Model segment of the official vehicle code.
        vehicle_code: Official vehicle code as printed on policies, built as
            ``brand_code-model_code``.
        amount: Kasko value in Turkish lira.
        currency: ISO 4217 currency code, always ``TRY`` for this data set.
    """

    model_year: int
    brand_id: int | None = None
    brand_name: str | None = None
    model_id: int
    model_name: str | None = None
    brand_code: int | None = None
    model_code: int | None = None
    vehicle_code: str | None = None
    amount: float = Field(ge=0)
    currency: str = "TRY"


class ArchiveMonth(TsbModel):
    """A month selectable in the kasko archive form.

    Attributes:
        month_id: Identifier the archive endpoint expects. It does not equal the
            calendar month number.
        month: Calendar month number between 1 and 12.
        name: Turkish month name.
    """

    month_id: int
    month: int = Field(ge=1, le=12)
    name: str


class ArchiveFile(TsbModel):
    """A monthly kasko list published as a spreadsheet.

    Attributes:
        year: Publication year of the list.
        month: Calendar month number of the list.
        filename: File name as published by TSB.
        url: Absolute URL the spreadsheet can be downloaded from.
        size_bytes: Size of the payload in bytes, when the file was downloaded.
        saved_path: Local path the spreadsheet was written to, when it was saved.
    """

    year: int
    month: int = Field(ge=1, le=12)
    filename: str
    url: str
    size_bytes: int = Field(default=0, ge=0)
    saved_path: str | None = None


class ArchiveRow(TsbModel):
    """One valuation row read out of a monthly archive spreadsheet.

    Attributes:
        year: Publication year of the list the row was read from.
        month: Calendar month number of the list the row was read from.
        model_year: Model year the valuation applies to, when the sheet reports it.
        brand: Brand display name.
        model: Model display name.
        brand_code: Brand segment of the official vehicle code, when present.
        model_code: Model segment of the official vehicle code, when present.
        vehicle_code: Official vehicle code, when it can be derived.
        amount: Kasko value in Turkish lira.
    """

    year: int
    month: int = Field(ge=1, le=12)
    model_year: int | None = None
    brand: str | None = None
    model: str | None = None
    brand_code: int | None = None
    model_code: int | None = None
    vehicle_code: str | None = None
    amount: float = Field(default=0.0, ge=0)
