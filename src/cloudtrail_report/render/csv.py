from __future__ import annotations

import csv
import datetime
import io
from typing import Any


def render(summary: dict[str, Any], meta: dict[str, Any]) -> str:
    """Render *summary* as a self-describing tidy long-format CSV string.

    meta keys
    ---------
    range_start   datetime.date   inclusive start of the queried range
    range_end     datetime.date   inclusive end of the queried range
    generated_at  datetime.datetime  report generation time (UTC)
    filters       dict[str, str]  applied filters only (may be empty)

    File layout
    -----------
    Row schema: section, dimension_a, dimension_b, count

    _meta rows carry report metadata (range, totals, applied filters).
    Single-dimension sections leave dimension_b empty.
    Cross-tab sections use dimension_a = row value, dimension_b = col value.

    This is valid RFC 4180 CSV throughout — no comment lines, no mixed schemas.
    """
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n")

    w.writerow(["section", "dimension_a", "dimension_b", "count"])

    # ------------------------------------------------------------------
    # Metadata section
    # ------------------------------------------------------------------
    start     = meta["range_start"]
    end       = meta["range_end"]
    generated = meta["generated_at"]
    filters: dict[str, str] = meta.get("filters") or {}

    gen_str = (
        generated.isoformat()
        if isinstance(generated, datetime.datetime)
        else str(generated)
    )

    for key, val in [
        ("generated_at",    gen_str),
        ("range_start",     str(start)),
        ("range_end",       str(end)),
        ("total_events",    summary["total_events"]),
        ("error_count",     summary["error_count"]),
        ("read_only_count", summary["read_only_count"]),
        ("write_count",     summary["write_count"]),
    ]:
        w.writerow(["_meta", key, "", val])

    for fname, fval in sorted(filters.items()):
        w.writerow(["_meta", f"filter.{fname}", "", fval])

    # ------------------------------------------------------------------
    # Single-dimension aggregations
    # ------------------------------------------------------------------
    _write_counts(w, "by_event_name",   summary["by_event_name"])
    _write_counts(w, "by_username",     summary["by_username"])
    _write_counts(w, "by_event_source", summary["by_event_source"])
    _write_counts(w, "by_region",       summary["by_region"])
    _write_counts(w, "by_error_code",   summary["by_error_code"])

    for d, cnt in sorted(summary["by_day"].items()):
        w.writerow(["by_day", str(d), "", cnt])

    # ------------------------------------------------------------------
    # Cross-tab sections
    # ------------------------------------------------------------------
    _write_xtab(w, "xtab_username_by_source", summary["xtab_username_by_source"])
    _write_xtab(w, "xtab_username_by_event",  summary["xtab_username_by_event"])

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_counts(w: Any, section: str, counts: dict[str, int]) -> None:
    for key, cnt in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        w.writerow([section, key, "", cnt])


def _write_xtab(w: Any, section: str, xtab: dict[str, dict[str, int]]) -> None:
    for row_key in sorted(xtab):
        for col_key, cnt in sorted(
            xtab[row_key].items(), key=lambda kv: kv[1], reverse=True
        ):
            w.writerow([section, row_key, col_key, cnt])
