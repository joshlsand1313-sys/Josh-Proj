# CloudTrail Audit Reporter — Project Plan

> Status key: ✅ Complete · 🔄 In Progress · ⬜ Pending · 🔒 Blocked (dependency not met)

---

## Phase 0 — Scope & Design

### ✅ Task 1 — Data Source Decision

**Deliverable:** `data-source.md`

Compared LookupEvents API vs S3 + Athena across five dimensions and chose LookupEvents for the PoC.

| Dimension | LookupEvents | S3 + Athena |
|---|---|---|
| 90-day coverage | Built-in, free | Only from trail creation date |
| Event types | Management only | Management + data events |
| Cost | Free | Trail + Athena + S3 storage |
| Multi-account | Single account | Native Organizations support |
| Setup | Zero | Trail, bucket, Glue, Athena workgroup |

**Decision:** LookupEvents. No trail existed; S3+Athena would have had zero historical data. Limitations (management-only, 90 days, single account) are acceptable for a PoC.

**Post-PoC migration:** Create Organizations trail → S3 → Athena. LookupEvents field names map 1:1 to Athena columns; report logic won't change.

---

### ⬜ Task 2 — Report Spec

**Deliverable:** `docs/report-spec.md` with example output tables

**Blocks:** Tasks 6, 7, 8

Define:
- **Aggregations:** by event name, by username/principal, by event source, by region, by error code, by day
- **Filters:** date range, event source, username, region, read-only vs write, errors-only
- **Output formats:** `.md`, `.csv`, or both — pick one in this task
- Example tables for each aggregation so renderers have a spec to implement against

---

### ✅ Task 3 — AWS Access & IAM

**Deliverable:** `infra/iam/cloudtrail-readonly-policy.json` + `docs/setup.md`

Created the minimum IAM policy and documented both auth patterns.

**Policy** (`infra/iam/cloudtrail-readonly-policy.json`):
- `cloudtrail:LookupEvents`
- `cloudtrail:DescribeTrails`
- `cloudtrail:GetTrailStatus`
- No write permissions

**Auth documentation** (`docs/setup.md`):
- Local: named profile (`~/.aws/credentials`) or AWS SSO
- Deployed: IAM task role assumed automatically by Lambda/EC2/ECS — no stored keys
- Verification commands + troubleshooting guide

---

## Phase 1 — Core Script

### ✅ Task 4 — Project Scaffold

**Deliverable:** `pyproject.toml`, `.gitignore`, `README.md`, `src/` layout, git init

| File | Purpose |
|---|---|
| `pyproject.toml` | PEP 517 build config; pinned deps; entry point `ct-report` |
| `.gitignore` | Python artifacts, venvs, AWS credentials |
| `README.md` | Install, auth pointer, usage examples |
| `src/cloudtrail_report/__init__.py` | Package root; `__version__ = "0.1.0"` |

**Decisions:**
- CLI framework: **click 8.x** (over argparse — too verbose; over typer — less mature)
- Output: **jinja2** for HTML reports, **stdlib csv** for tabular export (no pandas needed)
- Deps pinned: `boto3>=1.34,<2`, `click>=8.1,<9`, `jinja2>=3.1,<4`

---

### ✅ Task 5 — Fetcher Module

**Deliverable:** `src/cloudtrail_report/fetch.py`

Full pagination + error-handling layer over LookupEvents.

- **Pagination:** `NextToken` loop; handled transparently in `_paginate_with_backoff`
- **Throttling:** exponential backoff (1 s base → 32 s cap) with ±25% random jitter; 7 retries before re-raise. Handles `ThrottlingException`, `RateExceededException`, `RequestThrottledException`, `Throttling`
- **Credential errors:** custom `CredentialError` with human-readable messages for `NoCredentialsError`, `ProfileNotFound`, `AccessDeniedException`, `ExpiredTokenException`, `UnauthorizedOperation` — each includes a remediation hint
- **Multi-region:** `extra_regions` parameter; each region queried independently; results merged and sorted by `event_time`
- **Date window:** `_resolve_window` handles `--days` (relative) or explicit `--start`/`--end` (end made inclusive). Validates 90-day cap
- **Output:** calls `normalize.normalize(raw, region)` — no raw API shapes leak downstream

**CLI additions:** `--start`/`--end YYYY-MM-DD` (mutually exclusive with `--days`), `--extra-region` (repeatable)

---

### ✅ Task 6 — Normalizer Module

**Deliverable:** `src/cloudtrail_report/normalize.py`

