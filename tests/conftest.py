"""Shared fixtures and raw-event builders for the test suite."""
from __future__ import annotations

import datetime
import json
import pathlib

import pytest

_UTC = datetime.timezone.utc

# ---------------------------------------------------------------------------
# Location of golden output files
# ---------------------------------------------------------------------------

GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"

# ---------------------------------------------------------------------------
# Fixed datetime anchor — keeps golden files stable across runs
# ---------------------------------------------------------------------------

FIXED_NOW = datetime.datetime(2026, 8, 25, 12, 0, 0, tzinfo=_UTC)

FIXED_META = {
    "range_start":  datetime.date(2026, 8, 1),
    "range_end":    datetime.date(2026, 8, 25),
    "generated_at": FIXED_NOW,
    "filters":      {},
}

# ---------------------------------------------------------------------------
# Raw LookupEvents item builders (one per userIdentity type)
# Each returns a dict shaped like a real boto3 LookupEvents response item.
# ---------------------------------------------------------------------------

def _blob(**ct_fields) -> str:
    """Build a JSON-encoded CloudTrailEvent blob."""
    return json.dumps(ct_fields)


def raw_iam_user() -> dict:
    return {
        "EventId": "ev-iam-001",
        "EventTime": datetime.datetime(2026, 8, 25, 10, 0, 0, tzinfo=_UTC),
        "EventName": "DescribeInstances",
        "EventSource": "ec2.amazonaws.com",
        "ReadOnly": "true",
        "AccessKeyId": "AKIA1EXAMPLE",
        "CloudTrailEvent": _blob(
            eventID="ev-iam-001",
            eventName="DescribeInstances",
            eventSource="ec2.amazonaws.com",
            awsRegion="us-east-1",
            sourceIPAddress="1.2.3.4",
            userAgent="aws-cli/2.0",
            requestID="req-iam-001",
            readOnly=True,
            userIdentity={
                "type": "IAMUser",
                "userName": "alice",
                "accountId": "123456789012",
                "accessKeyId": "AKIA1EXAMPLE",
            },
        ),
    }


def raw_root() -> dict:
    return {
        "EventId": "ev-root-001",
        "EventTime": datetime.datetime(2026, 8, 25, 10, 1, 0, tzinfo=_UTC),
        "EventName": "CreateUser",
        "EventSource": "iam.amazonaws.com",
        "ReadOnly": "false",
        "CloudTrailEvent": _blob(
            eventID="ev-root-001",
            eventName="CreateUser",
            eventSource="iam.amazonaws.com",
            awsRegion="us-east-1",
            sourceIPAddress="5.6.7.8",
            userAgent="console.aws.amazon.com",
            requestID="req-root-001",
            readOnly=False,
            errorCode="AccessDenied",
            errorMessage="User is not authorized",
            userIdentity={
                "type": "Root",
                "accountId": "123456789012",
            },
        ),
    }


def raw_assumed_role() -> dict:
    return {
        "EventId": "ev-role-001",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 0, 0, tzinfo=_UTC),
        "EventName": "GetObject",
        "EventSource": "s3.amazonaws.com",
        "ReadOnly": "true",
        "AccessKeyId": "ASIA1EXAMPLE",
        "CloudTrailEvent": _blob(
            eventID="ev-role-001",
            eventName="GetObject",
            eventSource="s3.amazonaws.com",
            awsRegion="us-east-2",
            sourceIPAddress="1.2.3.4",
            userAgent="aws-sdk-java/1.0",
            requestID="req-role-001",
            readOnly=True,
            resources=[{"ResourceName": "arn:aws:s3:::my-bucket/key", "ResourceType": "AWS::S3::Object"}],
            userIdentity={
                "type": "AssumedRole",
                "arn": "arn:aws:sts::123456789012:assumed-role/DeployRole/i-0abc123",
                "accountId": "123456789012",
                "accessKeyId": "ASIA1EXAMPLE",
                "sessionContext": {
                    "sessionIssuer": {
                        "type": "Role",
                        "userName": "DeployRole",
                        "arn": "arn:aws:iam::123456789012:role/DeployRole",
                    }
                },
            },
        ),
    }


def raw_assumed_role_no_session_context() -> dict:
    """AssumedRole with no sessionContext — falls back to principalId suffix."""
    return {
        "EventId": "ev-role-002",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 2, 0, tzinfo=_UTC),
        "EventName": "ListBuckets",
        "EventSource": "s3.amazonaws.com",
        "ReadOnly": "true",
        "CloudTrailEvent": _blob(
            eventID="ev-role-002",
            eventName="ListBuckets",
            eventSource="s3.amazonaws.com",
            awsRegion="us-east-1",
            userIdentity={
                "type": "AssumedRole",
                "principalId": "AROA1EXAMPLE:my-session",
                "accountId": "123456789012",
            },
        ),
    }


def raw_federated_user() -> dict:
    return {
        "EventId": "ev-fed-001",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 3, 0, tzinfo=_UTC),
        "EventName": "GetCallerIdentity",
        "EventSource": "sts.amazonaws.com",
        "ReadOnly": "true",
        "CloudTrailEvent": _blob(
            eventID="ev-fed-001",
            eventName="GetCallerIdentity",
            eventSource="sts.amazonaws.com",
            awsRegion="us-east-1",
            userIdentity={
                "type": "FederatedUser",
                "principalId": "123456789012:bob",
                "accountId": "123456789012",
            },
        ),
    }


