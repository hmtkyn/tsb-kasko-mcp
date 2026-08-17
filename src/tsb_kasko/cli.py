"""Terminal interface for the TSB kasko value list.

Every command mirrors a method of :class:`tsb_kasko.client.TsbKaskoClient` and
supports three output formats, so the tool is equally usable interactively and
inside a shell pipeline.
"""

from __future__ import annotations

import asyncio
import csv
import json
import sys
from collections.abc import Coroutine, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, TypeVar, cast

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .client import TsbKaskoClient
from .config import Settings
from .exceptions import TsbKaskoError
from .parsing import format_amount

T = TypeVar("T")

console = Console()
error_console = Console(stderr=True)


class OutputFormat(StrEnum):
    """Supported rendering formats for command results."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"


app = typer.Typer(
    name="tsb-kasko",
    help="Query the kasko value list published by the Turkish Insurance Association.",
    no_args_is_help=True,
    add_completion=True,
)

DEFAULT_DOWNLOAD_DIR = Path.cwd()

archive_app = typer.Typer(
    name="archive",
    help="Work with past monthly kasko lists.",
    no_args_is_help=True,
)
cache_app = typer.Typer(
    name="cache",
    help="Inspect and clear the local response cache.",
    no_args_is_help=True,
)
app.add_typer(archive_app)
app.add_typer(cache_app)

FormatOption = Annotated[
    OutputFormat,
    typer.Option("--format", "-f", help="Output format.", case_sensitive=False),
]


def _run(coroutine: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine and turn package errors into a clean exit.

    Args:
        coroutine: Coroutine to execute.

    Returns:
        The value produced by the coroutine.

    Raises:
        typer.Exit: When the client reports an error.
    """
    try:
        return asyncio.run(coroutine)
    except TsbKaskoError as error:
        error_console.print(f"[bold red]{type(error).__name__}[/]: {error}")
        raise typer.Exit(code=1) from error


