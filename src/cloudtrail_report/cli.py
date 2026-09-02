from __future__ import annotations

import datetime
import os
import pathlib

import click

from cloudtrail_report import aggregate, cache as cache_mod
from cloudtrail_report.fetch import CredentialError, fetch_events
from cloudtrail_report.render import csv as csv_renderer
from cloudtrail_report.render import md as md_renderer

_UTC = datetime.timezone.utc


@click.group()
@click.option(
    "--profile", envvar="AWS_PROFILE", default=None,
    help="AWS named profile (~/.aws/credentials). Overrides AWS_PROFILE.",
)
@click.option(
    "--region", envvar="CT_REGION", default="us-east-1", show_default=True,
    help="Primary AWS region to query.",
)
@click.pass_context
def main(ctx: click.Context, profile: str | None, region: str) -> None:
    """CloudTrail management-event audit reporter."""
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["region"] = region


@main.command()
# ---- Time window --------------------------------------------------------
@click.option(
    "--days", envvar="CT_DAYS", default=None, type=click.IntRange(1, 90),
    help="Days of history to query (1–90). Mutually exclusive with --start/--end.",
)
@click.option(
    "--start", envvar="CT_START", type=click.DateTime(formats=["%Y-%m-%d"]), default=None,
    metavar="YYYY-MM-DD",
    help="Start of date range (UTC, inclusive). Requires --end.",
)
@click.option(
    "--end", envvar="CT_END", type=click.DateTime(formats=["%Y-%m-%d"]), default=None,
    metavar="YYYY-MM-DD",
    help="End of date range (UTC, inclusive). Requires --start.",
)
# ---- Query scope --------------------------------------------------------
@click.option(
    "--extra-region", "extra_regions", multiple=True, metavar="REGION",
    help="Additional region to query (repeatable).",
)
# ---- Post-fetch filters -------------------------------------------------
@click.option(
    "--event-source", default=None, metavar="SERVICE", envvar="CT_EVENT_SOURCE",
    help="Keep only events from this AWS service (e.g. ec2.amazonaws.com).",
)
@click.option(
    "--username", default=None, metavar="NAME", envvar="CT_USERNAME",
    help="Keep only events from this principal/username.",
)
@click.option(
    "--filter-region", default=None, metavar="REGION", envvar="CT_FILTER_REGION",
    help="Keep only events recorded in this AWS region (post-fetch).",
)
@click.option(
    "--read-only", "read_only", is_flag=True, default=False, envvar="CT_READ_ONLY",
    help="Keep only read-only (non-mutating) events.",
)
@click.option(
    "--errors-only", is_flag=True, default=False, envvar="CT_ERRORS_ONLY",
    help="Keep only events that returned an error.",
)
# ---- Cache --------------------------------------------------------------
@click.option(
    "--no-cache", "no_cache", is_flag=True, default=False, envvar="CT_NO_CACHE",
    help="Skip reading and writing the disk cache.",
)
@click.option(
    "--refresh", is_flag=True, default=False, envvar="CT_REFRESH",
    help="Force re-fetch from AWS and overwrite the existing cache entry.",
)
# ---- Output -------------------------------------------------------------
@click.option(
    "--format", "output_format",
    type=click.Choice(["md", "csv", "both"]), default="md", show_default=True,
    envvar="CT_FORMAT",
    help="Output format.",
)
@click.option(
    "--output", "output_dir",
    type=click.Path(file_okay=False), default=".", show_default=True,
    envvar="CT_OUTPUT",
    help="Directory to write report file(s) into.",
)
@click.pass_context
def run(
    ctx: click.Context,
    days: int | None,
    start: datetime.datetime | None,
    end: datetime.datetime | None,
    extra_regions: tuple[str, ...],
    event_source: str | None,
    username: str | None,
    filter_region: str | None,
    read_only: bool,
    errors_only: bool,
    no_cache: bool,
    refresh: bool,
    output_format: str,
    output_dir: str,
) -> None:
    """Fetch CloudTrail events and write an audit report."""
    # CT_EXTRA_REGIONS=us-west-2,eu-west-1 merges with any --extra-region flags.
    # click doesn't natively support comma-separated multiples from env vars.
    env_regions = [
        r.strip()
        for r in os.environ.get("CT_EXTRA_REGIONS", "").split(",")
        if r.strip()
    ]
    extra_regions = (*extra_regions, *env_regions)

    # --- Validate time window ---
    if (start is None) != (end is None):
        raise click.UsageError("--start and --end must be used together.")
    if days is not None and start is not None:
        raise click.UsageError("--days and --start/--end are mutually exclusive.")
    if start is not None:
        _validate_date_range(start, end)  # type: ignore[arg-type]

    profile: str | None = ctx.obj["profile"]
    primary_region: str = ctx.obj["region"]

    all_regions = [primary_region, *extra_regions]

    # --- Cache lookup --------------------------------------------------------
    ck, key_params = _compute_cache_key(days, start, end, primary_region, extra_regions)
    records: list[dict] | None = None

    if not no_cache and not refresh:
        records = cache_mod.load(ck)
        if records is not None:
            click.echo(
                f"Loaded {len(records):,} events from cache "
                f"(use --refresh to re-fetch)."
            )

    if records is None:
        # Nothing cached (or bypassed) — fetch from AWS.
        if start is not None:
            click.echo(
                f"Fetching events {start.date()} → {end.date()} "  # type: ignore[union-attr]
                f"from {', '.join(all_regions)}..."
            )
        else:
            click.echo(
                f"Fetching {days or 30} day(s) of events "
                f"from {', '.join(all_regions)}..."
            )

        try:
            records = fetch_events(
                profile=profile,
                primary_region=primary_region,
                days=days,
                start=start,
                end=end,
                extra_regions=extra_regions,
            )
        except CredentialError as exc:
            raise click.ClickException(str(exc)) from exc
        except ValueError as exc:
            raise click.UsageError(str(exc)) from exc

        click.echo(f"Fetched {len(records):,} events.")

        if not no_cache:
            cache_mod.save(ck, records, key_params=key_params)
            click.echo(
                f"Cached to {cache_mod.DEFAULT_CACHE_DIR / (ck + '.json')}"
            )

    # --- Apply post-fetch filters ---
    records, applied_filters = _apply_filters(
        records,
        event_source=event_source,
        username=username,
        filter_region=filter_region,
        read_only=True if read_only else None,
        errors_only=errors_only,
    )
    if applied_filters:
        click.echo(f"After filters: {len(records):,} events remain.")

    # --- Aggregate ---
    summary = aggregate.summarize(records)

    # --- Build renderer metadata ---
    now = datetime.datetime.now(_UTC)
    if start is not None:
        range_start = start.date()
        range_end = end.date()  # type: ignore[union-attr]
    else:
        n = days or 30
        range_start = (now - datetime.timedelta(days=n)).date()
        range_end = now.date()

    meta = {
        "range_start":  range_start,
        "range_end":    range_end,
        "generated_at": now,
        "filters":      applied_filters,
    }

    # --- Write output ---
    out = pathlib.Path(output_dir)
    # parents=True + exist_ok=True has a known race/ordering bug on Python 3.13/Windows
    # when intermediate directories already exist; os.makedirs is reliable.
    import os as _os
    _os.makedirs(out, exist_ok=True)

    written: list[pathlib.Path] = []
    if output_format in ("md", "both"):
        p = out / "report.md"
        p.write_text(md_renderer.render(summary, meta), encoding="utf-8")
        written.append(p)
    if output_format in ("csv", "both"):
        p = out / "report.csv"
        p.write_text(csv_renderer.render(summary, meta), encoding="utf-8")
        written.append(p)

    for p in written:
        click.echo(f"Wrote {p}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_cache_key(
    days: int | None,
    start: datetime.datetime | None,
    end: datetime.datetime | None,
    primary_region: str,
    extra_regions: tuple[str, ...],
) -> tuple[str, dict]:
    """Return (hex_key, key_params) for the given time-window + regions."""
    now = datetime.datetime.now(_UTC)
    if start is not None:
        start_date = start.date()
        end_date = end.date()  # type: ignore[union-attr]
    else:
        n = days or 30
        start_date = (now - datetime.timedelta(days=n)).date()
        end_date = now.date()
    regions = sorted({primary_region, *extra_regions})
    key = cache_mod.cache_key(start_date, end_date, regions)
    params = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "regions": regions,
    }
    return key, params


