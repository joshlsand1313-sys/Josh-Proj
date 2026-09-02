from __future__ import annotations

import datetime
import time
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Literal

JOB_TIMEOUT_SECONDS = 600  # 10 minutes

from cloudtrail_report import aggregate, cache as cache_mod
from cloudtrail_report.fetch import fetch_events
from cloudtrail_report.render import md as md_renderer

_UTC = datetime.timezone.utc


@dataclass
class Job:
    job_id: str
    status: Literal["pending", "running", "done", "error"]
    created_at: datetime.datetime
    params: dict[str, Any]
    report_md: str | None = None
    error: str | None = None
    pages_done: int = 0
    events_so_far: int = 0


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}

    def submit(self, params: dict[str, Any]) -> str:
        job_id = uuid.uuid4().hex[:12]

        # Synchronous cache check — returns "done" instantly on a hit, no thread needed.
        cached = _check_cache(params)
        if cached is not None:
            job = Job(
                job_id=job_id,
                status="done",
                created_at=datetime.datetime.now(_UTC),
                params=params,
                report_md=cached,
            )
            with self._lock:
                self._jobs[job_id] = job
            return job_id

        job = Job(
            job_id=job_id,
            status="pending",
            created_at=datetime.datetime.now(_UTC),
            params=params,
        )
        with self._lock:
            self._jobs[job_id] = job
        threading.Thread(target=self._worker, args=(job_id,), daemon=True).start()
        threading.Thread(target=self._watchdog, args=(job_id,), daemon=True).start()
        return job_id

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _worker(self, job_id: str) -> None:
        with self._lock:
            self._jobs[job_id].status = "running"

        def _on_progress(pages: int, events: int) -> None:
            with self._lock:
                job = self._jobs.get(job_id)
                if job:
                    job.pages_done = pages
                    job.events_so_far = events

        try:
            report_md = _run_report(self._jobs[job_id].params, on_progress=_on_progress)
            with self._lock:
                self._jobs[job_id].report_md = report_md
                self._jobs[job_id].status = "done"
        except Exception as exc:
            with self._lock:
                self._jobs[job_id].error = str(exc)
                self._jobs[job_id].status = "error"

    def _watchdog(self, job_id: str) -> None:
        time.sleep(JOB_TIMEOUT_SECONDS)
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status in ("pending", "running"):
                job.status = "error"
                job.error = (
                    f"Timed out after {JOB_TIMEOUT_SECONDS // 60} minutes. "
                    "This region may have too many events. Try a shorter date range, "
                    "or run ct-report from the CLI to pre-populate the cache."
                )


store = JobStore()


# ---------------------------------------------------------------------------
# Helpers shared by cache check and worker
# ---------------------------------------------------------------------------

def _resolve_window(params: dict[str, Any]) -> tuple[datetime.date, datetime.date]:
    start_str = params.get("start") or ""
    end_str   = params.get("end")   or ""
    if start_str and end_str:
        return (
            datetime.date.fromisoformat(start_str),
            datetime.date.fromisoformat(end_str),
        )
    now = datetime.datetime.now(_UTC)
    n = int(params.get("days") or 30)
    return (now - datetime.timedelta(days=n)).date(), now.date()


def _parse_extra_regions(params: dict[str, Any]) -> list[str]:
    return [r.strip() for r in (params.get("extra_regions") or "").split(",") if r.strip()]


def _check_cache(params: dict[str, Any]) -> str | None:
    """Return a rendered report string if the cache holds the raw records, else None."""
    start_date, end_date = _resolve_window(params)
    primary_region = params.get("region") or "us-east-1"
    regions = sorted({primary_region, *_parse_extra_regions(params)})
    ck = cache_mod.cache_key(start_date, end_date, regions)
    records = cache_mod.load(ck)
    if records is None:
        return None
    return _build_report(records, params, start_date, end_date)


def _run_report(params: dict[str, Any], on_progress=None) -> str:
    start_date, end_date = _resolve_window(params)
    primary_region = params.get("region") or "us-east-1"
    extra_regions  = _parse_extra_regions(params)
    regions = sorted({primary_region, *extra_regions})

    ck = cache_mod.cache_key(start_date, end_date, regions)
    records = cache_mod.load(ck)

    if records is None:
        start_str = params.get("start") or ""
        if start_str:
            start_dt = datetime.datetime(start_date.year, start_date.month, start_date.day, tzinfo=_UTC)
            end_dt   = datetime.datetime(end_date.year,   end_date.month,   end_date.day,   tzinfo=_UTC)
            days_val = None
        else:
            start_dt = end_dt = None
            days_val = int(params.get("days") or 30)

        records = fetch_events(
            profile=params.get("profile") or None,
            primary_region=primary_region,
            days=days_val,
            start=start_dt,
            end=end_dt,
            extra_regions=tuple(extra_regions),
            on_progress=on_progress,
        )
        cache_mod.save(ck, records, key_params={
            "start":   start_date.isoformat(),
            "end":     end_date.isoformat(),
            "regions": regions,
        })

    return _build_report(records, params, start_date, end_date)


def _build_report(
    records: list[dict],
    params: dict[str, Any],
    start_date: datetime.date,
    end_date: datetime.date,
) -> str:
    event_source  = params.get("event_source")  or None
    username      = params.get("username")       or None
    filter_region = params.get("filter_region")  or None
    read_only     = bool(params.get("read_only"))
    errors_only   = bool(params.get("errors_only"))

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
    if read_only:
        records = [r for r in records if r["read_only"]]
        applied["read_only"] = "true"
    if errors_only:
        records = [r for r in records if r.get("error_code")]
        applied["errors_only"] = "true"

    summary = aggregate.summarize(records)
    meta = {
        "range_start":  start_date,
        "range_end":    end_date,
        "generated_at": datetime.datetime.now(_UTC),
        "filters":      applied,
    }
    return md_renderer.render(summary, meta)