Parses the `CloudTrailEvent` JSON blob and resolves `userIdentity` to a stable, flat schema. This is the boundary where all raw API shapes are absorbed.

**Stable record schema:**

| Field | Type | Source |
|---|---|---|
| `event_id` | str | `CloudTrailEvent.eventID` |
| `event_time` | datetime (UTC) | boto3 `EventTime`, fallback to `eventTime` ISO string |
| `event_name` | str | `CloudTrailEvent.eventName` |
| `event_source` | str | `CloudTrailEvent.eventSource` |
| `principal_type` | str | `userIdentity.type` |
| `username` | str | resolved (see below) |
| `account_id` | str | `userIdentity.accountId` |
| `aws_region` | str | `CloudTrailEvent.awsRegion` → queried region |
| `source_ip` | str | `CloudTrailEvent.sourceIPAddress` |
| `user_agent` | str | `CloudTrailEvent.userAgent` |
| `request_id` | str | `CloudTrailEvent.requestID` |
| `read_only` | bool | `CloudTrailEvent.readOnly` (bool or string coerced) |
| `error_code` | str \| None | `CloudTrailEvent.errorCode` |
| `error_message` | str \| None | `CloudTrailEvent.errorMessage` |
| `resources` | list[{arn, type}] | `CloudTrailEvent.resources` → `Resources` |
| `access_key_id` | str | `userIdentity.accessKeyId` → `AccessKeyId` |

**`username` resolution by `principal_type`:**

| Type | username value |
|---|---|
| `IAMUser` | `userIdentity.userName` |
| `Root` | `"root"` |
| `AssumedRole` | `"<role-name>/<session-name>"` from sessionContext + ARN |
| `FederatedUser` | suffix after `:` in `principalId` |
| `AWSService` | `userIdentity.invokedBy` |
| `AWSAccount` | suffix after `:` in `principalId`, or `"account:<id>"` |
| `SAMLUser` / `WebIdentityUser` | `userName` → `principalId` suffix → type-name |
| Missing / unknown | `"unknown"` |

---

### ✅ Task 7 — Aggregator Module

**Deliverable:** `src/cloudtrail_report/aggregate.py`

**Depends on:** Tasks 2, 6

Pure functions over the normalized record list — no AWS calls, no I/O.

**Functions implemented:**

| Function | Description |
|---|---|
| `count_by(records, field)` | Generic group-by count for any field (str/None-safe) |
| `count_by_day(records)` | Per-calendar-day counts from `event_time.date()` |
| `count_by_error_code(records)` | Error events only; skips records with `error_code=None` |
| `top_n(counts, n)` | Sorted (key, count) list, descending, length-capped |
| `crosstab(records, row_field, col_field)` | `{row: {col: count}}` for any two fields |
| `summarize(records, *, top=10)` | Runs all aggregations; single dict for renderers |

**`summarize` output keys:** `total_events`, `error_count`, `read_only_count`, `write_count`, `by_event_name`, `by_username`, `by_event_source`, `by_region`, `by_error_code`, `by_day`, `top_event_names`, `top_usernames`, `top_source_ips`, `xtab_username_by_source`, `xtab_username_by_event`

**Design notes:**
- `count_by` skips `None`; includes empty strings (e.g. `source_ip=""` for internal AWS calls is valid data)
- `crosstab` skips records where either field is `None`
- `summarize` is the sole input to renderers — no further computation needed (makes Task 8 and Task 11 clean)

---

### ✅ Task 8 — Renderers

**Deliverable:** `src/cloudtrail_report/render/md.py`, `src/cloudtrail_report/render/csv.py`

**Depends on:** Tasks 2, 7

Both renderers share the same call signature:
```python
render(summary: dict, meta: dict) -> str
```
`meta` keys: `range_start` (date), `range_end` (date), `generated_at` (datetime UTC), `filters` (dict[str, str] — applied filters only, may be empty).

**CSV format decision (Task 2 gap resolved):** tidy long-format single file. Valid RFC 4180 throughout — no comment lines.

| Column | Purpose |
|---|---|
| `section` | `_meta`, `by_event_name`, `by_username`, `by_event_source`, `by_region`, `by_error_code`, `by_day`, `xtab_username_by_source`, `xtab_username_by_event` |
| `dimension_a` | Field value (or metadata key for `_meta` rows) |
| `dimension_b` | Second field value for cross-tabs; empty for single-dimension rows |
| `count` | Event count (or metadata value for `_meta` rows) |

`_meta` rows appear first: `generated_at`, `range_start`, `range_end`, `total_events`, `error_count`, `read_only_count`, `write_count`, then one row per applied filter as `filter.<name>`.

