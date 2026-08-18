"""Tests exercising the MCP server through an in memory client."""

from __future__ import annotations

import io
from pathlib import Path

import httpx
import pytest
import respx
from fastmcp import Client
from openpyxl import Workbook

from tsb_kasko import server
from tsb_kasko.server import mcp

from payloads import (
    ARCHIVE_FILE_PAYLOAD,
    BASE_URL,
    BRAND_LIST_PAYLOAD,
    INSURANCE_DATA_PAYLOAD,
    MODEL_LIST_PAYLOAD,
    MONTH_LIST_PAYLOAD,
    YEAR_LIST_PAYLOAD,
)

EXPECTED_TOOLS = {
    "kasko_list_model_years",
    "kasko_list_brands",
    "kasko_list_models",
    "kasko_lookup",
    "kasko_get_value",
    "kasko_archive_file",
    "kasko_search_archive",
    "kasko_download_archive",
}


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


def _mock_archive_download() -> bytes:
    """Register the month list, archive lookup and spreadsheet download routes."""
    content = _archive_workbook()
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDataArchiveFile").mock(
        return_value=httpx.Response(200, json=ARCHIVE_FILE_PAYLOAD)
    )
    respx.get(f"{BASE_URL}{ARCHIVE_FILE_PAYLOAD}").mock(
        return_value=httpx.Response(200, content=content)
    )
    return content


async def test_every_tool_is_registered() -> None:
    async with Client(mcp) as client:
        names = {tool.name for tool in await client.list_tools()}
    assert names >= EXPECTED_TOOLS


async def test_every_tool_documents_itself() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
    for tool in tools:
        assert tool.description, f"{tool.name} has no description"
        assert tool.inputSchema is not None


@respx.mock
async def test_list_model_years_tool_returns_years() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        return_value=httpx.Response(200, json=YEAR_LIST_PAYLOAD)
    )
    async with Client(mcp) as client:
        result = await client.call_tool("kasko_list_model_years", {})
    assert result.data["count"] == 15
    assert result.data["model_years"][0] == 2026


@respx.mock
async def test_lookup_tool_returns_formatted_amount() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json=INSURANCE_DATA_PAYLOAD)
    )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kasko_lookup", {"model_year": 2025, "query": "audi a3 sportback"}
        )
    payload = result.data
    assert payload["count"] == 1
    assert payload["currency"] == "TRY"
    assert payload["results"][0]["vehicle_code"] == "9-1616"
    assert payload["results"][0]["amount_formatted"] == "3.695.439,00 TL"


@respx.mock
async def test_list_brands_tool_returns_brands() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    async with Client(mcp) as client:
        result = await client.call_tool("kasko_list_brands", {"model_year": 2025})
    assert result.data["count"] == 5
    assert result.data["brands"][0]["name"] == "ADRIA"


@respx.mock
async def test_list_models_tool_resolves_the_brand_by_fragment() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    async with Client(mcp) as client:
        result = await client.call_tool("kasko_list_models", {"model_year": 2025, "brand": "aud"})
    assert result.data["brand"]["name"] == "AUDI"
    assert result.data["count"] == 4


@respx.mock
async def test_get_value_tool_prices_one_model() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json=INSURANCE_DATA_PAYLOAD)
    )
    async with Client(mcp) as client:
        result = await client.call_tool("kasko_get_value", {"model_year": 2025, "model_id": 138933})
    assert result.data["vehicle_code"] == "9-1616"
    assert result.data["amount_formatted"] == "3.695.439,00 TL"


@respx.mock
async def test_archive_file_tool_resolves_the_published_spreadsheet() -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDataArchiveFile").mock(
        return_value=httpx.Response(200, json=ARCHIVE_FILE_PAYLOAD)
    )
    async with Client(mcp) as client:
        result = await client.call_tool("kasko_archive_file", {"year": 2024, "month": 8})
    assert result.data["filename"] == "202408R4.xlsx"
    assert result.data["url"] == f"{BASE_URL}{ARCHIVE_FILE_PAYLOAD}"


@respx.mock
async def test_search_archive_tool_filters_the_monthly_list() -> None:
    _mock_archive_download()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kasko_search_archive", {"year": 2024, "month": 8, "query": "sahin"}
        )
    assert result.data["count"] == 1
    assert result.data["rows"][0]["vehicle_code"] == "56-220"
    assert result.data["currency"] == "TRY"


@respx.mock
async def test_download_archive_tool_writes_the_file(tmp_path: Path) -> None:
    content = _mock_archive_download()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kasko_download_archive",
            {"year": 2024, "month": 8, "destination": str(tmp_path)},
        )
    assert result.data["size_bytes"] == len(content)
    assert (tmp_path / "202408R4.xlsx").read_bytes() == content


async def test_download_archive_is_the_only_tool_that_writes() -> None:
    # readOnlyHint tells a client which calls are safe to make without asking.
    async with Client(mcp) as client:
        tools = await client.list_tools()
    writers = {
        tool.name for tool in tools if tool.annotations is None or not tool.annotations.readOnlyHint
    }
    assert writers == {"kasko_download_archive"}


def test_run_defaults_to_stdio_without_a_banner(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))
    server.run()
    assert calls == [{"show_banner": False}]


def test_run_passes_the_bind_address_to_http_transports(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))
    server.run("http", host="0.0.0.0", port=9000)
    assert calls == [{"transport": "http", "host": "0.0.0.0", "port": 9000}]


def test_main_reads_the_transport_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setenv("TSB_KASKO_TRANSPORT", "http")
    monkeypatch.setenv("TSB_KASKO_HOST", "0.0.0.0")
    monkeypatch.setenv("TSB_KASKO_PORT", "9100")
    server.main()
    assert calls == [{"transport": "http", "host": "0.0.0.0", "port": 9100}]


def test_main_falls_back_to_stdio_for_an_unknown_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(server.mcp, "run", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setenv("TSB_KASKO_TRANSPORT", "carrier-pigeon")
    server.main()
    # An unusable transport must not stop the server from starting at all.
    assert calls == [{"show_banner": False}]
