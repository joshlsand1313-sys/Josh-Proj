# CloudTrail Audit Report — Setup & Auth

## Overview

This project queries AWS CloudTrail using the **LookupEvents API** to generate audit reports on management events. The application uses **read-only** IAM permissions and requires no modification of any AWS resources.

---

## Local Development Auth

### Prerequisites

- AWS CLI installed and configured
- Named AWS profile or AWS SSO configured
- Credentials with `cloudtrail:LookupEvents` permission

### Configuration

#### Option A: Named AWS Profile (Recommended)

1. **Configure your profile** in `~/.aws/credentials` and `~/.aws/config`:

   ```ini
   # ~/.aws/credentials
   [default]
   aws_access_key_id = AKIAIOSFODNN7EXAMPLE
   aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   
   # or for IAM user with MFA:
   [my-profile]
   aws_access_key_id = AKIAIOSFODNN7EXAMPLE
   aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   
   # ~/.aws/config
   [profile my-profile]
   region = us-east-1
   mfa_serial = arn:aws:iam::123456789012:mfa/my-user
   ```

2. **Set the profile when running locally**:

   ```bash
   export AWS_PROFILE=my-profile
   # Then run your application
   ```

#### Option B: AWS SSO

1. **Configure SSO in `~/.aws/config`**:

   ```ini
   [profile my-sso]
   sso_start_url = https://my-org.awsapps.com/start
   sso_region = us-east-1
   sso_account_id = 123456789012
   sso_role_name = DeveloperAccess
   region = us-east-1
   ```

2. **Login and use**:

   ```bash
   aws sso login --profile my-sso
   export AWS_PROFILE=my-sso
   # Then run your application
   ```

### Permissions Required Locally

Your user or role must have these permissions (provided by `infra/iam/cloudtrail-readonly-policy.json`):

- `cloudtrail:LookupEvents` — query event history
- `cloudtrail:DescribeTrails` — list available trails (informational)
- `cloudtrail:GetTrailStatus` — check trail status (informational)

**No permissions to modify, delete, or write to CloudTrail are needed.**

---

## Deployed Environment Auth

### Lambda (or EC2/ECS)

When deployed to AWS Lambda, EC2, or ECS, **credentials are managed by an IAM task role**:

1. **Create a task role** with the policy from `infra/iam/cloudtrail-readonly-policy.json`:

   ```bash
   aws iam create-role \
     --role-name cloudtrail-query-task-role \
     --assume-role-policy-document file://trust-policy.json
   
   aws iam put-role-policy \
     --role-name cloudtrail-query-task-role \
     --policy-name CloudTrailReadOnly \
     --policy-document file://infra/iam/cloudtrail-readonly-policy.json
   ```

2. **Trust policy** (`trust-policy.json`) for Lambda:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Service": "lambda.amazonaws.com"
         },
         "Action": "sts:AssumeRole"
       }
     ]
   }
   ```

3. **Attach to Lambda function** (via CloudFormation, Terraform, or AWS console):
   - Set the Lambda **execution role** to `cloudtrail-query-task-role`
   - The Lambda runtime automatically assumes this role; no explicit credential handling needed

### Environment Variables (Not Required)

- **Do not store** `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in deployed environment variables
- **Do not check in** `.aws/credentials` or private keys
- The task role's temporary credentials are injected automatically via `AWS_ROLE_SESSION_TOKEN`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` environment variables (read-only from the role metadata service)

### Key Differences: Local vs Deployed

| Aspect | Local | Deployed |
|--------|-------|----------|
| **Credential source** | `~/.aws/credentials` or SSO login cache | IAM task role assumed via metadata service |
| **Key storage** | Developer's machine (locked down) | No keys stored; temporary credentials only |
| **MFA** | Optional; per developer | Not applicable; role-based access |
| **Rotation** | Manual (SSO auto-refreshes on login) | Automatic (AWS rotates every 1 hour) |
| **Multi-account access** | Possible via cross-account roles; not in PoC scope | Not in PoC scope; single account |

---

## Verify Permissions

### Local

```bash
# Check if your profile can call LookupEvents
aws cloudtrail lookup-events \
  --max-items 1 \
  --profile my-profile

# Expected output: a single event (or empty if no events in 90 days)
# Failure: "User: arn:aws:iam::123456789012:user/my-user is not authorized..." indicates missing permission
```

### Deployed (Lambda)

Test your Lambda function with a minimal handler:

```python
import boto3

cloudtrail = boto3.client('cloudtrail')

def lambda_handler(event, context):
    try:
        response = cloudtrail.lookup_events(MaxResults=1)
        return {
            'statusCode': 200,
            'body': f'Successfully queried CloudTrail: {len(response.get("Events", []))} events'
        }
    except Exception as e:
        return {
            'statusCode': 403,
            'body': f'Permission denied: {str(e)}'
        }
```

Deploy and invoke; if successful, permissions are correctly configured.

---

## Security Notes

1. **Read-only scope**: This policy grants query access only. No modifications to trails, logs, or configuration are possible.
2. **No S3 access**: LookupEvents does not require S3 bucket access; this policy is purely CloudTrail.
3. **Resource-level granularity**: If moving to S3 + Athena in future phases, add S3 and Athena permissions scoped to specific buckets and databases.
4. **Audit trail**: All API calls (including LookupEvents) are logged in CloudTrail; your queries are not hidden.

---

## Troubleshooting

### "UnauthorizedOperation: You do not have authorization to access CloudTrail"

- Verify the user/role attached to your profile has the policy from `infra/iam/cloudtrail-readonly-policy.json`
- Check IAM console: **Users** → **Permissions** → confirm `cloudtrail:LookupEvents` is listed

### "NoCredentialsError" in deployed Lambda

- Confirm the Lambda **execution role** is set to the task role with the CloudTrail policy
- Check Lambda IAM role: **AWS Lambda** → **Functions** → your function → **Configuration** → **Execution role**

### SSO Login Expires

```bash
# Re-authenticate
aws sso login --profile my-sso
```

---

## Next Steps

Once verified locally, move to Phase 3:
- Deploy the Lambda function with the task role
- Integrate the report generation logic
- Test end-to-end in the deployed environment
