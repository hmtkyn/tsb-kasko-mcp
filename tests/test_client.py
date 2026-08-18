"""Tests for the TSB kasko client against recorded live payloads."""

from __future__ import annotations

import httpx
import pytest
import respx

from tsb_kasko.client import TsbKaskoClient
from tsb_kasko.config import Settings
from tsb_kasko.exceptions import TsbNotFoundError, TsbParseError, TsbRequestError, TsbServiceError

from payloads import (
    ARCHIVE_FILE_PAYLOAD,
    BASE_URL,
    BRAND_LIST_PAYLOAD,
    INSURANCE_DATA_PAYLOAD,
    MODEL_LIST_PAYLOAD,
    MONTH_LIST_PAYLOAD,
    YEAR_LIST_PAYLOAD,
)


@respx.mock
async def test_list_model_years_sorts_descending(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        return_value=httpx.Response(200, json=YEAR_LIST_PAYLOAD)
    )
    years = await client.list_model_years()
    assert years[0] == 2026
    assert years[-1] == 2012
    assert years == sorted(years, reverse=True)


@respx.mock
async def test_list_brands_maps_identifiers(client: TsbKaskoClient) -> None:
    route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    brands = await client.list_brands(2025)
    assert route.calls.last.request.url.params["VehicleYear"] == "2025"
    assert [brand.name for brand in brands][:3] == ["ADRIA", "ALFA ROMEO", "AUDI"]
    assert next(brand.brand_id for brand in brands if brand.name == "AUDI") == 607


@respx.mock
async def test_list_models_uses_lowercase_year_parameter(client: TsbKaskoClient) -> None:
    route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    models = await client.list_models(2025, 607)
    params = route.calls.last.request.url.params
    assert params["vehicleYear"] == "2025"
    assert params["VehicleBrandId"] == "607"
    assert len(models) == 4
    assert models[0].brand_id == 607


@respx.mock
async def test_get_kasko_value_builds_vehicle_code(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json=INSURANCE_DATA_PAYLOAD)
    )
    value = await client.get_kasko_value(2025, 138933, brand_name="AUDI")
    assert value.amount == 3695439.0
    assert value.vehicle_code == "9-1616"
    assert value.brand_code == 9
    assert value.model_code == 1616
    assert value.currency == "TRY"


