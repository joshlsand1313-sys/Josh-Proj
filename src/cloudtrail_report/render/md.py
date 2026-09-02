from __future__ import annotations

import datetime
from collections import Counter
from typing import Any


def render(summary: dict[str, Any], meta: dict[str, Any]) -> str:
    """Render *summary* as a self-describing Markdown report string.

    meta keys
    ---------
    range_start   datetime.date   inclusive start of the queried range
    range_end     datetime.date   inclusive end of the queried range
    generated_at  datetime.datetime  report generation time (UTC)
    filters       dict[str, str]  applied filters only (may be empty)
    """
    sections = [
        _header(summary, meta),
        _top_section("Top Event Names",  summary["top_event_names"],  "Event Name"),
        _top_section("Top Principals",   summary["top_usernames"],    "Username"),
        _top_section("Top Source IPs",   summary["top_source_ips"],   "Source IP"),
        _counts_section("By Event Source", summary["by_event_source"], "Service"),
        _counts_section("By Region",       summary["by_region"],       "Region"),
        _errors_section(summary),
        _by_day_section(summary["by_day"]),
        _xtab_section(
            "Username × Event Source",
            summary["xtab_username_by_source"],
            "Username", "Service",
        ),
        _xtab_section(
            "Username × Event Name",
            summary["xtab_username_by_event"],
            "Username", "Event Name",
        ),
    ]
    return "\n\n".join(s for s in sections if s)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _header(summary: dict[str, Any], meta: dict[str, Any]) -> str:
    start       = meta["range_start"]
    end         = meta["range_end"]
    generated   = meta["generated_at"]
    filters: dict[str, str] = meta.get("filters") or {}

    gen_str = (
        generated.strftime("%Y-%m-%d %H:%M UTC")
        if isinstance(generated, datetime.datetime)
        else str(generated)
    )

    meta_rows = [
        ["Generated",    gen_str],
        ["Range",        f"{start} → {end}"],
        ["Total events", f"{summary['total_events']:,}"],
        ["Errors",       f"{summary['error_count']:,}"],
        ["Write events", f"{summary['write_count']:,}"],
        ["Read-only",    f"{summary['read_only_count']:,}"],
    ]
    if filters:
        filter_str = ", ".join(f"`{k}={v}`" for k, v in sorted(filters.items()))
        meta_rows.append(["Filters applied", filter_str])
    else:
        meta_rows.append(["Filters applied", "_none — showing all events in range_"])

    return "# CloudTrail Audit Report\n\n" + _md_table(["", ""], meta_rows) + "\n\n---"


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _top_section(title: str, pairs: list[tuple[str, int]], col_name: str) -> str:
    if not pairs:
        return f"## {title}\n\n_No data._"
    rows = [[_cell(name), f"{count:,}"] for name, count in pairs]
    return f"## {title}\n\n{_md_table([col_name, 'Count'], rows)}"


def _counts_section(title: str, counts: dict[str, int], col_name: str) -> str:
    if not counts:
        return f"## {title}\n\n_No data._"
    sorted_rows = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    rows = [[_cell(k), f"{v:,}"] for k, v in sorted_rows]
    return f"## {title}\n\n{_md_table([col_name, 'Count'], rows)}"


def _errors_section(summary: dict[str, Any]) -> str:
    by_error = summary["by_error_code"]
    if not by_error:
        return "## Errors by Error Code\n\n_No errors in this period._"
    sorted_rows = sorted(by_error.items(), key=lambda kv: kv[1], reverse=True)
    rows = [[_cell(code), f"{cnt:,}"] for code, cnt in sorted_rows]
    return f"## Errors by Error Code\n\n{_md_table(['Error Code', 'Count'], rows)}"


def _by_day_section(by_day: dict[datetime.date, int]) -> str:
    if not by_day:
        return ""
    rows = [[str(d), f"{cnt:,}"] for d, cnt in sorted(by_day.items())]
    return f"## Activity by Day\n\n{_md_table(['Date (UTC)', 'Events'], rows)}"


def _xtab_section(
    title: str,
    xtab: dict[str, dict[str, int]],
    row_label: str,
    col_label: str,
    *,
    max_cols: int = 10,
    max_rows: int = 20,
) -> str:
    if not xtab:
        return ""

    # Top columns by aggregate count across all rows
    col_totals: Counter[str] = Counter()
    for row_vals in xtab.values():
        for col, cnt in row_vals.items():
            col_totals[col] += cnt
    top_cols = [c for c, _ in col_totals.most_common(max_cols)]

    # Top rows by row total
    row_totals = {row: sum(vals.values()) for row, vals in xtab.items()}
    top_rows = sorted(row_totals, key=row_totals.__getitem__, reverse=True)[:max_rows]

    headers = [row_label] + [_cell(c) for c in top_cols] + ["Total"]
    table_rows = []
    for row_key in top_rows:
        vals = xtab[row_key]
        cells = [str(vals.get(c, "")) if vals.get(c) else "" for c in top_cols]
        table_rows.append([_cell(row_key)] + cells + [str(row_totals[row_key])])

    truncation_note = ""
    if len(xtab) > max_rows or len(col_totals) > max_cols:
        truncation_note = (
            f"\n\n_Showing top {max_rows} rows × top {max_cols} columns by count._"
        )

    return f"## {title}\n\n{_md_table(headers, table_rows)}{truncation_note}"


# ---------------------------------------------------------------------------
# Table primitives
# ---------------------------------------------------------------------------

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    sep_row    = "| " + " | ".join("---" for _ in headers) + " |"
    data_rows  = ["| " + " | ".join(c for c in row) + " |" for row in rows]
    return "\n".join([header_row, sep_row] + data_rows)


def _cell(v: Any) -> str:
    """Escape pipe characters so they don't break the markdown table."""
    return str(v).replace("|", "\\|")
