"""Unit tests for cloudtrail_report.cache."""
from __future__ import annotations

import datetime

import pytest

from cloudtrail_report import cache

_UTC = datetime.timezone.utc


def _record(event_name: str = "DescribeInstances") -> dict:
    return {
        "event_id": "ev-001",
        "event_time": datetime.datetime(2026, 8, 25, 10, 0, 0, tzinfo=_UTC),
        "event_name": event_name,
        "event_source": "ec2.amazonaws.com",
        "principal_type": "IAMUser",
        "username": "alice",
        "account_id": "123456789012",
        "aws_region": "us-east-1",
        "source_ip": "1.2.3.4",
        "user_agent": "aws-cli/2.0",
        "request_id": "req-1",
        "read_only": True,
        "error_code": None,
        "error_message": None,
        "resources": [],
        "access_key_id": "AKIA1",
    }


# ---------------------------------------------------------------------------
# cache_key stability
# ---------------------------------------------------------------------------

def test_cache_key_deterministic():
    start = datetime.date(2026, 8, 1)
    end   = datetime.date(2026, 8, 25)
    k1 = cache.cache_key(start, end, ["us-east-1"])
    k2 = cache.cache_key(start, end, ["us-east-1"])
    assert k1 == k2


def test_cache_key_region_order_independent():
    start = datetime.date(2026, 8, 1)
    end   = datetime.date(2026, 8, 25)
    k1 = cache.cache_key(start, end, ["us-east-1", "us-west-2"])
    k2 = cache.cache_key(start, end, ["us-west-2", "us-east-1"])
    assert k1 == k2


def test_cache_key_differs_for_different_range():
    k1 = cache.cache_key(datetime.date(2026, 8, 1), datetime.date(2026, 8, 25), ["us-east-1"])
    k2 = cache.cache_key(datetime.date(2026, 8, 2), datetime.date(2026, 8, 25), ["us-east-1"])
    assert k1 != k2


def test_cache_key_is_hex():
    k = cache.cache_key(datetime.date(2026, 8, 1), datetime.date(2026, 8, 25), ["us-east-1"])
    assert len(k) == 16
    int(k, 16)  # raises ValueError if not hex


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------

def test_roundtrip_preserves_records(tmp_path):
    records = [_record("GetObject"), _record("PutObject")]
    key = "testkey1"
    cache.save(key, records, cache_dir=tmp_path)
    loaded = cache.load(key, cache_dir=tmp_path)

    assert loaded is not None
    assert len(loaded) == 2
    assert {r["event_name"] for r in loaded} == {"GetObject", "PutObject"}


def test_roundtrip_preserves_datetime(tmp_path):
    records = [_record()]
    key = "testkey2"
    cache.save(key, records, cache_dir=tmp_path)
    loaded = cache.load(key, cache_dir=tmp_path)

    assert loaded is not None
    dt = loaded[0]["event_time"]
    assert isinstance(dt, datetime.datetime)
    assert dt == records[0]["event_time"]


def test_save_creates_cache_dir(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    cache.save("k", [_record()], cache_dir=nested)
    assert (nested / "k.json").exists()


# ---------------------------------------------------------------------------
# load miss / corrupt
# ---------------------------------------------------------------------------

def test_load_returns_none_on_miss(tmp_path):
    assert cache.load("nonexistent", cache_dir=tmp_path) is None


def test_load_returns_none_on_corrupt_json(tmp_path):
    (tmp_path / "bad.json").write_text("this is not json", encoding="utf-8")
    result = cache.load("bad", cache_dir=tmp_path)
    assert result is None


def test_load_returns_none_on_missing_records_key(tmp_path):
    import json
    (tmp_path / "norecords.json").write_text(
        json.dumps({"cached_at": "2026-08-25T00:00:00+00:00"}),
        encoding="utf-8",
    )
    # "records" key missing → iterating data["records"] raises KeyError → returns None
    result = cache.load("norecords", cache_dir=tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# key_params written to file
# ---------------------------------------------------------------------------

def test_key_params_written(tmp_path):
    import json
    params = {"start": "2026-08-01", "end": "2026-08-25", "regions": ["us-east-1"]}
    cache.save("withparams", [_record()], cache_dir=tmp_path, key_params=params)
    data = json.loads((tmp_path / "withparams.json").read_text(encoding="utf-8"))
    assert data["key_params"] == params