def raw_aws_service() -> dict:
    return {
        "EventId": "ev-svc-001",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 4, 0, tzinfo=_UTC),
        "EventName": "AssumeRole",
        "EventSource": "sts.amazonaws.com",
        "ReadOnly": "false",
        "CloudTrailEvent": _blob(
            eventID="ev-svc-001",
            eventName="AssumeRole",
            eventSource="sts.amazonaws.com",
            awsRegion="us-east-1",
            userIdentity={
                "type": "AWSService",
                "invokedBy": "lambda.amazonaws.com",
            },
        ),
    }


def raw_aws_account() -> dict:
    return {
        "EventId": "ev-acct-001",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 5, 0, tzinfo=_UTC),
        "EventName": "CreateRole",
        "EventSource": "iam.amazonaws.com",
        "ReadOnly": "false",
        "CloudTrailEvent": _blob(
            eventID="ev-acct-001",
            eventName="CreateRole",
            eventSource="iam.amazonaws.com",
            awsRegion="us-east-1",
            userIdentity={
                "type": "AWSAccount",
                "principalId": "987654321098:cross-account-user",
                "accountId": "987654321098",
            },
        ),
    }


def raw_saml_user() -> dict:
    return {
        "EventId": "ev-saml-001",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 6, 0, tzinfo=_UTC),
        "EventName": "GetRole",
        "EventSource": "iam.amazonaws.com",
        "ReadOnly": "true",
        "CloudTrailEvent": _blob(
            eventID="ev-saml-001",
            eventName="GetRole",
            eventSource="iam.amazonaws.com",
            awsRegion="us-east-1",
            userIdentity={
                "type": "SAMLUser",
                "userName": "carol@example.com",
                "accountId": "123456789012",
            },
        ),
    }


def raw_web_identity_user() -> dict:
    return {
        "EventId": "ev-web-001",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 7, 0, tzinfo=_UTC),
        "EventName": "GetBucketAcl",
        "EventSource": "s3.amazonaws.com",
        "ReadOnly": "true",
        "CloudTrailEvent": _blob(
            eventID="ev-web-001",
            eventName="GetBucketAcl",
            eventSource="s3.amazonaws.com",
            awsRegion="us-east-1",
            userIdentity={
                "type": "WebIdentityUser",
                "principalId": "accounts.google.com:dave",
                "accountId": "123456789012",
            },
        ),
    }


def raw_error_event() -> dict:
    """IAMUser event that returned an error — error_code + error_message populated."""
    return {
        "EventId": "ev-err-001",
        "EventTime": datetime.datetime(2026, 8, 25, 11, 0, 0, tzinfo=_UTC),
        "EventName": "DeleteBucket",
        "EventSource": "s3.amazonaws.com",
        "ReadOnly": "false",
        "CloudTrailEvent": _blob(
            eventID="ev-err-001",
            eventName="DeleteBucket",
            eventSource="s3.amazonaws.com",
            awsRegion="us-east-1",
            errorCode="BucketNotEmpty",
            errorMessage="The bucket you tried to delete is not empty",
            readOnly=False,
            userIdentity={
                "type": "IAMUser",
                "userName": "alice",
                "accountId": "123456789012",
            },
        ),
    }


def raw_minimal() -> dict:
    """Top-level fields only, no CloudTrailEvent blob — minimal fallback path."""
    return {
        "EventId": "ev-min-001",
        "EventTime": datetime.datetime(2026, 8, 25, 11, 1, 0, tzinfo=_UTC),
        "EventName": "DescribeSecurityGroups",
        "EventSource": "ec2.amazonaws.com",
        "ReadOnly": "true",
    }

# ---------------------------------------------------------------------------
# Normalized record fixture for aggregate / render tests
# (four records covering two days, all identity types represented)
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_records():
    from cloudtrail_report.normalize import normalize
    raws = [
        raw_assumed_role(),   # 2026-08-24 09:00  DeployRole/i-0abc123
        raw_iam_user(),       # 2026-08-25 10:00  alice (already has ListUsers below)
        raw_root(),           # 2026-08-25 10:01  root  + error
    ]
    # Add a second alice event on 2026-08-24 to give alice count=2
    second_alice = {
        "EventId": "ev-iam-002",
        "EventTime": datetime.datetime(2026, 8, 24, 9, 1, 0, tzinfo=_UTC),
        "EventName": "ListUsers",
        "EventSource": "iam.amazonaws.com",
        "ReadOnly": "true",
        "AccessKeyId": "AKIA1EXAMPLE",
        "CloudTrailEvent": _blob(
            eventID="ev-iam-002",
            eventName="ListUsers",
            eventSource="iam.amazonaws.com",
            awsRegion="us-east-1",
            sourceIPAddress="1.2.3.4",
            userAgent="aws-cli/2.0",
            requestID="req-iam-002",
            readOnly=True,
            userIdentity={
                "type": "IAMUser",
                "userName": "alice",
                "accountId": "123456789012",
                "accessKeyId": "AKIA1EXAMPLE",
            },
        ),
    }
    records = [normalize(r, "us-east-1") for r in [raw_assumed_role(), second_alice, raw_iam_user(), raw_root()]]
    records.sort(key=lambda r: r["event_time"])
    return records


@pytest.fixture()
def sample_summary(sample_records):
    from cloudtrail_report import aggregate
    return aggregate.summarize(sample_records)


@pytest.fixture()
def sample_meta():
    return FIXED_META.copy()
