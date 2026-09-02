# CloudTrail Audit Report

|  |  |
| --- | --- |
| Generated | 2026-08-25 12:00 UTC |
| Range | 2026-08-01 → 2026-08-25 |
| Total events | 4 |
| Errors | 1 |
| Write events | 1 |
| Read-only | 3 |
| Filters applied | _none — showing all events in range_ |

---

## Top Event Names

| Event Name | Count |
| --- | --- |
| GetObject | 1 |
| ListUsers | 1 |
| DescribeInstances | 1 |
| CreateUser | 1 |

## Top Principals

| Username | Count |
| --- | --- |
| alice | 2 |
| DeployRole/i-0abc123 | 1 |
| root | 1 |

## Top Source IPs

| Source IP | Count |
| --- | --- |
| 1.2.3.4 | 3 |
| 5.6.7.8 | 1 |

## By Event Source

| Service | Count |
| --- | --- |
| iam.amazonaws.com | 2 |
| s3.amazonaws.com | 1 |
| ec2.amazonaws.com | 1 |

## By Region

| Region | Count |
| --- | --- |
| us-east-1 | 3 |
| us-east-2 | 1 |

## Errors by Error Code

| Error Code | Count |
| --- | --- |
| AccessDenied | 1 |

## Activity by Day

| Date (UTC) | Events |
| --- | --- |
| 2026-08-24 | 2 |
| 2026-08-25 | 2 |

## Username × Event Source

| Username | iam.amazonaws.com | s3.amazonaws.com | ec2.amazonaws.com | Total |
| --- | --- | --- | --- | --- |
| alice | 1 |  | 1 | 2 |
| DeployRole/i-0abc123 |  | 1 |  | 1 |
| root | 1 |  |  | 1 |

## Username × Event Name

| Username | GetObject | ListUsers | DescribeInstances | CreateUser | Total |
| --- | --- | --- | --- | --- | --- |
| alice |  | 1 | 1 |  | 2 |
| DeployRole/i-0abc123 | 1 |  |  |  | 1 |
| root |  |  |  | 1 | 1 |