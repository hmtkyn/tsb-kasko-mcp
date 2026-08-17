"""Runtime configuration for the TSB kasko client, CLI and MCP server.

Every value can be overridden through an environment variable so that the same
package works unchanged as a local stdio MCP server, as a hosted HTTP server and
as a terminal tool.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_URL = "https://www.tsb.org.tr"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back on a default.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset or not an integer.

    Returns:
        The parsed integer value.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float environment variable, falling back on a default.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset or not a float.

    Returns:
        The parsed float value.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _default_cache_dir() -> Path:
    """Resolve the on disk cache directory.

    Returns:
        The directory used to persist cached TSB responses.
    """
    override = os.getenv("TSB_KASKO_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    base = os.getenv("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base).expanduser() / "tsb-kasko"


@dataclass(slots=True)
class Settings:
    """Effective configuration for one client instance.

    Attributes:
        base_url: Root URL of the TSB web application.
        timeout: Per request timeout in seconds.
        max_retries: Number of retries attempted for transient failures.
        cache_ttl: Lifetime in seconds of cached reference data such as brand lists.
        cache_dir: Directory holding the on disk response cache.
        cache_enabled: Whether responses are cached at all.
        user_agent: User agent string sent with every request.
    """

    base_url: str = field(default_factory=lambda: os.getenv("TSB_KASKO_BASE_URL", DEFAULT_BASE_URL))
    timeout: float = field(default_factory=lambda: _env_float("TSB_KASKO_TIMEOUT", 30.0))
    max_retries: int = field(default_factory=lambda: _env_int("TSB_KASKO_MAX_RETRIES", 3))
    cache_ttl: int = field(default_factory=lambda: _env_int("TSB_KASKO_CACHE_TTL", 21600))
    cache_dir: Path = field(default_factory=_default_cache_dir)
    cache_enabled: bool = field(
        default_factory=lambda: (
            os.getenv("TSB_KASKO_CACHE", "1").lower() not in {"0", "false", "no"}
        )
    )
    user_agent: str = field(
        default_factory=lambda: os.getenv("TSB_KASKO_USER_AGENT", DEFAULT_USER_AGENT)
    )

    def url(self, path: str) -> str:
        """Join a path onto the configured base URL.

        Args:
            path: Absolute path beginning with a slash, or a full URL.

        Returns:
            An absolute URL.
        """
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