def _validate_date_range(
    start: datetime.datetime,
    end: datetime.datetime,
) -> None:
    """Raise click.UsageError for any invalid --start/--end combination."""
    now    = datetime.datetime.now(_UTC)
    cutoff = now - datetime.timedelta(days=90)

    s = start if start.tzinfo else start.replace(tzinfo=_UTC)
    e = end   if end.tzinfo   else end.replace(tzinfo=_UTC)

    if s < cutoff:
        raise click.UsageError(
            f"--start {start.date()} is outside the 90-day LookupEvents window.\n"
            f"Earliest date allowed today: {cutoff.date()}."
        )
    if e > now + datetime.timedelta(days=1):
        raise click.UsageError(
            f"--end {end.date()} is in the future."
        )
    if e <= s:
        raise click.UsageError("--end must be after --start.")
    if (e - s).days > 90:
        raise click.UsageError(
            "Date range spans more than 90 days. "
            "LookupEvents only covers 90 days; narrow the window with --start/--end."
        )


def _apply_filters(
    records: list[dict],
    *,
    event_source: str | None,
    username: str | None,
    filter_region: str | None,
    read_only: bool | None,
    errors_only: bool,
) -> tuple[list[dict], dict[str, str]]:
    """Apply post-fetch filters; return (filtered_records, applied_filters_dict).

    applied_filters contains only the filters that were actually set, so
    renderers can embed them verbatim in self-describing output.
    """
    applied: dict[str, str] = {}

    if event_source:
        records = [r for r in records if r["event_source"] == event_source]
        applied["event_source"] = event_source
    if username:
        records = [r for r in records if r["username"] == username]
        applied["username"] = username
    if filter_region:
        records = [r for r in records if r["aws_region"] == filter_region]
        applied["region"] = filter_region
    if read_only is not None:
        records = [r for r in records if r["read_only"] == read_only]
        applied["read_only"] = "true"
    if errors_only:
        records = [r for r in records if r.get("error_code") is not None]
        applied["errors_only"] = "true"

    return records, applied


# ---------------------------------------------------------------------------
# serve command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int) -> None:
    """Start the web UI (requires: pip install 'cloudtrail-report[web]')."""
    try:
        import uvicorn
        import cloudtrail_report.web as web_mod
    except ImportError:
        raise click.ClickException(
            "Web dependencies not installed.\n"
            "Run: pip install \"cloudtrail-report[web]\""
        )
    web_mod._DEFAULT_PROFILE = ctx.obj["profile"] or ""
    web_mod._DEFAULT_REGION = ctx.obj["region"]
    click.echo(f"Starting web UI at http://{host}:{port}")
    uvicorn.run(web_mod.app, host=host, port=port, reload=False)
