"""Tests for environment driven configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from tsb_kasko.config import DEFAULT_BASE_URL, Settings


def test_defaults_apply_without_any_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "TSB_KASKO_BASE_URL",
        "TSB_KASKO_TIMEOUT",
        "TSB_KASKO_MAX_RETRIES",
        "TSB_KASKO_CACHE",
        "TSB_KASKO_CACHE_TTL",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings()
    assert settings.base_url == DEFAULT_BASE_URL
    assert settings.timeout == 30.0
    assert settings.max_retries == 3
    assert settings.cache_ttl == 21600
    assert settings.cache_enabled is True


def test_environment_overrides_every_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TSB_KASKO_BASE_URL", "https://mirror.example.com")
    monkeypatch.setenv("TSB_KASKO_TIMEOUT", "7.5")
    monkeypatch.setenv("TSB_KASKO_MAX_RETRIES", "5")
    monkeypatch.setenv("TSB_KASKO_CACHE_TTL", "120")
    monkeypatch.setenv("TSB_KASKO_USER_AGENT", "tsb-kasko-tests/1.0")
    settings = Settings()
    assert settings.base_url == "https://mirror.example.com"
    assert settings.timeout == 7.5
    assert settings.max_retries == 5
    assert settings.cache_ttl == 120
    assert settings.user_agent == "tsb-kasko-tests/1.0"


@pytest.mark.parametrize("raw", ["0", "false", "FALSE", "no", "No"])
def test_cache_can_be_switched_off(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("TSB_KASKO_CACHE", raw)
    assert Settings().cache_enabled is False


@pytest.mark.parametrize("raw", ["1", "true", "yes", "anything-else"])
def test_cache_stays_on_for_every_other_value(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("TSB_KASKO_CACHE", raw)
    assert Settings().cache_enabled is True


def test_unparsable_numbers_fall_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TSB_KASKO_TIMEOUT", "soon")
    monkeypatch.setenv("TSB_KASKO_MAX_RETRIES", "many")
    settings = Settings()
    # A typo in an environment variable must not take the tool down.
    assert settings.timeout == 30.0
    assert settings.max_retries == 3


def test_cache_dir_override_is_expanded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TSB_KASKO_CACHE_DIR", str(tmp_path / "somewhere"))
    assert Settings().cache_dir == tmp_path / "somewhere"


def test_cache_dir_follows_xdg_when_no_override_is_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TSB_KASKO_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert Settings().cache_dir == tmp_path / "tsb-kasko"


def test_cache_dir_falls_back_to_the_home_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TSB_KASKO_CACHE_DIR", raising=False)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert Settings().cache_dir == tmp_path / ".cache" / "tsb-kasko"


@pytest.mark.parametrize(
    ("base", "path", "expected"),
    [
        (
            "https://www.tsb.org.tr",
            "/InsuranceData/GetMonthList",
            "https://www.tsb.org.tr/InsuranceData/GetMonthList",
        ),
        (
            "https://www.tsb.org.tr/",
            "InsuranceData/GetMonthList",
            "https://www.tsb.org.tr/InsuranceData/GetMonthList",
        ),
        (
            "https://www.tsb.org.tr/",
            "/content/file.xlsx",
            "https://www.tsb.org.tr/content/file.xlsx",
        ),
    ],
)
def test_url_joins_without_doubling_slashes(base: str, path: str, expected: str) -> None:
    assert Settings(base_url=base).url(path) == expected


@pytest.mark.parametrize("absolute", ["https://cdn.example.com/a.xlsx", "http://example.com/b"])
def test_url_passes_absolute_urls_through(absolute: str) -> None:
    # The archive endpoint sometimes answers with a full URL rather than a path.
    assert Settings().url(absolute) == absolute
