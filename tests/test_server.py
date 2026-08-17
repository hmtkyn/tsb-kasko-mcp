"""Tests exercising the MCP server through an in memory client."""

from __future__ import annotations

import httpx
import respx
from fastmcp import Client

from tsb_kasko.server import mcp

from payloads import (
    BASE_URL,
    BRAND_LIST_PAYLOAD,
    INSURANCE_DATA_PAYLOAD,
    MODEL_LIST_PAYLOAD,
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
