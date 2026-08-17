"""Asynchronous HTTP client for the TSB kasko value service.

The client owns connection reuse, retries, caching and payload normalisation. It
is the only dependency of both the CLI and the MCP server, so behaviour stays
identical across the two front ends.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx

from . import endpoints, parsing
from .cache import TtlCache
from .config import Settings
from .exceptions import TsbNotFoundError, TsbParseError, TsbRequestError
from .models import ArchiveFile, ArchiveMonth, ArchiveRow, Brand, KaskoValue, VehicleModel

_RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})

_SEARCH_CONCURRENCY = 8


class TsbKaskoClient:
    """Reads kasko values and archive spreadsheets from the TSB web service.

    The client is an async context manager. Reusing one instance across calls
    keeps both the connection pool and the reference data cache warm.

    Example:
        >>> async with TsbKaskoClient() as client:
        ...     brands = await client.list_brands(2025)
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialise the client.

        Args:
            settings: Effective configuration. Defaults to values read from the
                environment.
            http_client: Pre-configured HTTPX client, mainly useful for tests.
                When supplied the caller keeps ownership and stays responsible
                for closing it.
        """
        self.settings = settings or Settings()
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            timeout=self.settings.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": self.settings.user_agent,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": self.settings.url(endpoints.PAGE_KASKO_LIST),
            },
        )
        self._cache = TtlCache(
            self.settings.cache_dir,
            self.settings.cache_ttl,
            enabled=self.settings.cache_enabled,
        )

    async def __aenter__(self) -> Self:
        """Enter the async context manager.

        Returns:
            The client itself.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release the connection pool on context exit.

        Args:
            exc_type: Exception class raised inside the context, if any.
            exc: Exception instance raised inside the context, if any.
            traceback: Traceback associated with the exception, if any.
        """
        await self.aclose()

    async def aclose(self) -> None:
        """Release the underlying connection pool when this instance owns it."""
        if self._owns_client:
            await self._http.aclose()

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Perform one GET request with bounded retries.

        Args:
            url: Absolute URL to request.
            params: Query string parameters.

        Returns:
            The successful HTTP response.

        Raises:
            TsbRequestError: When the endpoint stays unreachable or keeps failing.
        """
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries):
            try:
                response = await self._http.get(url, params=params)
            except httpx.HTTPError as error:
                last_error = error
                await asyncio.sleep(0.4 * (attempt + 1))
                continue

            if (
                response.status_code in _RETRYABLE_STATUS
                and attempt < self.settings.max_retries - 1
            ):
                await asyncio.sleep(0.4 * (attempt + 1))
                continue

            if response.status_code >= 400:
                raise TsbRequestError(
                    f"TSB returned HTTP {response.status_code} for {url}",
                    status_code=response.status_code,
                    url=url,
                )
            return response

        raise TsbRequestError(f"TSB request to {url} failed: {last_error}", url=url)

    async def _call(
        self,
        endpoint: endpoints.Endpoint,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Call an endpoint and return its decoded payload.

        Args:
            endpoint: Endpoint descriptor to call.
            arguments: Logical argument names mapped to values. Names are
                translated through ``endpoint.params`` before being sent.

        Returns:
            The value carried in the response, with the TSB envelope removed for
            endpoints that use one.

        Raises:
            TsbParseError: When the body is not valid JSON.
        """
        params = {
            endpoint.params.get(name, name): value
            for name, value in (arguments or {}).items()
            if value is not None
        }
        response = await self._get(self.settings.url(endpoint.path), params)
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as error:
            raise TsbParseError(
                f"Expected JSON from {response.url} but received: {response.text[:200]!r}"
            ) from error
        return parsing.unwrap(payload) if endpoint.enveloped else payload

    async def _cached_call(
        self,
        key: str,
        endpoint: endpoints.Endpoint,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Call an endpoint through the time to live cache.

        Args:
            key: Cache key identifying the request.
            endpoint: Endpoint descriptor to call on a cache miss.
            arguments: Logical arguments for the call.

        Returns:
            The decoded payload, served from cache when it is still fresh.
        """
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        payload = await self._call(endpoint, arguments)
        self._cache.set(key, payload)
        return payload

    async def list_model_years(self) -> list[int]:
        """List the model years covered by the kasko value list.

        Returns:
            Model years in descending order.
        """
        payload = await self._cached_call("years", endpoints.VEHICLE_YEARS)
        years = {int(item) for item in payload if str(item).isdigit()}
        return sorted(years, reverse=True)

    async def list_brands(self, model_year: int) -> list[Brand]:
        """List the brands that have models in a model year.

        Args:
            model_year: Model year to filter on.

        Returns:
            Brands ordered by display name.
        """
        payload = await self._cached_call(
            f"brands:{model_year}",
            endpoints.VEHICLE_BRANDS,
            {"model_year": model_year},
        )
        brands = [
            Brand(brand_id=int(item["VehicleBrandId"]), name=str(item["Name"]).strip())
            for item in payload
            if isinstance(item, dict) and item.get("VehicleBrandId") is not None
        ]
        return sorted(brands, key=lambda brand: parsing.fold(brand.name))

    async def list_models(self, model_year: int, brand_id: int) -> list[VehicleModel]:
        """List the models of one brand in a model year.

        Args:
            model_year: Model year to filter on.
            brand_id: Brand identifier returned by :meth:`list_brands`.

        Returns:
            Models ordered by display name.
        """
        payload = await self._cached_call(
            f"models:{model_year}:{brand_id}",
            endpoints.VEHICLE_MODELS,
            {"model_year": model_year, "brand_id": brand_id},
        )
        models = [
            VehicleModel(
                model_id=int(item["VehicleModelId"]),
                name=str(item["Name"]).strip(),
                brand_id=brand_id,
            )
            for item in payload
            if isinstance(item, dict) and item.get("VehicleModelId") is not None
        ]
        return sorted(models, key=lambda model: parsing.fold(model.name))

    async def get_kasko_value(
        self,
        model_year: int,
        model_id: int,
        *,
        brand_id: int | None = None,
        brand_name: str | None = None,
        model_name: str | None = None,
    ) -> KaskoValue:
        """Read the kasko value of one model in one model year.

        Args:
            model_year: Model year of the vehicle.
            model_id: Model identifier returned by :meth:`list_models`.
            brand_id: Brand identifier, carried through to the result when known.
            brand_name: Brand display name, carried through to the result.
            model_name: Model display name, carried through to the result.

        Returns:
            The valuation, including the official vehicle code.

        Raises:
            TsbNotFoundError: When TSB reports no valuation for the selection.
        """
        payload = await self._call(
            endpoints.INSURANCE_DATA,
            {"model_year": model_year, "model_id": model_id},
        )
        if not isinstance(payload, dict):
            raise TsbNotFoundError(
                f"No kasko value for model {model_id} in model year {model_year}"
            )

        brand_code = payload.get("VehicleBrandCode")
        model_code = payload.get("VehicleModelCode")
        vehicle_code = (
            f"{int(brand_code)}-{int(model_code)}"
            if brand_code not in (None, 0) and model_code not in (None, 0)
            else None
        )
        return KaskoValue(
            model_year=model_year,
            brand_id=brand_id,
            brand_name=brand_name,
            model_id=model_id,
            model_name=model_name,
            brand_code=int(brand_code) if brand_code is not None else None,
            model_code=int(model_code) if model_code is not None else None,
            vehicle_code=vehicle_code,
            amount=parsing.parse_amount(payload.get("Amount")),
        )

    async def find_brand(self, model_year: int, name: str) -> Brand:
        """Resolve a brand by name for a model year.

        Matching is case insensitive and tolerant of Turkish diacritics. An exact
        match wins over a prefix match, which wins over a substring match.

        Args:
            model_year: Model year to search within.
            name: Brand name or fragment, for example ``"vw"`` or ``"volkswagen"``.

        Returns:
            The matching brand.

        Raises:
            TsbNotFoundError: When no brand matches.
        """
        needle = parsing.fold(name)
        brands = await self.list_brands(model_year)
        predicates: tuple[Callable[[Brand], bool], ...] = (
            lambda candidate: parsing.fold(candidate.name) == needle,
            lambda candidate: parsing.fold(candidate.name).startswith(needle),
            lambda candidate: needle in parsing.fold(candidate.name),
        )
        for predicate in predicates:
            for brand in brands:
                if predicate(brand):
                    return brand
        raise TsbNotFoundError(f"No brand matching {name!r} in model year {model_year}")

    async def search_models(
        self,
        model_year: int,
        query: str,
        *,
        brand: str | None = None,
        limit: int = 25,
    ) -> list[VehicleModel]:
        """Find models whose brand and name match every term of a query.

        When no brand is given the search runs across all brands of the model
        year. Brand model lists are cached, so a repeated search costs no
        requests at all.

        Args:
            model_year: Model year to search within.
            query: Free text such as ``"corolla 1.6 hybrid"``.
            brand: Optional brand name to restrict the search to.
            limit: Maximum number of models returned.

        Returns:
            Matching models, at most ``limit`` entries.
        """
        terms = parsing.split_terms(query)
        if brand:
            candidates = [await self.find_brand(model_year, brand)]
        else:
            all_brands = await self.list_brands(model_year)
            named = [
                item
                for item in all_brands
                if any(term in parsing.fold(item.name) for term in terms)
            ]
            candidates = named or all_brands

        semaphore = asyncio.Semaphore(_SEARCH_CONCURRENCY)

        async def models_of(candidate: Brand) -> tuple[Brand, list[VehicleModel]]:
            """Fetch the models of one brand under the concurrency limit.

            Args:
                candidate: Brand to fetch models for.

            Returns:
                The brand and its models, or an empty list when the call fails.
            """
            async with semaphore:
                try:
                    return candidate, await self.list_models(model_year, candidate.brand_id)
                except (TsbRequestError, TsbParseError):
                    return candidate, []

        results: list[VehicleModel] = []
        for found_brand, models in await asyncio.gather(*(models_of(item) for item in candidates)):
            for model in models:
                haystack = parsing.fold(f"{found_brand.name} {model.name}")
                if parsing.matches_all_terms(haystack, terms):
                    results.append(model.model_copy(update={"brand_name": found_brand.name}))
        return results[:limit]

    async def lookup(
        self,
        model_year: int,
        query: str,
        *,
        brand: str | None = None,
        limit: int = 5,
    ) -> list[KaskoValue]:
        """Search for models and read the kasko value of each match.

        This is the single call most callers want: it turns a free text vehicle
        description into priced results without the caller resolving identifiers
        first.

        Args:
            model_year: Model year of the vehicle.
            query: Free text such as ``"audi a3 sportback s line"``.
            brand: Optional brand name to restrict the search to.
            limit: Maximum number of valuations returned.

        Returns:
            Valuations ordered the same way as the underlying model search.

        Raises:
            TsbNotFoundError: When the query matches no model.
        """
        models = await self.search_models(model_year, query, brand=brand, limit=limit)
        if not models:
            raise TsbNotFoundError(f"No model matching {query!r} in model year {model_year}")

        semaphore = asyncio.Semaphore(_SEARCH_CONCURRENCY)

        async def value_of(model: VehicleModel) -> KaskoValue | None:
            """Read the valuation of one model under the concurrency limit.

            Args:
                model: Model to price.

            Returns:
                The valuation, or ``None`` when TSB has no value for the model.
            """
            async with semaphore:
                try:
                    return await self.get_kasko_value(
                        model_year,
                        model.model_id,
                        brand_id=model.brand_id,
                        brand_name=model.brand_name,
                        model_name=model.name,
                    )
                except (TsbNotFoundError, TsbRequestError, TsbParseError):
                    return None

        priced = await asyncio.gather(*(value_of(model) for model in models))
        return [value for value in priced if value is not None]

    async def list_archive_months(self) -> list[ArchiveMonth]:
        """List the months selectable in the kasko archive form.

        Returns:
            Months ordered from January to December.
        """
        payload = await self._cached_call("months", endpoints.MONTHS)
        months = [
            ArchiveMonth(
                month_id=int(item["Id"]),
                month=int(item["MonthOrder"]),
                name=str(item["Name"]).strip(),
            )
            for item in payload
            if isinstance(item, dict) and item.get("Id") is not None
        ]
        return sorted(months, key=lambda item: item.month)

    async def resolve_month_id(self, month: int) -> int:
        """Translate a calendar month number into the identifier TSB expects.

        The archive endpoint keys months by a database identifier that does not
        follow calendar order, so the mapping is resolved from the live month
        list rather than hard coded.

        Args:
            month: Calendar month number between 1 and 12.

        Returns:
            The identifier accepted by the archive endpoint.

        Raises:
            TsbNotFoundError: When the month is outside the published list.
        """
        for entry in await self.list_archive_months():
            if entry.month == month:
                return entry.month_id
        raise TsbNotFoundError(f"Month {month} is not offered by the TSB archive")

    async def get_archive_file(self, year: int, month: int) -> ArchiveFile:
        """Resolve the spreadsheet published for one month.

        Args:
            year: Publication year.
            month: Calendar month number between 1 and 12.

        Returns:
            Metadata describing the published spreadsheet, without downloading it.

        Raises:
            TsbNotFoundError: When no spreadsheet exists for the given month.
        """
        month_id = await self.resolve_month_id(month)
        payload = await self._call(
            endpoints.ARCHIVE_FILE,
            {"year": year, "month_id": month_id},
        )
        path = str(payload or "").strip()
        if not path:
            raise TsbNotFoundError(f"TSB publishes no kasko archive for {month:02d}.{year}")
        url = self.settings.url(path)
        return ArchiveFile(
            year=year,
            month=month,
            filename=url.rsplit("/", 1)[-1],
            url=url,
        )

    async def download_archive_file(self, year: int, month: int, destination: Path) -> ArchiveFile:
        """Download the spreadsheet published for one month.

        Args:
            year: Publication year.
            month: Calendar month number between 1 and 12.
            destination: Directory or file path the spreadsheet is written to.

        Returns:
            Metadata describing the downloaded spreadsheet.
        """
        archive = await self.get_archive_file(year, month)
        response = await self._get(archive.url)
        target = destination / archive.filename if destination.is_dir() else destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        return archive.model_copy(
            update={"size_bytes": len(response.content), "saved_path": str(target)}
        )

    async def read_archive_rows(
        self,
        year: int,
        month: int,
        *,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ArchiveRow]:
        """Download a monthly spreadsheet and read its valuation rows.

        Args:
            year: Publication year.
            month: Calendar month number between 1 and 12.
            query: Optional free text filter applied to brand and model columns.
            limit: Maximum number of rows returned.

        Returns:
            Valuation rows read from the spreadsheet.
        """
        from .archive import parse_workbook

        archive = await self.get_archive_file(year, month)
        response = await self._get(archive.url)
        return parse_workbook(
            response.content,
            year=year,
            month=month,
            query=query,
            limit=limit,
        )