@respx.mock
async def test_find_brand_prefers_exact_match(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    assert (await client.find_brand(2025, "audi")).brand_id == 607
    assert (await client.find_brand(2025, "ALFA")).name == "ALFA ROMEO"


@respx.mock
async def test_find_brand_raises_when_unknown(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    with pytest.raises(TsbNotFoundError):
        await client.find_brand(2025, "delorean")


@respx.mock
async def test_search_models_requires_every_term(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    matches = await client.search_models(2025, "audi a3 sportback")
    assert len(matches) == 1
    assert matches[0].model_id == 138933
    assert matches[0].brand_name == "AUDI"


@respx.mock
async def test_lookup_prices_every_match(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json=INSURANCE_DATA_PAYLOAD)
    )
    values = await client.lookup(2025, "audi a3 sportback")
    assert len(values) == 1
    assert values[0].vehicle_code == "9-1616"
    assert values[0].model_name.startswith("A3 SPORTBACK")


@respx.mock
async def test_lookup_raises_when_nothing_matches(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    with pytest.raises(TsbNotFoundError):
        await client.lookup(2025, "audi q7 tdi")


@respx.mock
async def test_resolve_month_id_uses_published_mapping(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    assert await client.resolve_month_id(1) == 2
    assert await client.resolve_month_id(8) == 9
    assert await client.resolve_month_id(10) == 1


@respx.mock
async def test_get_archive_file_builds_absolute_url(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    route = respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDataArchiveFile").mock(
        return_value=httpx.Response(200, json=ARCHIVE_FILE_PAYLOAD)
    )
    archive = await client.get_archive_file(2024, 8)
    params = route.calls.last.request.url.params
    assert params["Year"] == "2024"
    assert params["MonthId"] == "9"
    assert archive.filename == "202408R4.xlsx"
    assert archive.url == f"{BASE_URL}/content/InsuranceExcelFiles/202408R4.xlsx"


@respx.mock
async def test_get_archive_file_raises_when_missing(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDataArchiveFile").mock(
        return_value=httpx.Response(200, json="")
    )
    with pytest.raises(TsbNotFoundError):
        await client.get_archive_file(2024, 8)


@respx.mock
async def test_service_error_envelope_is_surfaced(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        return_value=httpx.Response(
            200, json={"HasError": True, "Message": "Servis hatasi", "Result": None}
        )
    )
    with pytest.raises(TsbServiceError, match="Servis hatasi"):
        await client.list_model_years()


@respx.mock
async def test_http_error_is_wrapped(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(return_value=httpx.Response(503))
    with pytest.raises(TsbRequestError) as excinfo:
        await client.list_model_years()
    assert excinfo.value.status_code == 503


@respx.mock
async def test_non_json_response_is_wrapped(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        return_value=httpx.Response(200, text="<html>maintenance</html>")
    )
    with pytest.raises(TsbParseError):
        await client.list_model_years()


@respx.mock
async def test_reference_data_is_cached(client: TsbKaskoClient) -> None:
    route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    await client.list_brands(2025)
    await client.list_brands(2025)
    assert route.call_count == 1


@respx.mock
async def test_connection_errors_are_retried_then_wrapped(settings: Settings) -> None:
    settings.max_retries = 3
    route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        side_effect=httpx.ConnectError("network down")
    )
    async with httpx.AsyncClient(base_url=BASE_URL) as http_client:
        client = TsbKaskoClient(settings, http_client=http_client)
        with pytest.raises(TsbRequestError):
            await client.list_model_years()
    assert route.call_count == 3


@respx.mock
async def test_a_retryable_status_is_retried_before_succeeding(settings: Settings) -> None:
    settings.max_retries = 3
    route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=YEAR_LIST_PAYLOAD),
        ]
    )
    async with httpx.AsyncClient(base_url=BASE_URL) as http_client:
        years = await TsbKaskoClient(settings, http_client=http_client).list_model_years()
    assert route.call_count == 2
    assert years[0] == 2026


@respx.mock
async def test_a_client_error_is_not_retried(settings: Settings) -> None:
    settings.max_retries = 3
    route = respx.get(f"{BASE_URL}/InsuranceData/GetVehicleYearList").mock(
        return_value=httpx.Response(404)
    )
    async with httpx.AsyncClient(base_url=BASE_URL) as http_client:
        client = TsbKaskoClient(settings, http_client=http_client)
        with pytest.raises(TsbRequestError) as error:
            await client.list_model_years()
    assert route.call_count == 1
    assert error.value.status_code == 404


@respx.mock
async def test_missing_valuation_raises_not_found(client: TsbKaskoClient) -> None:
    # TSB answers with a null Result rather than an error for an unpriced model.
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json={"HasError": False, "Message": "", "Result": None})
    )
    with pytest.raises(TsbNotFoundError):
        await client.get_kasko_value(2025, 999999)


@respx.mock
async def test_resolve_month_id_raises_for_an_unpublished_month(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetMonthList").mock(
        return_value=httpx.Response(200, json=MONTH_LIST_PAYLOAD)
    )
    # The recorded payload omits July, mirroring a month TSB has not published.
    with pytest.raises(TsbNotFoundError):
        await client.resolve_month_id(7)


@respx.mock
async def test_a_failing_brand_does_not_abort_the_whole_search(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        side_effect=[httpx.Response(500)] + [httpx.Response(200, json=MODEL_LIST_PAYLOAD)] * 8
    )
    # Four brands still answer, so the search returns their matches instead of failing.
    assert await client.search_models(2025, "a3 sportback")


@respx.mock
async def test_an_unpriced_match_is_dropped_from_the_lookup(client: TsbKaskoClient) -> None:
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleBrandList").mock(
        return_value=httpx.Response(200, json=BRAND_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetVehicleModelList").mock(
        return_value=httpx.Response(200, json=MODEL_LIST_PAYLOAD)
    )
    respx.get(f"{BASE_URL}/InsuranceData/GetInsuranceDatas").mock(
        return_value=httpx.Response(200, json={"HasError": False, "Message": "", "Result": None})
    )
    assert await client.lookup(2025, "audi a3 sportback") == []


async def test_an_injected_http_client_is_left_open(settings: Settings) -> None:
    async with httpx.AsyncClient(base_url=BASE_URL) as http_client:
        async with TsbKaskoClient(settings, http_client=http_client):
            pass
        # The caller owns the injected client, so exiting the context must not close it.
        assert not http_client.is_closed


async def test_an_owned_http_client_is_closed_on_exit(settings: Settings) -> None:
    client = TsbKaskoClient(settings)
    async with client:
        pass
    assert client._http.is_closed
