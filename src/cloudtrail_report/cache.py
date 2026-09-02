from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import pathlib

log = logging.getLogger(__name__)

_env_cache_dir = os.environ.get("CT_CACHE_DIR")
DEFAULT_CACHE_DIR: pathlib.Path = (
    pathlib.Path(_env_cache_dir) if _env_cache_dir
    else pathlib.Path.home() / ".cache" / "ct-report"
)

_UTC = datetime.timezone.utc


def cache_key(
    start_date: datetime.date,
    end_date: datetime.date,
    regions: list[str],
) -> str:
    """16-hex-char key, stable for the same (date_range, sorted_regions) tuple."""
    fingerprint = "|".join([
        start_date.isoformat(),
        end_date.isoformat(),
        *sorted(regions),
    ])
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


def load_day(
    date: datetime.date,
    regions: list[str],
    cache_dir: pathlib.Path = DEFAULT_CACHE_DIR,
) -> list[dict] | None:
    """Return cached records for a single calendar day, or None on a miss."""
    key = cache_key(date, date + datetime.timedelta(days=1), regions)
    return load(key, cache_dir)


def save_day(
    date: datetime.date,
    regions: list[str],
    records: list[dict],
    cache_dir: pathlib.Path = DEFAULT_CACHE_DIR,
) -> None:
    """Persist records for a single calendar day."""
    end = date + datetime.timedelta(days=1)
    key = cache_key(date, end, regions)
    save(key, records, cache_dir, key_params={
        "start": date.isoformat(),
        "end": end.isoformat(),
        "regions": sorted(regions),
    })


def load(key: str, cache_dir: pathlib.Path = DEFAULT_CACHE_DIR) -> list[dict] | None:
    """Return cached records for *key*, or None on a miss or corrupt entry."""
    path = cache_dir / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        records = [_decode_record(r) for r in data["records"]]
        log.debug(
            "Cache hit %s: %d records, cached %s",
            key, len(records), data.get("cached_at", "?"),
        )
        return records
    except Exception as exc:  # noqa: BLE001
        log.warning("Cache entry %s unreadable; ignoring: %s", path, exc)
        return None


def save(
    key: str,
    records: list[dict],
    cache_dir: pathlib.Path = DEFAULT_CACHE_DIR,
    *,
    key_params: dict | None = None,
) -> None:
    """Persist *records* to disk under *key*."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.json"
    payload = {
        "key_params": key_params or {},
        "cached_at": datetime.datetime.now(_UTC).isoformat(),
        "record_count": len(records),
        "records": [_encode_record(r) for r in records],
    }
    path.write_text(
        json.dumps(payload, separators=(",", ":")),
        encoding="utf-8",
    )
    log.debug("Cache saved %s (%d records)", path, len(records))


# ---------------------------------------------------------------------------
# Internal serialization
# ---------------------------------------------------------------------------

def _encode_record(r: dict) -> dict:
    out = dict(r)
    if isinstance(out.get("event_time"), datetime.datetime):
        out["event_time"] = out["event_time"].isoformat()
    return out


def _decode_record(r: dict) -> dict:
    out = dict(r)
    if isinstance(out.get("event_time"), str):
        out["event_time"] = datetime.datetime.fromisoformat(out["event_time"])
    return out
