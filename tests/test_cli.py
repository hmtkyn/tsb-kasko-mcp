"""Tests driving the Typer command line interface end to end.

The CLI builds its own client from the environment, so these tests exercise the
same code path a user gets from a terminal: argument parsing, the client call,
and the chosen renderer.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import httpx
import pytest
import respx
from openpyxl import Workbook
from typer.testing import CliRunner

from tsb_kasko import __version__
from tsb_kasko.cli import app

from payloads import (
    ARCHIVE_FILE_PAYLOAD,
    BASE_URL,
    BRAND_LIST_PAYLOAD,
    INSURANCE_DATA_PAYLOAD,
    MODEL_LIST_PAYLOAD,
    MONTH_LIST_PAYLOAD,
    YEAR_LIST_PAYLOAD,
)

runner = CliRunner()

ARCHIVE_URL = f"{BASE_URL}{ARCHIVE_FILE_PAYLOAD}"


@pytest.fixture(autouse=True)
def wide_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop Rich from truncating table cells to an 80 column default."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("TERM", "dumb")


def _mock_lookup_endpoints() -> None:
    """Register the three endpoints a free text lookup walks through."""
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json=INSURANCE_DATA_PAYLOAD)
    )


def _archive_workbook() -> bytes:
    """Build a workbook shaped like a published monthly kasko list."""
    workbook = Workbook()
    sheet = workbook.active
    for row in (
        ["Marka Kodu", "Model Kodu", "Marka", "Tip", "Kasko Bedeli"],
        [9, 1616, "AUDI", "A3 SPORTBACK 35 TFSI", "3.695.439,00"],
        [56, 220, "TOFAŞ", "ŞAHİN 1.6", "185.000,00"],
    ):
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_version_flag_prints_the_package_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_bare_invocation_shows_help() -> None:
    result = runner.invoke(app, [])
    # Click exits 2 for a missing subcommand, help text included.
    assert result.exit_code == 2
    assert "lookup" in result.stdout
    assert "archive" in result.stdout


@respx.mock
def test_years_command_reports_covered_model_years() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        return_value=httpx.Response(200, json=YEAR_LIST_PAYLOAD)
    )
    result = runner.invoke(app, ["years", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["model_year"] == 2026
    assert len(payload) == 15


@respx.mock
def test_brands_command_writes_csv() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    result = runner.invoke(app, ["brands", "2025", "--format", "csv"])
    assert result.exit_code == 0
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert [row["name"] for row in rows] == ["ADRIA", "ALFA ROMEO", "AUDI", "BMW", "CITROEN"]


@respx.mock
def test_models_command_resolves_the_brand_by_fragment() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    result = runner.invoke(app, ["models", "2025", "aud", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert {row["brand_name"] for row in payload} == {"AUDI"}
    assert len(payload) == 4


@respx.mock
def test_lookup_command_returns_the_formatted_amount() -> None:
    _mock_lookup_endpoints()
    result = runner.invoke(app, ["lookup", "2025", "audi a3 sportback", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["vehicle_code"] == "9-1616"
    assert payload[0]["amount_formatted"] == "3.695.439,00 TL"


@respx.mock
def test_lookup_command_renders_a_table_by_default() -> None:
    _mock_lookup_endpoints()
    result = runner.invoke(app, ["lookup", "2025", "audi a3 sportback"])
    assert result.exit_code == 0
    assert "9-1616" in result.stdout
    assert "3.695.439,00 TL" in result.stdout


@respx.mock
def test_lookup_command_honours_the_brand_filter() -> None:
    brand_route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    model_route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json=INSURANCE_DATA_PAYLOAD)
    )
    result = runner.invoke(app, ["lookup", "2025", "a3", "--brand", "audi", "--format", "json"])
    assert result.exit_code == 0
    assert brand_route.call_count == 1
    # Naming the brand keeps the search to a single model list instead of all five.
    assert model_route.call_count == 1


@respx.mock
def test_value_command_prices_one_model() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json=INSURANCE_DATA_PAYLOAD)
    )
    result = runner.invoke(app, ["value", "2025", "138933", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["amount"] == 3695439
    assert payload[0]["vehicle_code"] == "9-1616"


@respx.mock
def test_unknown_brand_exits_with_code_one() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    result = runner.invoke(app, ["models", "2025", "delorean"])
    assert result.exit_code == 1
    assert "TsbNotFoundError" in result.stderr


@respx.mock
def test_transport_failure_exits_with_code_one() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(return_value=httpx.Response(503))
    result = runner.invoke(app, ["years"])
    assert result.exit_code == 1
    assert "TsbRequestError" in result.stderr


@respx.mock
def test_archive_months_command_lists_the_published_months() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    result = runner.invoke(app, ["archive", "months", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    # October carries month_id 1, which is why the mapping is resolved, not computed.
    assert {"month": 10, "month_id": 1, "name": "Ekim"} in payload


@respx.mock
def test_archive_file_command_builds_an_absolute_url() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDataArchiveFile").mock(
        return_value=httpx.Response(200, json=ARCHIVE_FILE_PAYLOAD)
    )
    result = runner.invoke(app, ["archive", "file", "2024", "8", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["url"] == ARCHIVE_URL
    assert payload[0]["filename"] == "202408R4.xlsx"


@respx.mock
def test_archive_search_command_filters_rows() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDataArchiveFile").mock(
        return_value=httpx.Response(200, json=ARCHIVE_FILE_PAYLOAD)
    )
    respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, content=_archive_workbook()))
    result = runner.invoke(
        app, ["archive", "search", "2024", "8", "--query", "sahin", "--format", "json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["vehicle_code"] == "56-220"


@respx.mock
def test_archive_download_command_writes_the_spreadsheet(tmp_path: Path) -> None:
    content = _archive_workbook()
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDataArchiveFile").mock(
        return_value=httpx.Response(200, json=ARCHIVE_FILE_PAYLOAD)
    )
    respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, content=content))
    result = runner.invoke(app, ["archive", "download", "2024", "8", "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "202408R4.xlsx").read_bytes() == content


def test_cache_path_reports_the_configured_directory(tmp_path: Path) -> None:
    result = runner.invoke(app, ["cache", "path"])
    assert result.exit_code == 0
    # The autouse isolated_cache fixture points the cache at the test's tmp_path.
    assert "cache" in result.stdout


@respx.mock
def test_cache_clear_removes_persisted_entries() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        return_value=httpx.Response(200, json=YEAR_LIST_PAYLOAD)
    )
    assert runner.invoke(app, ["years", "--format", "json"]).exit_code == 0

    result = runner.invoke(app, ["cache", "clear"])
    assert result.exit_code == 0
    assert "Removed 1" in result.stdout


def test_serve_rejects_an_unknown_transport() -> None:
    result = runner.invoke(app, ["serve", "--transport", "carrier-pigeon"])
    assert result.exit_code == 2
    assert "Unknown transport" in result.stderr


@respx.mock
def test_empty_result_prints_a_notice_instead_of_an_empty_table() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json={"HasError": False, "Message": "", "Result": []})
    )
    result = runner.invoke(app, ["brands", "2025"])
    assert result.exit_code == 0
    assert "No records found" in result.stdout


def test_serve_starts_the_requested_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    from tsb_kasko import server

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))
    result = runner.invoke(app, ["serve", "--transport", "http", "--port", "9200"])
    assert result.exit_code == 0
    assert calls == [{"transport": "http", "host": "127.0.0.1", "port": 9200}]


def test_console_script_entry_point_invokes_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    from tsb_kasko import cli

    invoked: list[bool] = []
    monkeypatch.setattr(cli, "app", lambda: invoked.append(True))
    cli.main()
    assert invoked == [True]