**Markdown sections (in order):**
1. Header table: generated, range, totals, filters applied
2. Top Event Names (pre-sorted top-N from `summarize`)
3. Top Principals
4. Top Source IPs
5. By Event Source (all, sorted by count)
6. By Region (all, sorted by count)
7. Errors by Error Code (skipped with note if no errors)
8. Activity by Day (chronological)
9. Username × Event Source cross-tab (top 20 rows × top 10 cols)
10. Username × Event Name cross-tab (top 20 rows × top 10 cols)

**Notes:**
- `|` in cell values is escaped to `\|` in markdown
- Cross-tabs truncate to top-20 rows × top-10 cols with a trailing note
- Empty sections return empty string and are dropped from the join

---

### ✅ Task 9 — CLI Wiring

**Deliverable:** `src/cloudtrail_report/cli.py` (complete)

**Depends on:** Tasks 5, 6, 7, 8

Full rewrite — wired to `aggregate.summarize` + `render/md` + `render/csv`. Old `report.build_report` (html) no longer used from CLI.

**`main` group flags:**

| Flag | Default | Notes |
|---|---|---|
| `--profile` | `$AWS_PROFILE` | Named profile |
| `--region` | `us-east-1` | Primary query region |

**`run` command flags:**

| Flag | Default | Notes |
|---|---|---|
| `--days N` | 30 | 1–90 (IntRange); mutually exclusive with --start/--end |
| `--start YYYY-MM-DD` | — | Requires --end |
| `--end YYYY-MM-DD` | — | Requires --start; inclusive |
| `--extra-region REGION` | — | Repeatable; adds query regions |
| `--event-source SERVICE` | — | Post-fetch filter |
| `--username NAME` | — | Post-fetch filter |
| `--filter-region REGION` | — | Post-fetch filter (distinct from `--region` query target) |
| `--read-only` | off | Post-fetch filter: read-only events only |
| `--errors-only` | off | Post-fetch filter: error events only |
| `--format md\|csv\|both` | `md` | Output format |
| `--output DIR` | `.` | Output directory; created if absent |

**90-day validation (`_validate_date_range`):** raises `click.UsageError` (not ValueError) for: start before 90-day cutoff (with exact earliest-allowed date), end in the future, end ≤ start, range > 90 days. Checked before any AWS call.

**Filter pipeline (`_apply_filters`):** returns `(filtered_records, applied_filters_dict)`. Only applied filters appear in the dict — fed directly to `meta["filters"]` so renderers embed them verbatim. Reports emit `After filters: N events remain.` only when at least one filter was active.

**Data flow:** `fetch_events()` → `_apply_filters()` → `aggregate.summarize()` → `md_renderer.render()` and/or `csv_renderer.render()` → write `report.md` / `report.csv` to output dir.

---

### ✅ Task 10 — Local Caching

**Deliverable:** `src/cloudtrail_report/cache.py` + CLI flags in `cli.py`

**Depends on:** Task 5

Cache raw fetched events to disk (JSON) keyed by date range + region, with `--no-cache` / `--refresh` flags.

**Cache location:** `~/.cache/ct-report/<key>.json` (created on first write).

**Cache key:** SHA-256 (16 hex chars) of `start_date|end_date|region1|region2|…` (regions sorted). Keyed on dates, not datetimes, so `--days 30` hits the same entry on multiple runs the same day. Post-fetch filters are NOT part of the key — the cache holds pre-filter data so you can re-run with different filters for free.

**Cache file format:**
```json
{"key_params": {"start": "2026-07-26", "end": "2026-08-25", "regions": ["us-east-1"]},
 "cached_at": "2026-08-25T12:00:00+00:00",
 "record_count": 1234,
 "records": [...]}
```
`event_time` is serialized as an ISO-8601 string and deserialized back to `datetime` on load. Corrupt or unreadable entries log a warning and fall through to a live fetch.

**New CLI flags on `run`:**

| Flag | Behaviour |
|---|---|
| *(default)* | Try cache → hit: use it; miss: fetch + save |
| `--refresh` | Skip cache read; fetch from AWS; overwrite cache |
| `--no-cache` | Skip cache read AND write entirely |

**Data flow change in `cli.py`:**
`_compute_cache_key()` → `cache.load()` → (miss) → `fetch_events()` → `cache.save()` → filters → aggregate → render

---

## Phase 2 — Quality

### ✅ Task 11 — Test Suite

**Depends on:** Tasks 6, 7, 8

**67 tests, 0 warnings — all green.**

**Test layout:**

