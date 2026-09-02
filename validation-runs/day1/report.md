# CloudTrail Audit Report

|  |  |
| --- | --- |
| Generated | 2026-08-28 06:01 UTC |
| Range | 2026-08-27 → 2026-08-28 |
| Total events | 485 |
| Errors | 402 |
| Write events | 0 |
| Read-only | 485 |
| Filters applied | _none — showing all events in range_ |

---

## Top Event Names

| Event Name | Count |
| --- | --- |
| ListManagedNotificationEvents | 92 |
| GetAccountPlanState | 69 |
| GetAccountColor | 56 |
| GetAccountInformation | 55 |
| DescribeEventAggregates | 51 |
| GetRole | 44 |
| GetCostAndUsage | 23 |
| GetAccountPasswordPolicy | 16 |
| ListRoles | 15 |
| GetCostForecast | 10 |

## Top Principals

| Username | Count |
| --- | --- |
| AWSReservedSSO_DeveloperReadECSRDS_b51741742ac9d794/kkumar | 289 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/jsandoval | 79 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/kkumar | 51 |
| solutions-ccci-config-recorder-role/configLambdaExecution | 37 |
| AWSReservedSSO_Admin_fec679100bb1bbf3/ldorsett | 22 |
| AWS Internal | 3 |
| AWSServiceRoleForOrganizations/ASLRP-SLRCreationManager | 3 |
| AWSServiceRoleForAccessAnalyzer/access-analyzer | 1 |

## Top Source IPs

| Source IP | Count |
| --- | --- |
| 18.216.181.62 | 362 |
| 95.173.219.23 | 47 |
| config.amazonaws.com | 37 |
| 95.173.219.24 | 18 |
| 95.173.219.22 | 13 |
| AWS Internal | 3 |
| organizations.amazonaws.com | 3 |
| 95.173.219.18 | 1 |
| access-analyzer.amazonaws.com | 1 |

## By Event Source

| Service | Count |
| --- | --- |
| iam.amazonaws.com | 94 |
| notifications.amazonaws.com | 92 |
| freetier.amazonaws.com | 74 |
| account.amazonaws.com | 57 |
| uxc.amazonaws.com | 56 |
| health.amazonaws.com | 51 |
| ce.amazonaws.com | 33 |
| cost-optimization-hub.amazonaws.com | 10 |
| s3.amazonaws.com | 5 |
| pricelist.amazonaws.com | 4 |
| organizations.amazonaws.com | 3 |
| sts.amazonaws.com | 3 |
| codewhisperer.amazonaws.com | 2 |
| support.amazonaws.com | 1 |

## By Region

| Region | Count |
| --- | --- |
| us-east-1 | 485 |

## Errors by Error Code

| Error Code | Count |
| --- | --- |
| AccessDenied | 395 |
| ResourceNotFoundException | 5 |
| CredentialReportNotPresentException | 2 |

## Activity by Day

| Date (UTC) | Events |
| --- | --- |
| 2026-08-26 | 169 |
| 2026-08-27 | 316 |

## Username × Event Source

| Username | iam.amazonaws.com | notifications.amazonaws.com | freetier.amazonaws.com | account.amazonaws.com | uxc.amazonaws.com | health.amazonaws.com | ce.amazonaws.com | cost-optimization-hub.amazonaws.com | s3.amazonaws.com | pricelist.amazonaws.com | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWSReservedSSO_DeveloperReadECSRDS_b51741742ac9d794/kkumar | 45 | 63 | 52 | 40 | 40 | 27 | 12 | 3 | 1 | 4 | 289 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/jsandoval | 3 | 12 | 12 | 7 | 7 | 15 | 15 | 5 | 2 |  | 79 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/kkumar | 5 | 10 | 7 | 7 | 7 | 6 | 3 | 1 | 2 |  | 51 |
| solutions-ccci-config-recorder-role/configLambdaExecution | 35 |  |  | 2 |  |  |  |  |  |  | 37 |
| AWSReservedSSO_Admin_fec679100bb1bbf3/ldorsett | 2 | 7 | 3 | 1 | 2 | 3 | 3 | 1 |  |  | 22 |
| AWS Internal |  |  |  |  |  |  |  |  |  |  | 3 |
| AWSServiceRoleForOrganizations/ASLRP-SLRCreationManager | 3 |  |  |  |  |  |  |  |  |  | 3 |
| AWSServiceRoleForAccessAnalyzer/access-analyzer | 1 |  |  |  |  |  |  |  |  |  | 1 |

_Showing top 20 rows × top 10 columns by count._

## Username × Event Name

| Username | ListManagedNotificationEvents | GetAccountPlanState | GetAccountColor | GetAccountInformation | DescribeEventAggregates | GetRole | GetCostAndUsage | GetAccountPasswordPolicy | ListRoles | GetCostForecast | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWSReservedSSO_DeveloperReadECSRDS_b51741742ac9d794/kkumar | 63 | 49 | 40 | 40 | 27 | 35 | 9 |  | 10 | 3 | 289 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/jsandoval | 12 | 10 | 7 | 7 | 15 | 3 | 10 |  |  | 5 | 79 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/kkumar | 10 | 7 | 7 | 7 | 6 | 5 | 2 |  |  | 1 | 51 |
| solutions-ccci-config-recorder-role/configLambdaExecution |  |  |  |  |  |  |  | 16 | 1 |  | 37 |
| AWSReservedSSO_Admin_fec679100bb1bbf3/ldorsett | 7 | 3 | 2 | 1 | 3 | 1 | 2 |  |  | 1 | 22 |
| AWS Internal |  |  |  |  |  |  |  |  |  |  | 3 |
| AWSServiceRoleForOrganizations/ASLRP-SLRCreationManager |  |  |  |  |  |  |  |  | 3 |  | 3 |
| AWSServiceRoleForAccessAnalyzer/access-analyzer |  |  |  |  |  |  |  |  | 1 |  | 1 |

_Showing top 20 rows × top 10 columns by count._