"""Client, CLI and MCP server for the TSB kasko value list.

The Turkish Insurance Association publishes the reference valuation used by
every kasko policy sold in Turkey. This package turns the undocumented endpoints
behind that page into a typed Python client, a terminal tool and an MCP server
that Claude, ChatGPT and Gemini can call.
"""

from __future__ import annotations

from .client import TsbKaskoClient
from .config import Settings
from .exceptions import (
    TsbKaskoError,
    TsbNotFoundError,
    TsbParseError,
    TsbRequestError,
    TsbServiceError,
)
from .models import ArchiveFile, ArchiveMonth, ArchiveRow, Brand, KaskoValue, VehicleModel

__version__ = "0.1.0"

__all__ = [
    "ArchiveFile",
    "ArchiveMonth",
    "ArchiveRow",
    "Brand",
    "KaskoValue",
    "Settings",
    "TsbKaskoClient",
    "TsbKaskoError",
    "TsbNotFoundError",
    "TsbParseError",
    "TsbRequestError",
    "TsbServiceError",
    "VehicleModel",
    "__version__",
]