| File | What it covers |
|---|---|
| `tests/conftest.py` | Raw-event builders (one per identity type + error + minimal) + `sample_records` / `sample_summary` / `sample_meta` pytest fixtures |
| `tests/test_normalize.py` | 24 tests — all 8 identity types, error fields, `read_only` bool/string coercions, `event_time` boto/ISO/absent paths, resources, access_key_id fallback |
| `tests/test_aggregate.py` | 18 tests — `count_by`, `count_by_day`, `count_by_error_code`, `top_n`, `crosstab`, `summarize` (counts, keys, empty, `top` param) |
| `tests/test_fetch.py` | 5 tests — single page, pagination, ThrottlingException retry, AccessDeniedException → CredentialError, ProfileNotFound → CredentialError; uses `botocore.stub.Stubber` |
| `tests/test_render.py` | 10 tests — MD + CSV golden-file comparison, header content, no-errors message, filters inline, pipe escaping, CSV section coverage |
| `tests/test_cache.py` | 11 tests — key stability/hex/region-order, save+load round-trip (records + datetime), directory creation, miss returns None, corrupt JSON returns None, key_params written |

**Fixtures:**
- Raw event builders in `conftest.py` (plain functions, not pytest fixtures) so they can be reused in `test_fetch.py` without fixture injection
- Golden files in `tests/golden/report.md` and `tests/golden/report.csv` — regenerated automatically if deleted; comparison normalises `\r\n` vs `\n`

**`pyproject.toml` additions:**
```toml
[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths  = ["tests"]
```

**Install dev deps:** `pip install -e ".[dev]"`

---

### ✅ Task 12 — Docs

**Depends on:** Task 9

**Deliverable:** `README.md` (complete rewrite)

Sections:
- **Install** — venv + `pip install -e .`; dev deps via `.[dev]`
- **Auth** — named profile, SSO, verify command; pointer to `docs/setup.md` for full details
- **Usage** — three worked examples:
  1. Default 30-day Markdown report (shows caching behaviour)
  2. Exact date range (`--start`/`--end`), both formats, custom output dir
  3. Error triage: `--event-source iam.amazonaws.com --errors-only --refresh`, multi-region, CSV
- **All flags** — two tables (global / `run`) covering every option including cache flags
- **Cache** — four one-liner examples showing default / filter reuse / `--refresh` / `--no-cache`
- **Sample output** — markdown header + Top Event Names + Top Principals excerpt with realistic numbers
- **Known limits**:
  - 90-day window (LookupEvents hard limit; migration path = Organizations trail → S3 → Athena)
  - Management events only (no data events regardless of trail config)
  - Single lookup attribute per API call — all multi-field filtering is post-fetch, so full volume is always fetched (cache mitigates this)
  - Single AWS account per run

---

### ✅ Task 13 — Validation Run

**Depends on:** Tasks 9, 3

Run against a real AWS account. Spot-check event counts against the CloudTrail console. Record timing and record volume for a full 90-day pull — this number sizes Phase 3 (sync render vs background job).

**Account:** Solutions-CCCI (`387075078863`) via `DeveloperRead` SSO role. Auth profile: `cloudtrail`.

**Bugs found and fixed during this run:**
- `cloudtrail` profile had wrong `sso_role_name` (`AWSReservedSSO_DeveloperRead_69df50b99e0d373c` → `DeveloperRead`) in `~/.aws/config`
- Python 3.13 pathlib `mkdir(parents=True, exist_ok=True)` bug on Windows when intermediate parent already exists — fixed in `cli.py` by replacing with `os.makedirs(out, exist_ok=True)`

**Results — 1-day pull (2026-08-27):**

| Metric | Value |
|---|---|
| Events | 485 |
| Errors | 402 (83%) |
| Write events | 0 |
| Wall time | 7.7 s |

**Results — 90-day pull (2026-05-30 → 2026-08-28):**

| Metric | Value |
|---|---|
| Events | 16,680 |
| Errors | 8,100 (49%) |
| Write events | 137 |
| Wall time | 182.9 s (~3 min) |
| Rate | ~91 events/s |

**Phase 3 sizing conclusion:** 182.9 s for a cold full-range pull rules out synchronous HTTP rendering for the 90-day case. A web UI must either (a) default to a shorter window (≤7 days ~14 s est.), or (b) run the fetch as a background job and poll/redirect when ready. Recommend background job + cache: the cache makes subsequent same-day requests instant regardless of window size.

