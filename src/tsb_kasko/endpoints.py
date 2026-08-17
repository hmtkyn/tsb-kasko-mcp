"""Endpoint descriptors for the TSB kasko value service.

TSB publishes no API contract. The kasko value page is an ASP.NET Core MVC
application whose front end calls the ``InsuranceData`` controller with plain GET
requests, no authentication and no required cookies. Every path and query
parameter the client depends on is declared here, so a rename on the TSB side is
a single file edit.

Most endpoints answer with the envelope::

    {"HasError": false, "Message": "", "Result": ...}

Two of them predate that convention and answer with a bare JSON value instead,
which is recorded on the descriptor as ``enveloped=False``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Endpoint:
    """Describes one remote call.

    Attributes:
        path: Path relative to the configured base URL.
        params: Mapping of logical argument names to the query field names TSB
            expects. TSB is inconsistent about the casing of these names, so the
            mapping is declared per endpoint rather than derived.
        enveloped: Whether the response is wrapped in the ``HasError`` envelope.
    """

    path: str
    params: dict[str, str] = field(default_factory=dict)
    enveloped: bool = True


PAGE_KASKO_LIST = "/tr/kasko-deger-listesi"
"""Public page hosting the current kasko value form."""

PAGE_KASKO_ARCHIVE = "/tr/kasko-arsiv-listesi"
"""Public page hosting the monthly kasko archive form."""

VEHICLE_YEARS = Endpoint(path="/InsuranceData/GetVehicleYearList")
"""Returns the model years covered by the kasko value list, newest first."""

VEHICLE_BRANDS = Endpoint(
    path="/InsuranceData/GetVehicleBrandList",
    params={"model_year": "VehicleYear"},
)
"""Returns the brands that have at least one model in the given model year."""

VEHICLE_MODELS = Endpoint(
    path="/InsuranceData/GetVehicleModelList",
    params={"model_year": "vehicleYear", "brand_id": "VehicleBrandId"},
)
"""Returns the models of one brand in the given model year."""

INSURANCE_DATA = Endpoint(
    path="/InsuranceData/GetInsuranceDatas",
    params={"model_year": "VehicleYear", "model_id": "VehicleModelId"},
)
"""Returns the kasko value and the official vehicle code of one model."""

MONTHS = Endpoint(path="/InsuranceData/GetMonthList", enveloped=False)
"""Returns the months selectable in the archive form.

The ``Id`` field is a database identifier and does not equal the calendar month
number; ``MonthOrder`` carries the calendar month. The archive endpoint expects
the ``Id``, which is why the list has to be resolved rather than computed.
"""

ARCHIVE_FILE = Endpoint(
    path="/InsuranceData/GetInsuranceDataArchiveFile",
    params={"year": "Year", "month_id": "MonthId"},
    enveloped=False,
)
"""Returns the site relative path of the spreadsheet published for one month."""
