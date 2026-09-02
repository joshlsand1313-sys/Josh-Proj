# CloudTrail Audit Report

|  |  |
| --- | --- |
| Generated | 2026-08-28 06:20 UTC |
| Range | 2026-08-27 → 2026-08-28 |
| Total events | 802 |
| Errors | 348 |
| Write events | 0 |
| Read-only | 802 |
| Filters applied | _none — showing all events in range_ |

---

## Top Event Names

| Event Name | Count |
| --- | --- |
| LookupEvents | 374 |
| ListManagedNotificationEvents | 80 |
| GetAccountPlanState | 60 |
| GetAccountColor | 47 |
| GetAccountInformation | 46 |
| DescribeEventAggregates | 45 |
| GetRole | 38 |
| GetCostAndUsage | 21 |
| GetAccountPasswordPolicy | 16 |
| ListRoles | 15 |

## Top Principals

| Username | Count |
| --- | --- |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/jsandoval | 453 |
| AWSReservedSSO_DeveloperReadECSRDS_b51741742ac9d794/kkumar | 265 |
| solutions-ccci-config-recorder-role/configLambdaExecution | 37 |
| AWSReservedSSO_Admin_fec679100bb1bbf3/ldorsett | 22 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/kkumar | 18 |
| AWS Internal | 3 |
| AWSServiceRoleForOrganizations/ASLRP-SLRCreationManager | 3 |
| AWSServiceRoleForAccessAnalyzer/access-analyzer | 1 |

## Top Source IPs

| Source IP | Count |
| --- | --- |
| 18.216.181.62 | 679 |
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
| cloudtrail.amazonaws.com | 374 |
| iam.amazonaws.com | 88 |
| notifications.amazonaws.com | 80 |
| freetier.amazonaws.com | 65 |
| account.amazonaws.com | 48 |
| uxc.amazonaws.com | 47 |
| health.amazonaws.com | 45 |
| ce.amazonaws.com | 30 |
| cost-optimization-hub.amazonaws.com | 9 |
| pricelist.amazonaws.com | 4 |
| s3.amazonaws.com | 3 |
| organizations.amazonaws.com | 3 |
| sts.amazonaws.com | 3 |
| codewhisperer.amazonaws.com | 2 |
| support.amazonaws.com | 1 |

## By Region

| Region | Count |
| --- | --- |
| us-east-1 | 802 |

## Errors by Error Code

| Error Code | Count |
| --- | --- |
| AccessDenied | 341 |
| ResourceNotFoundException | 5 |
| CredentialReportNotPresentException | 2 |

## Activity by Day

| Date (UTC) | Events |
| --- | --- |
| 2026-08-26 | 112 |
| 2026-08-27 | 690 |

## Username × Event Source

| Username | cloudtrail.amazonaws.com | iam.amazonaws.com | notifications.amazonaws.com | freetier.amazonaws.com | account.amazonaws.com | uxc.amazonaws.com | health.amazonaws.com | ce.amazonaws.com | cost-optimization-hub.amazonaws.com | pricelist.amazonaws.com | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/jsandoval | 374 | 3 | 12 | 12 | 7 | 7 | 15 | 15 | 5 |  | 453 |
| AWSReservedSSO_DeveloperReadECSRDS_b51741742ac9d794/kkumar |  | 41 | 58 | 48 | 36 | 36 | 24 | 12 | 3 | 4 | 265 |
| solutions-ccci-config-recorder-role/configLambdaExecution |  | 35 |  |  | 2 |  |  |  |  |  | 37 |
| AWSReservedSSO_Admin_fec679100bb1bbf3/ldorsett |  | 2 | 7 | 3 | 1 | 2 | 3 | 3 | 1 |  | 22 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/kkumar |  | 3 | 3 | 2 | 2 | 2 | 3 |  |  |  | 18 |
| AWS Internal |  |  |  |  |  |  |  |  |  |  | 3 |
| AWSServiceRoleForOrganizations/ASLRP-SLRCreationManager |  | 3 |  |  |  |  |  |  |  |  | 3 |
| AWSServiceRoleForAccessAnalyzer/access-analyzer |  | 1 |  |  |  |  |  |  |  |  | 1 |

_Showing top 20 rows × top 10 columns by count._

## Username × Event Name

| Username | LookupEvents | ListManagedNotificationEvents | GetAccountPlanState | GetAccountColor | GetAccountInformation | DescribeEventAggregates | GetRole | GetCostAndUsage | GetAccountPasswordPolicy | ListRoles | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/jsandoval | 374 | 12 | 10 | 7 | 7 | 15 | 3 | 10 |  |  | 453 |
| AWSReservedSSO_DeveloperReadECSRDS_b51741742ac9d794/kkumar |  | 58 | 45 | 36 | 36 | 24 | 31 | 9 |  | 10 | 265 |
| solutions-ccci-config-recorder-role/configLambdaExecution |  |  |  |  |  |  |  |  | 16 | 1 | 37 |
| AWSReservedSSO_Admin_fec679100bb1bbf3/ldorsett |  | 7 | 3 | 2 | 1 | 3 | 1 | 2 |  |  | 22 |
| AWSReservedSSO_DeveloperRead_69df50b99e0d373c/kkumar |  | 3 | 2 | 2 | 2 | 3 | 3 |  |  |  | 18 |
| AWS Internal |  |  |  |  |  |  |  |  |  |  | 3 |
| AWSServiceRoleForOrganizations/ASLRP-SLRCreationManager |  |  |  |  |  |  |  |  |  | 3 | 3 |
| AWSServiceRoleForAccessAnalyzer/access-analyzer |  |  |  |  |  |  |  |  |  | 1 | 1 |

_Showing top 20 rows × top 10 columns by count._