**Spot-check notes:**
- Top event `ListManagedNotificationEvents` (2,229 over 90 days) consistent with console notification polling
- `config.amazonaws.com` appears as source IP for Config recorder events — expected
- Principal `solutions-ccci-config-recorder-role/configLambdaExecution` is the AWS Config recorder — consistent with 3,080 read events

**Output files:** `validation-runs/day1/` and `validation-runs/day90/`

---

## Phase 3 — Deployment Prep *(scoped now, built after PoC sign-off)*

### ✅ Task 14 — Containerize

**Depends on:** Task 9

Dockerfile: slim Python base, non-root user, env-var config to replace CLI flags, healthcheck.

**Deliverables:** `Dockerfile`, `.dockerignore`, env-var additions to `cli.py` and `cache.py`

**Env-var additions to `cli.py`:**

| Env var | CLI flag | Notes |
|---|---|---|
| `AWS_PROFILE` | `--profile` | Already existed |
| `CT_REGION` | `--region` | Already existed |
| `CT_DAYS` | `--days` | Already existed |
| `CT_START` | `--start` | Already existed |
| `CT_END` | `--end` | Already existed |
| `CT_EXTRA_REGIONS` | `--extra-region` | Comma-separated; parsed manually in `run()` — click doesn't support env-var multiples |
| `CT_EVENT_SOURCE` | `--event-source` | Added |
| `CT_USERNAME` | `--username` | Added |
| `CT_FILTER_REGION` | `--filter-region` | Added |
| `CT_READ_ONLY` | `--read-only` | Added |
| `CT_ERRORS_ONLY` | `--errors-only` | Added |
| `CT_NO_CACHE` | `--no-cache` | Added |
| `CT_REFRESH` | `--refresh` | Added |
| `CT_FORMAT` | `--format` | Added |
| `CT_OUTPUT` | `--output` | Added |

**`cache.py`:** Added `CT_CACHE_DIR` env var support for `DEFAULT_CACHE_DIR` — overrides `~/.cache/ct-report` so the container can redirect to a mounted volume or `/tmp`.

**Dockerfile decisions:**
- Base: `python:3.13-slim`
- Non-root user: uid 1001, home dir created (`/home/app`) so `Path.home()` resolves cleanly
- Output: `CT_OUTPUT=/reports`; `/reports` owned by `app`, declared as `VOLUME`
- Healthcheck: `ct-report --help` — verifies binary + package are intact
- Entrypoint: `ct-report run` — all config via env vars; override individual options with `docker run image run --days 7`

**Usage:**
```bash
# Basic run — writes /reports/report.md inside the container
docker run \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... -e AWS_SESSION_TOKEN=... \
  -e CT_REGION=us-east-1 -e CT_DAYS=30 \
  -v $(pwd)/out:/reports \
  cloudtrail-report

# With filters and CSV output
docker run \
  -e CT_FORMAT=csv -e CT_EVENT_SOURCE=iam.amazonaws.com -e CT_ERRORS_ONLY=1 \
  -v $(pwd)/out:/reports \
  cloudtrail-report
```

---

### 🔄 Task 15 — Web Layer Spike

**Depends on:** Tasks 13, 14

Thin FastAPI wrapper with background-job pattern (decided by Task 13 timing).

**Completed:**
- `src/cloudtrail_report/web.py` — FastAPI app: filter form (`GET /`), job submit (`POST /run`), job status page (`GET /job/{id}`), polling endpoint (`GET /job/{id}/status`), health check
- `src/cloudtrail_report/jobs.py` — `JobStore`: synchronous cache check (instant for cached windows), background daemon thread for live fetches; `_run_report` → `fetch_events` → cache save → `md_renderer.render`
- `pyproject.toml` — `[web]` optional dep group: `fastapi>=0.115`, `uvicorn[standard]>=0.30`, `python-multipart>=0.0.9`
- `cli.py` — `serve` command wired to uvicorn; now passes `--profile` and `--region` from main group into `web._DEFAULT_PROFILE` / `web._DEFAULT_REGION` so the form pre-fills with the correct credentials and region

**In progress / known issues:**
- Default region fixed to `us-east-2`; profile pre-filled from `--profile` flag on `serve`
- Long fetches (>30 days) still show "Fetching…" with no progress indicator — acceptable for now

---

### ⬜ Task 16 — AWS Deployment Plan

**Deliverable:** `docs/deployment-plan.md`

**Depends on:** Task 15

Decide: ECS Fargate vs App Runner vs Lambda. Cover: ALB + custom domain + ACM cert; task role replacing local credentials; authentication (Cognito / ALB OIDC / IdP) — this report exposes who did what in your account and must not be publicly reachable; log/report persistence in S3.
