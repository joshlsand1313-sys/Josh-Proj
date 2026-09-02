"""Unit tests for cloudtrail_report.aggregate."""
from __future__ import annotations

import datetime

import pytest

from cloudtrail_report import aggregate

_UTC = datetime.timezone.utc


def _rec(**kw) -> dict:
    """Minimal normalized record with overrideable fields."""
    base = {
        "event_time": datetime.datetime(2026, 8, 25, 10, 0, 0, tzinfo=_UTC),
        "event_name": "DescribeInstances",
        "event_source": "ec2.amazonaws.com",
        "username": "alice",
        "aws_region": "us-east-1",
        "source_ip": "1.2.3.4",
        "read_only": True,
        "error_code": None,
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# count_by
# ---------------------------------------------------------------------------

def test_count_by_basic():
    records = [_rec(username="alice"), _rec(username="bob"), _rec(username="alice")]
    assert aggregate.count_by(records, "username") == {"alice": 2, "bob": 1}


def test_count_by_skips_none():
    records = [_rec(error_code=None), _rec(error_code=None), _rec(error_code="AccessDenied")]
    result = aggregate.count_by(records, "error_code")
    assert result == {"AccessDenied": 1}


def test_count_by_empty():
    assert aggregate.count_by([], "username") == {}


def test_count_by_casts_to_str():
    records = [_rec(read_only=True), _rec(read_only=False), _rec(read_only=True)]
    result = aggregate.count_by(records, "read_only")
    assert result == {"True": 2, "False": 1}


# ---------------------------------------------------------------------------
# count_by_day
# ---------------------------------------------------------------------------

def test_count_by_day_groups_correctly():
    d1 = datetime.date(2026, 8, 24)
    d2 = datetime.date(2026, 8, 25)
    records = [
        _rec(event_time=datetime.datetime(2026, 8, 24, 9, 0, 0, tzinfo=_UTC)),
        _rec(event_time=datetime.datetime(2026, 8, 24, 23, 59, 59, tzinfo=_UTC)),
        _rec(event_time=datetime.datetime(2026, 8, 25, 0, 0, 0, tzinfo=_UTC)),
    ]
    result = aggregate.count_by_day(records)
    assert result[d1] == 2
    assert result[d2] == 1


def test_count_by_day_skips_non_datetime():
    records = [_rec(event_time="not-a-datetime")]
    assert aggregate.count_by_day(records) == {}


# ---------------------------------------------------------------------------
# count_by_error_code
# ---------------------------------------------------------------------------

def test_count_by_error_code_skips_no_error():
    records = [
        _rec(error_code=None),
        _rec(error_code="AccessDenied"),
        _rec(error_code="AccessDenied"),
        _rec(error_code="NoSuchBucket"),
    ]
    result = aggregate.count_by_error_code(records)
    assert result == {"AccessDenied": 2, "NoSuchBucket": 1}


def test_count_by_error_code_all_clean():
    assert aggregate.count_by_error_code([_rec(), _rec()]) == {}


# ---------------------------------------------------------------------------
# top_n
# ---------------------------------------------------------------------------

def test_top_n_sorted_descending():
    counts = {"b": 3, "a": 5, "c": 1}
    result = aggregate.top_n(counts, 10)
    assert result[0] == ("a", 5)
    assert result[1] == ("b", 3)
    assert result[2] == ("c", 1)


def test_top_n_truncates():
    counts = {str(i): i for i in range(20)}
    result = aggregate.top_n(counts, 5)
    assert len(result) == 5
    assert result[0][1] == 19


def test_top_n_empty():
    assert aggregate.top_n({}, 10) == []


# ---------------------------------------------------------------------------
# crosstab
# ---------------------------------------------------------------------------

def test_crosstab_basic():
    records = [
        _rec(username="alice", event_source="ec2.amazonaws.com"),
        _rec(username="alice", event_source="s3.amazonaws.com"),
        _rec(username="bob",   event_source="ec2.amazonaws.com"),
    ]
    result = aggregate.crosstab(records, "username", "event_source")
    assert result["alice"]["ec2.amazonaws.com"] == 1
    assert result["alice"]["s3.amazonaws.com"] == 1
    assert result["bob"]["ec2.amazonaws.com"] == 1


def test_crosstab_skips_none_row():
    records = [_rec(username=None, event_source="ec2.amazonaws.com")]
    assert aggregate.crosstab(records, "username", "event_source") == {}


def test_crosstab_skips_none_col():
    records = [_rec(username="alice", event_source=None)]
    assert aggregate.crosstab(records, "username", "event_source") == {}


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------

def test_summarize_counts(sample_records):
    s = aggregate.summarize(sample_records)
    assert s["total_events"] == len(sample_records)
    assert s["error_count"] == sum(1 for r in sample_records if r.get("error_code"))
    assert s["read_only_count"] == sum(1 for r in sample_records if r.get("read_only"))
    assert s["write_count"] == s["total_events"] - s["read_only_count"]


def test_summarize_keys_present(sample_records):
    s = aggregate.summarize(sample_records)
    expected_keys = {
        "total_events", "error_count", "read_only_count", "write_count",
        "by_event_name", "by_username", "by_event_source", "by_region",
        "by_error_code", "by_day",
        "top_event_names", "top_usernames", "top_source_ips",
        "xtab_username_by_source", "xtab_username_by_event",
    }
    assert expected_keys.issubset(s.keys())


def test_summarize_empty():
    s = aggregate.summarize([])
    assert s["total_events"] == 0
    assert s["error_count"] == 0
    assert s["read_only_count"] == 0
    assert s["write_count"] == 0
    assert s["by_event_name"] == {}
    assert s["top_event_names"] == []


def test_summarize_top_n_respects_top_param(sample_records):
    s = aggregate.summarize(sample_records, top=1)
    assert len(s["top_event_names"]) <= 1
    assert len(s["top_usernames"]) <= 1
