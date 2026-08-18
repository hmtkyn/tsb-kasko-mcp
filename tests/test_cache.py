"""Tests for the on disk time to live cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tsb_kasko.cache import TtlCache


def test_roundtrip_returns_the_stored_value(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=60)
    cache.set("brands:2025", [{"brand_id": 607, "name": "AUDI"}])
    assert cache.get("brands:2025") == [{"brand_id": 607, "name": "AUDI"}]


def test_miss_returns_none(tmp_path: Path) -> None:
    assert TtlCache(tmp_path, ttl=60).get("absent") is None


def test_value_survives_a_new_cache_instance(tmp_path: Path) -> None:
    TtlCache(tmp_path, ttl=60).set("years", [2025, 2024])
    # A fresh instance has an empty memory layer, so this can only come from disk.
    assert TtlCache(tmp_path, ttl=60).get("years") == [2025, 2024]


def test_expired_entry_is_not_served(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=0)
    cache.set("years", [2025])
    assert TtlCache(tmp_path, ttl=0).get("years") is None


def test_disabled_cache_never_stores_anything(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=60, enabled=False)
    cache.set("years", [2025])
    assert cache.get("years") is None
    assert list(tmp_path.glob("*.json")) == []


def test_corrupt_entry_is_treated_as_a_miss(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=60)
    cache.set("years", [2025])
    entry = next(iter(tmp_path.glob("*.json")))
    entry.write_text("{not json", encoding="utf-8")
    assert TtlCache(tmp_path, ttl=60).get("years") is None


def test_clear_reports_how_many_entries_were_removed(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=60)
    cache.set("years", [2025])
    cache.set("brands:2025", [])
    assert cache.clear() == 2
    assert cache.get("years") is None


def test_clear_on_a_missing_directory_is_a_no_op(tmp_path: Path) -> None:
    assert TtlCache(tmp_path / "never-created", ttl=60).clear() == 0


def test_keys_are_hashed_into_filesystem_safe_names(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=60)
    cache.set("models:2025/607", {"ok": True})
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    # A raw key would carry a path separator; the digest keeps it a flat file.
    assert files[0].stem.isalnum()


def test_distinct_keys_do_not_collide(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=60)
    cache.set("brands:2025", ["a"])
    cache.set("brands:2024", ["b"])
    assert cache.get("brands:2025") == ["a"]
    assert cache.get("brands:2024") == ["b"]


def test_stored_payload_keeps_turkish_characters_readable(tmp_path: Path) -> None:
    cache = TtlCache(tmp_path, ttl=60)
    cache.set("months", [{"name": "Ağustos"}])
    raw = next(iter(tmp_path.glob("*.json"))).read_text(encoding="utf-8")
    assert "Ağustos" in raw
    assert json.loads(raw)["value"] == [{"name": "Ağustos"}]


def test_unwritable_directory_degrades_to_no_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = TtlCache(tmp_path / "cache", ttl=60)

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("read-only filesystem")

    monkeypatch.setattr(Path, "mkdir", refuse)
    # A failure to persist must not propagate: the cache is an optimisation.
    cache.set("years", [2025])
    assert cache.get("years") == [2025]


def test_clear_ignores_entries_it_cannot_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = TtlCache(tmp_path, ttl=60)
    cache.set("years", [2025])
    cache.set("brands:2025", [])

    def refuse(self: Path) -> None:
        raise OSError("file is locked")

    monkeypatch.setattr(Path, "unlink", refuse)
    # A locked file on Windows must not turn `cache clear` into a crash.
    assert cache.clear() == 0
