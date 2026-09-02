from __future__ import annotations

import datetime
from collections import Counter, defaultdict
from typing import Any

Records = list[dict[str, Any]]
Counts = dict[str, int]
CrossTab = dict[str, dict[str, int]]


# ---------------------------------------------------------------------------
# Single-dimension counts
# ---------------------------------------------------------------------------

def count_by(records: Records, field: str) -> Counts:
    """Count records grouped by the value of *field*.

    None values are skipped; every other value is cast to str so the result
    is always Dict[str, int] regardless of the field's native type.
    """
    c: Counter[str] = Counter()
    for r in records:
        val = r.get(field)
        if val is None:
            continue
        c[str(val)] += 1
    return dict(c)


def count_by_day(records: Records) -> dict[datetime.date, int]:
    """Count records per calendar day (UTC date of event_time)."""
    c: Counter[datetime.date] = Counter()
    for r in records:
        t = r.get("event_time")
        if isinstance(t, datetime.datetime):
            c[t.date()] += 1
    return dict(c)


def count_by_error_code(records: Records) -> Counts:
    """Count error events by error_code; records without an error are skipped."""
    c: Counter[str] = Counter()
    for r in records:
        code = r.get("error_code")
        if code:
            c[code] += 1
    return dict(c)


# ---------------------------------------------------------------------------
# Top-N
# ---------------------------------------------------------------------------

def top_n(counts: dict[Any, int], n: int) -> list[tuple[str, int]]:
    """Return the top-*n* (key, count) pairs sorted by count descending."""
    return sorted(
        ((str(k), v) for k, v in counts.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )[:n]


# ---------------------------------------------------------------------------
# Cross-tabulation
# ---------------------------------------------------------------------------

def crosstab(records: Records, row_field: str, col_field: str) -> CrossTab:
    """Count records bucketed by *row_field* × *col_field*.

    Returns ``{row_value: {col_value: count}}``.  Records where either field
    is None are skipped.
    """
    ct: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for r in records:
        row = r.get(row_field)
        col = r.get(col_field)
        if row is None or col is None:
            continue
        ct[str(row)][str(col)] += 1
    return {k: dict(v) for k, v in ct.items()}


# ---------------------------------------------------------------------------
# Summary — single entry point for renderers
# ---------------------------------------------------------------------------

def summarize(records: Records, *, top: int = 10) -> dict[str, Any]:
    """Run all aggregations over *records* and return one structured dict.

    Renderers receive this dict directly; no further computation is required.

    Keys
    ----
    total_events          int
    error_count           int
    read_only_count       int
    write_count           int
    by_event_name         Counts
    by_username           Counts
    by_event_source       Counts
    by_region             Counts
    by_error_code         Counts  (error events only)
    by_day                dict[date, int]
    top_event_names       list[tuple[str, int]]
    top_usernames         list[tuple[str, int]]
    top_source_ips        list[tuple[str, int]]
    xtab_username_by_source  CrossTab
    xtab_username_by_event   CrossTab
    """
    by_event_name   = count_by(records, "event_name")
    by_username     = count_by(records, "username")
    by_event_source = count_by(records, "event_source")
    by_region       = count_by(records, "aws_region")
    by_error_code   = count_by_error_code(records)
    by_day          = count_by_day(records)

    error_count     = sum(1 for r in records if r.get("error_code"))
    read_only_count = sum(1 for r in records if r.get("read_only"))

    return {
        "total_events":              len(records),
        "error_count":               error_count,
        "read_only_count":           read_only_count,
        "write_count":               len(records) - read_only_count,
        "by_event_name":             by_event_name,
        "by_username":               by_username,
        "by_event_source":           by_event_source,
        "by_region":                 by_region,
        "by_error_code":             by_error_code,
        "by_day":                    by_day,
        "top_event_names":           top_n(by_event_name, top),
        "top_usernames":             top_n(by_username, top),
        "top_source_ips":            top_n(count_by(records, "source_ip"), top),
        "xtab_username_by_source":   crosstab(records, "username", "event_source"),
        "xtab_username_by_event":    crosstab(records, "username", "event_name"),
    }
