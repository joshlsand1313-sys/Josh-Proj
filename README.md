# CloudTrail Audit Reporter

Queries AWS CloudTrail management events via the **LookupEvents API** and writes human-readable audit reports in Markdown and/or CSV. No trail infrastructure is required — it works directly against the free 90-day Event History available in every AWS account.

---

## Install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .
```

This installs the `ct-report` command-line entry point.

To also install test dependencies:

```bash
pip install -e ".[dev]"
```

---

## Auth

The tool is read-only. Attach the policy in `infra/iam/cloudtrail-readonly-policy.json` to your IAM user or role — it grants only `cloudtrail:LookupEvents`, `DescribeTrails`, and `GetTrailStatus`.

**Named profile (most common):**

```bash
# Add to ~/.aws/credentials
[audit-ro]
aws_access_key_id     = AKIA...
aws_secret_access_key = ...

# Pass at runtime
ct-report --profile audit-ro run
# or set once for the shell session
export AWS_PROFILE=audit-ro
ct-report run
```

**AWS SSO:**

```bash
aws sso login --profile my-sso
ct-report --profile my-sso run
```

**Verify before running:**

```bash
aws cloudtrail lookup-events --max-items 1 --profile audit-ro
```

If that returns JSON you have the right permissions. Full setup details, MFA configuration, and deployed-environment (Lambda / ECS task role) instructions are in [`docs/setup.md`](docs/setup.md).

---

## Usage

Global flags (`--profile`, `--region`) **must appear before** the `run` subcommand:

```
ct-report [--profile PROFILE] [--region REGION] run [OPTIONS]
```

### Example 1 — 30-day Markdown report (default)

```bash
ct-report --profile audit-ro run
```

Fetches the last 30 days of management events from `us-east-1` and writes `report.md` in the current directory. Results are cached to `~/.cache/ct-report/` so the next run with the same date window is instant.

### Example 2 — Exact date range, both formats, custom output directory

```bash
ct-report --profile audit-ro run \
  --start 2026-05-27 \
  --end   2026-08-25 \
  --format both \
  --output ./reports/q3/
```

Writes `reports/q3/report.md` and `reports/q3/report.csv`. The `--end` date is inclusive. Both flags are required together; they are mutually exclusive with `--days`.

### Example 3 — Error triage: IAM write failures, multi-region, force re-fetch

```bash
ct-report --profile audit-ro --region us-east-1 run \
  --days 7 \
  --extra-region us-west-2 \
  --event-source iam.amazonaws.com \
  --errors-only \
  --refresh \
  --format csv \
  --output ./reports/iam-errors/
```

Queries `us-east-1` and `us-west-2`, keeps only IAM events that returned an error code, and writes a CSV. `--refresh` forces a live re-fetch and overwrites the cached entry — useful when you need up-to-the-minute data.

---

## All flags

Global flags (before `run`):

| Flag | Default | Description |
|---|---|---|
| `--profile NAME` | `$AWS_PROFILE` | Named AWS credentials profile |
| `--region REGION` | `us-east-1` | Primary region to query |

`run` flags:

| Flag | Default | Description |
|---|---|---|
| `--days N` | `30` | Days of history (1–90). Mutually exclusive with `--start`/`--end` |
| `--start YYYY-MM-DD` | — | Start of range (inclusive). Requires `--end` |
| `--end YYYY-MM-DD` | — | End of range (inclusive). Requires `--start` |
| `--extra-region REGION` | — | Additional region to query (repeatable) |
| `--event-source SERVICE` | — | Keep only events from this service, e.g. `ec2.amazonaws.com` |
| `--username NAME` | — | Keep only events from this principal |
| `--filter-region REGION` | — | Keep only events recorded in this region (post-fetch) |
| `--read-only` | off | Keep only read-only (non-mutating) events |
| `--errors-only` | off | Keep only events that returned an error |
| `--no-cache` | off | Skip reading and writing the disk cache |
| `--refresh` | off | Force re-fetch from AWS; overwrite cache |
| `--format md\|csv\|both` | `md` | Output format |
| `--output DIR` | `.` | Directory to write report file(s) into |

---

## Cache

Results are cached to `~/.cache/ct-report/<key>.json` keyed on the date window and queried regions. A 90-day full pull can take several minutes and is rate-limited; the cache makes re-runs with different filters essentially instant.

```bash
ct-report run --days 90            # fetches and caches
ct-report run --days 90 --errors-only   # cache hit — no AWS call
ct-report run --days 90 --refresh  # re-fetches and overwrites cache
ct-report run --days 90 --no-cache # skips cache entirely
```

---

## Sample output

```markdown
# CloudTrail Audit Report

|  |  |
| --- | --- |
| Generated     | 2026-08-25 14:32 UTC              |
| Range         | 2026-07-26 → 2026-08-25           |
| Total events  | 8,412                             |
| Errors        | 34                                |
| Write events  | 1,203                             |
| Read-only     | 7,209                             |
| Filters applied | _none — showing all events in range_ |

---

## Top Event Names

| Event Name | Count |
| --- | --- |
| DescribeInstances      | 1,842 |
| GetCallerIdentity      | 1,204 |
| ListBuckets            | 987   |
| DescribeSecurityGroups | 743   |
| AssumeRole             | 621   |

## Top Principals

| Username | Count |
| --- | --- |
| alice                  | 3,102 |
| DeployRole/i-0abc1234  | 2,891 |
| ci-runner/github-push  | 1,205 |
...
```

The CSV format (`--format csv`) writes a tidy long-format file with columns `section`, `dimension_a`, `dimension_b`, `count` — suitable for import into Excel, pandas, or any BI tool.

---

## Known limits

**90-day window.** LookupEvents only covers the past 90 days. There is no way to extend this limit with the current data source. For longer history, create an Organizations trail → S3 → Athena; the normalized field names in this tool map 1:1 to Athena columns.

**Management events only.** LookupEvents returns management-plane API calls (EC2 `RunInstances`, IAM `CreateUser`, S3 `CreateBucket`, etc.). It does not return data events (S3 `GetObject`/`PutObject`, DynamoDB reads/writes, Lambda invocations) even if a trail is configured to capture them.

**Single lookup attribute per API call.** The LookupEvents API accepts only one filter attribute at a time. All multi-field filtering in this tool (combining `--username`, `--event-source`, `--errors-only`, etc.) is done **post-fetch**: the full date window is downloaded first, then Python-side filters are applied locally. For large windows this means the full event volume is always fetched regardless of how narrow the filters are — which is exactly why the cache exists.

**Single AWS account per run.** LookupEvents queries one account. For cross-account auditing, run `ct-report` once per account (with the appropriate `--profile`) and compare the resulting CSVs.
