"""MCP server exposing the TSB kasko value list.

Tool descriptions are written for model consumption rather than for humans: they
state what the tool returns, which argument order avoids a wasted round trip and
what the returned identifiers mean. The server runs over stdio for Claude
Desktop, Claude Code and Gemini CLI, and over streamable HTTP for hosted
connectors such as ChatGPT.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Literal, cast, get_args

from fastmcp import FastMCP
from pydantic import Field

from .client import TsbKaskoClient
from .config import Settings
from .parsing import format_amount

Transport = Literal["stdio", "http", "sse"]
"""Transports this server can be started with."""

TRANSPORTS: frozenset[str] = frozenset(get_args(Transport))
"""Set form of :data:`Transport`, used to validate environment input."""

INSTRUCTIONS = """
Read vehicle valuations from the Kasko Deger Listesi published by the Turkish
Insurance Association (TSB). This is the reference value every kasko policy in
Turkey is priced against, and it is also the figure used in total loss and theft
settlements.

Typical flow: call kasko_lookup with the model year and a free text description
of the vehicle. Fall back to kasko_list_brands and kasko_list_models only when
the user needs to pick from an explicit list.

Values are published per model year, cover model years 2012 and newer, and are
expressed in Turkish lira.
""".strip()

mcp: FastMCP = FastMCP(
    name="tsb-kasko",
    instructions=INSTRUCTIONS,
    version="0.1.0",
    website_url="https://github.com/hmtkyn/tsb-kasko-mcp",
)

_settings = Settings()


def _client() -> TsbKaskoClient:
    """Build a client bound to the process wide settings.

    Returns:
        A new client instance.
    """
    return TsbKaskoClient(_settings)


@mcp.tool(
    annotations={"readOnlyHint": True, "openWorldHint": True},
    tags={"kasko", "reference"},
)
async def kasko_list_model_years() -> dict[str, Any]:
    """List the vehicle model years covered by the TSB kasko value list.

    Call this when the user gives no model year, or to check whether a year is
    covered before querying it. Coverage starts at 2012.

    Returns:
        A mapping with the covered model years in descending order.
    """
    async with _client() as client:
        years = await client.list_model_years()
    return {"model_years": years, "count": len(years)}


@mcp.tool(
    annotations={"readOnlyHint": True, "openWorldHint": True},
    tags={"kasko", "reference"},
)
async def kasko_list_brands(
    model_year: Annotated[int, Field(description="Vehicle model year, for example 2025.")],
) -> dict[str, Any]:
    """List the vehicle brands available for a model year.

    Brand availability differs per model year, so the year is required. The
    returned brand_id is the identifier kasko_list_models expects; it is not the
    brand code printed on policies.

    Args:
        model_year: Vehicle model year to list brands for.

    Returns:
        A mapping with the brands available in that model year.
    """
    async with _client() as client:
        brands = await client.list_brands(model_year)
    return {
        "model_year": model_year,
        "count": len(brands),
        "brands": [brand.model_dump() for brand in brands],
    }


@mcp.tool(
    annotations={"readOnlyHint": True, "openWorldHint": True},
    tags={"kasko", "reference"},
)
async def kasko_list_models(
    model_year: Annotated[int, Field(description="Vehicle model year, for example 2025.")],
    brand: Annotated[
        str,
        Field(description="Brand name or fragment, for example 'audi' or 'vw'."),
    ],
) -> dict[str, Any]:
    """List the models of one brand in a model year.

    Model names carry trim, engine and gearbox information, which is what makes
    two rows of the same nameplate differ in value. The returned model_id is the
    identifier kasko_get_value expects.

    Args:
        model_year: Vehicle model year to list models for.
        brand: Brand name or fragment. Matching ignores case and Turkish accents.

    Returns:
        A mapping with the resolved brand and its models.
    """
    async with _client() as client:
        resolved = await client.find_brand(model_year, brand)
        models = await client.list_models(model_year, resolved.brand_id)
    return {
        "model_year": model_year,
        "brand": resolved.model_dump(),
        "count": len(models),
        "models": [model.model_dump() for model in models],
    }


@mcp.tool(
    annotations={"readOnlyHint": True, "openWorldHint": True},
    tags={"kasko", "valuation"},
)
async def kasko_lookup(
    model_year: Annotated[int, Field(description="Vehicle model year, for example 2025.")],
    query: Annotated[
        str,
        Field(
            description=(
                "Free text vehicle description. Include brand, nameplate and any trim "
                "or engine detail the user gave, for example 'audi a3 sportback s line' "
                "or 'corolla 1.6 hybrid'."
            )
        ),
    ],
    brand: Annotated[
        str | None,
        Field(description="Optional brand name to restrict the search and speed it up."),
    ] = None,
    limit: Annotated[
        int,
        Field(ge=1, le=25, description="Maximum number of priced matches to return."),
    ] = 5,
) -> dict[str, Any]:
    """Look up the kasko value of a vehicle from a free text description.

    This is the primary tool. It resolves the description to matching models and
    returns the value of each, so no identifier lookup is needed first. Every
    result carries vehicle_code, the brand and model code pair printed on
    policies, which is the value an insurer will ask for.

    When several trims match, present them to the user rather than guessing: the
    spread between trims of the same nameplate is often large.

    Args:
        model_year: Vehicle model year to price.
        query: Free text vehicle description.
        brand: Optional brand name to restrict the search.
        limit: Maximum number of priced matches to return.

    Returns:
        A mapping with the matched valuations, amounts in Turkish lira.
    """
    async with _client() as client:
        values = await client.lookup(model_year, query, brand=brand, limit=limit)
    return {
        "model_year": model_year,
        "query": query,
        "count": len(values),
        "currency": "TRY",
        "results": [
            {**value.model_dump(), "amount_formatted": format_amount(value.amount)}
            for value in values
        ],
    }


@mcp.tool(
    annotations={"readOnlyHint": True, "openWorldHint": True},
    tags={"kasko", "valuation"},
)
async def kasko_get_value(
    model_year: Annotated[int, Field(description="Vehicle model year, for example 2025.")],
    model_id: Annotated[
        int,
        Field(description="Model identifier returned by kasko_list_models or kasko_lookup."),
    ],
) -> dict[str, Any]:
    """Read the kasko value of one exact model by its identifier.

    Use this after the user picks a specific row from kasko_list_models. When the
    vehicle is only described in words, use kasko_lookup instead.

    Args:
        model_year: Vehicle model year to price.
        model_id: Model identifier to price.

    Returns:
        A mapping with the valuation and the official vehicle code.
    """
    async with _client() as client:
        value = await client.get_kasko_value(model_year, model_id)
    return {**value.model_dump(), "amount_formatted": format_amount(value.amount)}


@mcp.tool(
    annotations={"readOnlyHint": True, "openWorldHint": True},
    tags={"kasko", "archive"},
)
async def kasko_archive_file(
    year: Annotated[int, Field(description="Publication year of the list, for example 2025.")],
    month: Annotated[
        int,
        Field(ge=1, le=12, description="Calendar month of the list, 1 for January."),
    ],
) -> dict[str, Any]:
    """Resolve the monthly kasko list spreadsheet published by TSB.

    TSB republishes the full list every month and keeps the past editions online.
    Use this to cite or hand the user the exact file for a given month, or to
    compare a current value against an older one.

    Args:
        year: Publication year of the list.
        month: Calendar month of the list.

    Returns:
        A mapping with the file name and the direct download URL.
    """
    async with _client() as client:
        archive = await client.get_archive_file(year, month)
    return archive.model_dump()


@mcp.tool(
    annotations={"readOnlyHint": True, "openWorldHint": True},
    tags={"kasko", "archive"},
)
async def kasko_search_archive(
    year: Annotated[int, Field(description="Publication year of the list, for example 2025.")],
    month: Annotated[
        int,
        Field(ge=1, le=12, description="Calendar month of the list, 1 for January."),
    ],
    query: Annotated[
        str | None,
        Field(description="Optional free text filter applied to brand and model names."),
    ] = None,
    limit: Annotated[
        int,
        Field(ge=1, le=200, description="Maximum number of rows to return."),
    ] = 50,
) -> dict[str, Any]:
    """Search inside a past monthly kasko list.

    Answers historical questions the live endpoints cannot, such as what a
    vehicle was valued at earlier in the year. The spreadsheet is downloaded and
    filtered server side, so keep the query specific.

    Args:
        year: Publication year of the list.
        month: Calendar month of the list.
        query: Optional free text filter applied to brand and model names.
        limit: Maximum number of rows to return.

    Returns:
        A mapping with the matching rows of that month's list.
    """
    async with _client() as client:
        rows = await client.read_archive_rows(year, month, query=query, limit=limit)
    return {
        "year": year,
        "month": month,
        "query": query,
        "count": len(rows),
        "currency": "TRY",
        "rows": [row.model_dump() for row in rows],
    }


@mcp.tool(
    annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    tags={"kasko", "archive"},
)
async def kasko_download_archive(
    year: Annotated[int, Field(description="Publication year of the list, for example 2025.")],
    month: Annotated[
        int,
        Field(ge=1, le=12, description="Calendar month of the list, 1 for January."),
    ],
    destination: Annotated[
        str | None,
        Field(description="Directory to save into. Defaults to the current working directory."),
    ] = None,
) -> dict[str, Any]:
    """Download a monthly kasko list spreadsheet to disk.

    Use this when the user wants the whole list as a file rather than a few rows.
    Prefer kasko_search_archive when they only need specific vehicles.

    Args:
        year: Publication year of the list.
        month: Calendar month of the list.
        destination: Directory to save into.

    Returns:
        A mapping with the saved path and the size of the file.
    """
    target = Path(destination).expanduser() if destination else Path.cwd()
    async with _client() as client:
        archive = await client.download_archive_file(year, month, target)
    return archive.model_dump()


def run(
    transport: Transport = "stdio",
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Serve the MCP endpoint over the requested transport.

    Args:
        transport: Transport to serve. ``stdio`` is what Claude Desktop, Claude
            Code and Gemini CLI expect; ``http`` serves a streamable HTTP
            endpoint for hosted connectors such as ChatGPT.
        host: Bind address used by the HTTP transports.
        port: Port used by the HTTP transports.
    """
    if transport == "stdio":
        mcp.run(show_banner=False)
        return
    mcp.run(transport=transport, host=host, port=port)


def main() -> None:
    """Run the MCP server using the environment for configuration.

    ``TSB_KASKO_TRANSPORT`` selects the transport and defaults to stdio.
    ``TSB_KASKO_HOST`` and ``TSB_KASKO_PORT`` apply to the HTTP transports.
    """
    requested = os.getenv("TSB_KASKO_TRANSPORT", "stdio").lower()
    transport = cast(Transport, requested) if requested in TRANSPORTS else "stdio"
    run(
        transport,
        host=os.getenv("TSB_KASKO_HOST", "127.0.0.1"),
        port=int(os.getenv("TSB_KASKO_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
