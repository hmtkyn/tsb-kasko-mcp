"""Shared fixtures for the test suite."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from tsb_kasko.client import TsbKaskoClient
from tsb_kasko.config import Settings

from payloads import BASE_URL


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test off the developer's real response cache.

    The MCP server builds its settings at import time, so the module level
    instance is replaced as well as the environment.
    """
    monkeypatch.setenv("TSB_KASKO_CACHE_DIR", str(tmp_path / "cache"))
    from tsb_kasko import server

    monkeypatch.setattr(server, "_settings", Settings(cache_dir=tmp_path / "cache"))


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Build settings pointing the cache at an isolated temporary directory."""
    return Settings(
        base_url=BASE_URL,
        timeout=5.0,
        max_retries=1,
        cache_ttl=60,
        cache_dir=tmp_path / "cache",
        cache_enabled=True,
        user_agent="tsb-kasko-tests",
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[TsbKaskoClient]:
    """Provide a client whose transport is intercepted by respx."""
    async with httpx.AsyncClient(base_url=BASE_URL) as http_client:
        yield TsbKaskoClient(settings, http_client=http_client)
