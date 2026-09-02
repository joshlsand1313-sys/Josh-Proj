"""Renderer tests — golden-file comparison for md + csv, plus unit assertions."""
from __future__ import annotations

import pathlib

import pytest

from cloudtrail_report.render import csv as csv_renderer
from cloudtrail_report.render import md as md_renderer

from conftest import GOLDEN_DIR


# ---------------------------------------------------------------------------
# Golden-file helper
# ---------------------------------------------------------------------------

def _check_golden(actual: str, golden_path: pathlib.Path) -> None:
    """Compare *actual* to the golden file at *golden_path*.

    If the golden file does not exist, create it and pass (first-run bootstrap).
    Comparison normalises line endings so \r\n / \n differences don't fail CI.
    """
    if not golden_path.exists():
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(actual, encoding="utf-8")
        return  # newly generated — consider this a pass
    expected = golden_path.read_text(encoding="utf-8")
    assert actual.splitlines() == expected.splitlines()


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def test_md_golden(sample_summary, sample_meta):
    actual = md_renderer.render(sample_summary, sample_meta)
    _check_golden(actual, GOLDEN_DIR / "report.md")


def test_md_contains_header(sample_summary, sample_meta):
    out = md_renderer.render(sample_summary, sample_meta)
    assert "# CloudTrail Audit Report" in out
    assert "2026-08-01" in out
    assert "2026-08-25" in out


def test_md_no_errors_message_when_empty(sample_meta):
    from cloudtrail_report import aggregate
    summary = aggregate.summarize([])
    out = md_renderer.render(summary, sample_meta)
    assert "_No errors in this period._" in out


def test_md_filters_shown_when_present(sample_summary):
    import datetime
    meta = {
        "range_start": datetime.date(2026, 8, 1),
        "range_end": datetime.date(2026, 8, 25),
        "generated_at": datetime.datetime(2026, 8, 25, 12, 0, 0, tzinfo=datetime.timezone.utc),
        "filters": {"username": "alice", "errors_only": "true"},
    }
    out = md_renderer.render(sample_summary, meta)
    assert "username=alice" in out
    assert "errors_only=true" in out


def test_md_pipe_in_value_escaped(sample_meta):
    r"""A value containing | must be escaped as \| in markdown tables."""
    from cloudtrail_report import aggregate
    from cloudtrail_report.normalize import normalize
    from conftest import _blob
    import datetime, json
    item = {
        "EventId": "ev-pipe",
        "EventTime": datetime.datetime(2026, 8, 25, 10, 0, 0, tzinfo=datetime.timezone.utc),
        "EventName": "name|with|pipes",
        "EventSource": "ec2.amazonaws.com",
        "CloudTrailEvent": _blob(
            eventID="ev-pipe",
            eventName="name|with|pipes",
            eventSource="ec2.amazonaws.com",
            awsRegion="us-east-1",
            userIdentity={"type": "IAMUser", "userName": "u", "accountId": "0"},
        ),
    }
    records = [normalize(item)]
    summary = aggregate.summarize(records)
    out = md_renderer.render(summary, sample_meta)
    assert "name\\|with\\|pipes" in out


# ---------------------------------------------------------------------------
# CSV renderer
# ---------------------------------------------------------------------------

def test_csv_golden(sample_summary, sample_meta):
    actual = csv_renderer.render(sample_summary, sample_meta)
    _check_golden(actual, GOLDEN_DIR / "report.csv")


def test_csv_has_header_row(sample_summary, sample_meta):
    out = csv_renderer.render(sample_summary, sample_meta)
    first_line = out.splitlines()[0]
    assert first_line == "section,dimension_a,dimension_b,count"


def test_csv_meta_rows_present(sample_summary, sample_meta):
    out = csv_renderer.render(sample_summary, sample_meta)
    lines = out.splitlines()
    meta_lines = [l for l in lines if l.startswith("_meta,")]
    keys = {l.split(",")[1] for l in meta_lines}
    assert {"generated_at", "range_start", "range_end", "total_events"}.issubset(keys)


def test_csv_filter_rows_present(sample_summary):
    import datetime
    meta = {
        "range_start": datetime.date(2026, 8, 1),
        "range_end": datetime.date(2026, 8, 25),
        "generated_at": datetime.datetime(2026, 8, 25, 12, 0, 0, tzinfo=datetime.timezone.utc),
        "filters": {"username": "alice"},
    }
    out = csv_renderer.render(sample_summary, meta)
    assert "_meta,filter.username,,alice" in out.splitlines()


def test_csv_all_sections_present(sample_summary, sample_meta):
    out = csv_renderer.render(sample_summary, sample_meta)
    lines = out.splitlines()
    sections = {l.split(",")[0] for l in lines[1:]}  # skip header
    expected = {
        "_meta", "by_event_name", "by_username", "by_event_source",
        "by_region", "by_day",
    }
    assert expected.issubset(sections)
