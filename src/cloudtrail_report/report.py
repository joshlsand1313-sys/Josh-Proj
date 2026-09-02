from __future__ import annotations

import csv
import datetime
import pathlib

from jinja2 import Environment, PackageLoader, select_autoescape

_CSV_FIELDS = [
    "event_time",
    "event_name",
    "principal_type",
    "username",
    "account_id",
    "event_source",
    "aws_region",
    "source_ip",
    "read_only",
    "error_code",
    "error_message",
    "request_id",
    "access_key_id",
]


def build_report(
    events: list[dict],
    output_format: str,
    output_path: str,
) -> None:
    if output_format == "html":
        _write_html(events, output_path)
    elif output_format == "csv":
        _write_csv(events, output_path)
    else:
        raise ValueError(f"Unknown format: {output_format!r}")


def _write_html(events: list[dict], output_path: str) -> None:
    env = Environment(
        loader=PackageLoader("cloudtrail_report", "templates"),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html.j2")
    html = template.render(
        events=events,
        event_count=len(events),
        generated_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    pathlib.Path(output_path).write_text(html, encoding="utf-8")


def _write_csv(events: list[dict], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for event in events:
            row = {k: event.get(k, "") for k in _CSV_FIELDS}
            writer.writerow(row)
