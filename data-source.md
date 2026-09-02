# Phase 0 Task 1 — Data Source Decision

## Options Compared

| Dimension | LookupEvents API | S3 + Athena |
|---|---|---|
| **90-day coverage** | Built-in. Event History retains the last 90 days of management events automatically, no setup required. | Unlimited retention, but only from the moment a trail is created. No historical data before the trail exists. |
| **Management vs data events** | Management events only (API calls that create, modify, or delete resources). Data events (S3 object-level, Lambda invocations, etc.) are not available. | Both management and data events, depending on what the trail is configured to log. Data events must be explicitly enabled. |
| **Cost** | Free. LookupEvents is included in the AWS CloudTrail free tier with no per-query charge. | Trail delivery to S3 is free for management events; data events incur a per-event fee (~$0.10/100k). Athena charges per TB scanned (~$5/TB). Glue catalog, S3 storage, and S3 request costs also apply. |
| **Multi-account / Organizations support** | Single account only. The API returns events for the account whose credentials are used. Cross-account queries require calling the API separately per account. | Native multi-account support via an AWS Organizations trail, which aggregates events from all member accounts into one S3 bucket and one Athena table. |
| **Query speed and flexibility** | Limited. Supports filtering by a single attribute at a time (e.g., username, resource type, event name). Returns at most 50 results per page; full 90-day scans require pagination and client-side filtering. | High flexibility. Standard SQL over the full dataset; multi-column filters, aggregations, and joins are all supported. Query speed depends on partition design but is generally fast for targeted date ranges. |
| **Setup complexity** | None. Available immediately in every AWS account with no configuration. | High. Requires creating a trail, an S3 bucket with appropriate bucket policy, an Athena workgroup, a Glue Data Catalog database and table, and S3 partition management (or partition projection). |

---

## Recommendation: LookupEvents API

**Use LookupEvents for the PoC.**

We do not currently have a CloudTrail trail configured, which means an S3 + Athena approach would have no data to query until a trail is created, an S3 bucket is provisioned, and Athena is wired up — none of which exist yet. LookupEvents, by contrast, is available right now against the last 90 days of management events at no cost and with zero infrastructure.

The limitations of LookupEvents are acceptable for a PoC:

- **90-day window** is sufficient to validate report structure and usefulness.
- **Management events only** covers the highest-value signals for a security/audit reporting use case (IAM changes, resource creation/deletion, console logins).
- **Single-account scope** is fine at the PoC stage; multi-account expansion is a post-PoC concern.

If the PoC proves valuable and the project graduates to production, the natural migration path is to create an Organizations trail, deliver logs to S3, and switch the query layer to Athena. The report logic built against LookupEvents maps directly onto the same fields in Athena, making that migration low-risk.

**Decision: LookupEvents API for Phase 0.**

