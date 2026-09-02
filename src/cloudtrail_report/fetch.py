from __future__ import annotations

import datetime
import logging
import random
import time
from collections.abc import Generator

import boto3
import botocore.exceptions

from cloudtrail_report.normalize import normalize

log = logging.getLogger(__name__)

_BASE_BACKOFF = 1.0
_MAX_BACKOFF = 32.0
_MAX_RETRIES = 7

_THROTTLE_CODES = frozenset({
    "ThrottlingException",
    "RateExceededException",
    "RequestThrottledException",
    "Throttling",
})
_AUTH_CODES = frozenset({
    "AccessDeniedException",
    "AuthFailure",
    "ExpiredTokenException",
    "InvalidClientTokenId",
    "UnauthorizedOperation",
})


class CredentialError(RuntimeError):
    """Raised when credentials are absent or lack required permissions."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_events(
    profile: str | None,
    primary_region: str,
    days: int | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    extra_regions: tuple[str, ...] | list[str] = (),
    on_progress=None,
) -> list[dict]:
    """Fetch and normalize CloudTrail management events.

    Supply either `days` (lookback from now) or explicit `start`/`end` UTC
    datetimes — not both. `extra_regions` adds regions beyond `primary_region`.

    Returns a flat list of normalized records sorted ascending by event_time.
    Records are API-agnostic dicts; no boto3/CloudTrail-specific keys leak out.
    """
    start_time, end_time = _resolve_window(days, start, end)

    try:
        session = boto3.Session(profile_name=profile)
    except botocore.exceptions.ProfileNotFound as exc:
        raise CredentialError(f"AWS profile not found: {exc}") from exc

    regions = [primary_region] + [r for r in extra_regions if r != primary_region]
    records: list[dict] = []
    pages = 0
    total = 0

    def _page_cb(n: int) -> None:
        nonlocal pages, total
        pages += 1
        total += n
        if on_progress is not None:
            on_progress(pages, total)

    for region in regions:
        log.info("Querying %s: %s → %s", region, start_time.date(), end_time.date())
        try:
            client = session.client("cloudtrail", region_name=region)
            for raw in _paginate_with_backoff(client, start_time, end_time, on_page=_page_cb):
                records.append(normalize(raw, region))
        except botocore.exceptions.NoCredentialsError as exc:
            raise CredentialError(
                "No AWS credentials found. Run `aws configure` or set AWS_PROFILE."
            ) from exc
        except botocore.exceptions.ProfileNotFound as exc:
            raise CredentialError(str(exc)) from exc

    records.sort(key=lambda r: r["event_time"])
    return records


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_window(
    days: int | None,
    start: datetime.datetime | None,
    end: datetime.datetime | None,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Return (start_time, end_time) as UTC-aware datetimes."""
    utc = datetime.timezone.utc

    if start is not None or end is not None:
        if start is None or end is None:
            raise ValueError("--start and --end must be used together.")
        if start.tzinfo is None:
            start = start.replace(tzinfo=utc)
        if end.tzinfo is None:
            # treat end as inclusive: extend to end of the given day
            end = (end + datetime.timedelta(days=1)).replace(tzinfo=utc)
        if end <= start:
            raise ValueError("--end must be after --start.")
        if (end - start).days > 90:
            raise ValueError("Date range exceeds the 90-day LookupEvents limit.")
        return start, end

    days = days if days is not None else 30
    now = datetime.datetime.now(utc)
    return now - datetime.timedelta(days=days), now


def _paginate_with_backoff(
    client,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    on_page=None,
) -> Generator[dict, None, None]:
    """Yield raw LookupEvents items, retrying throttle errors with jittered backoff."""
    kwargs: dict = {"StartTime": start_time, "EndTime": end_time}
    retries = 0

    while True:
        try:
            response = client.lookup_events(**kwargs)
            retries = 0
        except botocore.exceptions.ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in _THROTTLE_CODES:
                if retries >= _MAX_RETRIES:
                    raise
                delay = min(_MAX_BACKOFF, _BASE_BACKOFF * (2 ** retries))
                delay *= random.uniform(0.75, 1.25)
                log.warning(
                    "Throttled (%s); retrying in %.1fs (attempt %d/%d)",
                    code, delay, retries + 1, _MAX_RETRIES,
                )
                time.sleep(delay)
                retries += 1
                continue
            if code in _AUTH_CODES:
                raise CredentialError(
                    f"Permission denied ({code}). Attach the policy in "
                    "infra/iam/cloudtrail-readonly-policy.json to your IAM user or role."
                ) from exc
            raise

        events = response.get("Events", [])
        yield from events
        if on_page is not None:
            on_page(len(events))

        next_token = response.get("NextToken")
        if not next_token:
            break
        kwargs["NextToken"] = next_token