def _render(
    rows: Sequence[dict[str, Any]],
    columns: Sequence[tuple[str, str]],
    output_format: OutputFormat,
    *,
    title: str | None = None,
) -> None:
    """Write records to stdout in the requested format.

    Args:
        rows: Records to render.
        columns: Pairs of record key and column heading, in display order.
        output_format: Format to render in.
        title: Optional title shown above the table.
    """
    if output_format is OutputFormat.JSON:
        console.print_json(json.dumps(list(rows), ensure_ascii=False, default=str))
        return

    if output_format is OutputFormat.CSV:
        writer = csv.DictWriter(
            sys.stdout, fieldnames=[key for key, _ in columns], extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
        return

    if not rows:
        console.print("[yellow]No records found.[/]")
        return

    table = Table(title=title, header_style="bold cyan", row_styles=["", "dim"])
    for _, heading in columns:
        table.add_column(heading, overflow="fold")
    for row in rows:
        table.add_row(*["" if row.get(key) is None else str(row.get(key)) for key, _ in columns])
    console.print(table)


def _version_callback(value: bool) -> None:
    """Print the package version and exit.

    Args:
        value: Whether the flag was supplied.

    Raises:
        typer.Exit: Always, when the flag was supplied.
    """
    if value:
        console.print(f"tsb-kasko {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Query the kasko value list published by the Turkish Insurance Association.

    Args:
        version: Whether to print the version and exit.
    """


@app.command()
def years(output_format: FormatOption = OutputFormat.TABLE) -> None:
    """List the model years covered by the kasko value list.

    Args:
        output_format: Format to render the result in.
    """

    async def action() -> list[int]:
        """Fetch the covered model years.

        Returns:
            Model years in descending order.
        """
        async with TsbKaskoClient() as client:
            return await client.list_model_years()

    result = _run(action())
    _render(
        [{"model_year": year} for year in result],
        [("model_year", "Model Year")],
        output_format,
        title="Covered model years",
    )


@app.command()
def brands(
    model_year: Annotated[int, typer.Argument(help="Vehicle model year, for example 2025.")],
    output_format: FormatOption = OutputFormat.TABLE,
) -> None:
    """List the brands available for a model year.

    Args:
        model_year: Vehicle model year to list brands for.
        output_format: Format to render the result in.
    """

    async def action() -> list[dict[str, Any]]:
        """Fetch the brands of a model year.

        Returns:
            Brand records ready for rendering.
        """
        async with TsbKaskoClient() as client:
            return [brand.model_dump() for brand in await client.list_brands(model_year)]

    _render(
        _run(action()),
        [("brand_id", "Brand ID"), ("name", "Brand")],
        output_format,
        title=f"Brands in {model_year}",
    )


@app.command()
def models(
    model_year: Annotated[int, typer.Argument(help="Vehicle model year, for example 2025.")],
    brand: Annotated[str, typer.Argument(help="Brand name or fragment, for example 'audi'.")],
    output_format: FormatOption = OutputFormat.TABLE,
) -> None:
    """List the models of one brand in a model year.

    Args:
        model_year: Vehicle model year to list models for.
        brand: Brand name or fragment.
        output_format: Format to render the result in.
    """

    async def action() -> list[dict[str, Any]]:
        """Fetch the models of one brand.

        Returns:
            Model records ready for rendering.
        """
        async with TsbKaskoClient() as client:
            resolved = await client.find_brand(model_year, brand)
            found = await client.list_models(model_year, resolved.brand_id)
            return [model.model_dump() | {"brand_name": resolved.name} for model in found]

    _render(
        _run(action()),
        [("model_id", "Model ID"), ("brand_name", "Brand"), ("name", "Model")],
        output_format,
        title=f"{brand.upper()} models in {model_year}",
    )


@app.command()
def lookup(
    model_year: Annotated[int, typer.Argument(help="Vehicle model year, for example 2025.")],
    query: Annotated[str, typer.Argument(help="Free text vehicle description.")],
    brand: Annotated[
        str | None,
        typer.Option("--brand", "-b", help="Restrict the search to one brand."),
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=1, max=25, help="Maximum matches.")
    ] = 5,
    output_format: FormatOption = OutputFormat.TABLE,
) -> None:
    """Look up the kasko value of a vehicle from a free text description.

    Args:
        model_year: Vehicle model year to price.
        query: Free text vehicle description.
        brand: Optional brand name to restrict the search.
        limit: Maximum number of priced matches to return.
        output_format: Format to render the result in.
    """

    async def action() -> list[dict[str, Any]]:
        """Search for models and price every match.

        Returns:
            Valuation records ready for rendering.
        """
        async with TsbKaskoClient() as client:
            values = await client.lookup(model_year, query, brand=brand, limit=limit)
            return [
                value.model_dump() | {"amount_formatted": format_amount(value.amount)}
                for value in values
            ]

    _render(
        _run(action()),
        [
            ("vehicle_code", "Vehicle Code"),
            ("brand_name", "Brand"),
            ("model_name", "Model"),
            ("amount_formatted", "Kasko Value"),
        ],
        output_format,
        title=f"{query} in {model_year}",
    )


@app.command()
def value(
    model_year: Annotated[int, typer.Argument(help="Vehicle model year, for example 2025.")],
    model_id: Annotated[int, typer.Argument(help="Model identifier from the models command.")],
    output_format: FormatOption = OutputFormat.TABLE,
) -> None:
    """Read the kasko value of one exact model.

    Args:
        model_year: Vehicle model year to price.
        model_id: Model identifier to price.
        output_format: Format to render the result in.
    """

    async def action() -> list[dict[str, Any]]:
        """Price one model by identifier.

        Returns:
            A single valuation record ready for rendering.
        """
        async with TsbKaskoClient() as client:
            found = await client.get_kasko_value(model_year, model_id)
            return [found.model_dump() | {"amount_formatted": format_amount(found.amount)}]

    _render(
        _run(action()),
        [
            ("vehicle_code", "Vehicle Code"),
            ("model_year", "Model Year"),
            ("model_id", "Model ID"),
            ("amount_formatted", "Kasko Value"),
        ],
        output_format,
    )


@archive_app.command("months")
def archive_months(output_format: FormatOption = OutputFormat.TABLE) -> None:
    """List the months offered by the kasko archive.

    Args:
        output_format: Format to render the result in.
    """

    async def action() -> list[dict[str, Any]]:
        """Fetch the archive month list.

        Returns:
            Month records ready for rendering.
        """
        async with TsbKaskoClient() as client:
            return [month.model_dump() for month in await client.list_archive_months()]

    _render(
        _run(action()),
        [("month", "Month"), ("name", "Name"), ("month_id", "TSB Month ID")],
        output_format,
        title="Archive months",
    )


@archive_app.command("file")
def archive_file(
    year: Annotated[int, typer.Argument(help="Publication year, for example 2025.")],
    month: Annotated[int, typer.Argument(min=1, max=12, help="Calendar month, 1 for January.")],
    output_format: FormatOption = OutputFormat.TABLE,
) -> None:
    """Resolve the spreadsheet published for one month.

    Args:
        year: Publication year of the list.
        month: Calendar month of the list.
        output_format: Format to render the result in.
    """

    async def action() -> list[dict[str, Any]]:
        """Resolve the published spreadsheet.

        Returns:
            A single archive record ready for rendering.
        """
        async with TsbKaskoClient() as client:
            return [(await client.get_archive_file(year, month)).model_dump()]

    _render(
        _run(action()),
        [("year", "Year"), ("month", "Month"), ("filename", "File"), ("url", "URL")],
        output_format,
    )


@archive_app.command("download")
def archive_download(
    year: Annotated[int, typer.Argument(help="Publication year, for example 2025.")],
    month: Annotated[int, typer.Argument(min=1, max=12, help="Calendar month, 1 for January.")],
    destination: Annotated[
        Path,
        typer.Option("--output", "-o", help="Directory or file path to save into."),
    ] = DEFAULT_DOWNLOAD_DIR,
) -> None:
    """Download the spreadsheet published for one month.

    Args:
        year: Publication year of the list.
        month: Calendar month of the list.
        destination: Directory or file path to save into.
    """

    async def action() -> dict[str, Any]:
        """Download the published spreadsheet.

        Returns:
            The archive record describing the saved file.
        """
        async with TsbKaskoClient() as client:
            return (await client.download_archive_file(year, month, destination)).model_dump()

    saved = _run(action())
    size_kb = saved["size_bytes"] / 1024
    console.print(f"[green]Saved[/] {saved['saved_path']} ({size_kb:,.1f} KiB)")


@archive_app.command("search")
def archive_search(
    year: Annotated[int, typer.Argument(help="Publication year, for example 2025.")],
    month: Annotated[int, typer.Argument(min=1, max=12, help="Calendar month, 1 for January.")],
    query: Annotated[
        str | None,
        typer.Option("--query", "-q", help="Filter applied to brand and model names."),
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=1, max=1000, help="Maximum rows.")
    ] = 50,
    output_format: FormatOption = OutputFormat.TABLE,
) -> None:
    """Search inside a past monthly kasko list.

    Args:
        year: Publication year of the list.
        month: Calendar month of the list.
        query: Optional filter applied to brand and model names.
        limit: Maximum number of rows to return.
        output_format: Format to render the result in.
    """

    async def action() -> list[dict[str, Any]]:
        """Download and filter one monthly list.

        Returns:
            Archive rows ready for rendering.
        """
        async with TsbKaskoClient() as client:
            rows = await client.read_archive_rows(year, month, query=query, limit=limit)
            return [
                row.model_dump() | {"amount_formatted": format_amount(row.amount)} for row in rows
            ]

    _render(
        _run(action()),
        [
            ("vehicle_code", "Vehicle Code"),
            ("model_year", "Model Year"),
            ("brand", "Brand"),
            ("model", "Model"),
            ("amount_formatted", "Kasko Value"),
        ],
        output_format,
        title=f"Archive {month:02d}.{year}",
    )


@cache_app.command("path")
def cache_path() -> None:
    """Print the directory holding the local response cache."""
    console.print(str(Settings().cache_dir))


@cache_app.command("clear")
def cache_clear() -> None:
    """Delete every cached response."""
    from .cache import TtlCache

    settings = Settings()
    removed = TtlCache(settings.cache_dir, settings.cache_ttl).clear()
    console.print(f"[green]Removed[/] {removed} cached responses.")


@app.command()
def serve(
    transport: Annotated[
        str,
        typer.Option("--transport", "-t", help="MCP transport: stdio, http or sse."),
    ] = "stdio",
    host: Annotated[
        str, typer.Option("--host", help="Bind address for HTTP transports.")
    ] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port for HTTP transports.")] = 8000,
) -> None:
    """Run the MCP server without leaving the CLI.

    Args:
        transport: MCP transport to serve.
        host: Bind address used by the HTTP transports.
        port: Port used by the HTTP transports.
    """
    from .server import TRANSPORTS, Transport, run

    if transport not in TRANSPORTS:
        error_console.print(
            f"[bold red]Unknown transport[/]: {transport}. "
            f"Choose one of {', '.join(sorted(TRANSPORTS))}."
        )
        raise typer.Exit(code=2)
    run(cast(Transport, transport), host=host, port=port)


def main() -> None:
    """Entry point registered as the ``tsb-kasko`` console script."""
    app()


if __name__ == "__main__":
    main()
