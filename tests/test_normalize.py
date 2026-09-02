"""Unit tests for cloudtrail_report.normalize."""
from __future__ import annotations

import datetime
import json

import pytest

from cloudtrail_report.normalize import normalize

from conftest import (
    raw_assumed_role,
    raw_assumed_role_no_session_context,
    raw_aws_account,
    raw_aws_service,
    raw_error_event,
    raw_federated_user,
    raw_iam_user,
    raw_minimal,
    raw_root,
    raw_saml_user,
    raw_web_identity_user,
)

_UTC = datetime.timezone.utc


# ---------------------------------------------------------------------------
# Identity type → (principal_type, username)
# ---------------------------------------------------------------------------

def test_iam_user_identity():
    r = normalize(raw_iam_user())
    assert r["principal_type"] == "IAMUser"
    assert r["username"] == "alice"
    assert r["account_id"] == "123456789012"


def test_root_identity():
    r = normalize(raw_root())
    assert r["principal_type"] == "Root"
    assert r["username"] == "root"


def test_assumed_role_full():
    """sessionContext + arn → 'RoleName/SessionName'."""
    r = normalize(raw_assumed_role())
    assert r["principal_type"] == "AssumedRole"
    assert r["username"] == "DeployRole/i-0abc123"


def test_assumed_role_no_session_context():
    """No sessionContext → principalId suffix used as fallback."""
    r = normalize(raw_assumed_role_no_session_context())
    assert r["principal_type"] == "AssumedRole"
    assert r["username"] == "my-session"


def test_federated_user_pid_suffix():
    r = normalize(raw_federated_user())
    assert r["principal_type"] == "FederatedUser"
    assert r["username"] == "bob"


def test_aws_service_invoked_by():
    r = normalize(raw_aws_service())
    assert r["principal_type"] == "AWSService"
    assert r["username"] == "lambda.amazonaws.com"


def test_aws_account_pid_suffix():
    r = normalize(raw_aws_account())
    assert r["principal_type"] == "AWSAccount"
    assert r["username"] == "cross-account-user"


def test_saml_user_username():
    r = normalize(raw_saml_user())
    assert r["principal_type"] == "SAMLUser"
    assert r["username"] == "carol@example.com"


def test_web_identity_user_pid_suffix():
    r = normalize(raw_web_identity_user())
    assert r["principal_type"] == "WebIdentityUser"
    assert r["username"] == "dave"


def test_missing_identity():
    """No CloudTrailEvent blob and no identity → Unknown/unknown."""
    item = {
        "EventId": "ev-x",
        "EventTime": datetime.datetime(2026, 8, 25, 1, 0, 0, tzinfo=_UTC),
        "EventName": "SomeAction",
        "EventSource": "ec2.amazonaws.com",
    }
    r = normalize(item)
    assert r["principal_type"] == "Unknown"
    assert r["username"] == "unknown"


# ---------------------------------------------------------------------------
# Error fields
# ---------------------------------------------------------------------------

def test_error_fields_populated():
    r = normalize(raw_error_event())
    assert r["error_code"] == "BucketNotEmpty"
    assert "not empty" in r["error_message"]


def test_no_error_is_none():
    r = normalize(raw_iam_user())
    assert r["error_code"] is None
    assert r["error_message"] is None


# ---------------------------------------------------------------------------
# read_only coercions
# ---------------------------------------------------------------------------

def test_read_only_string_true():
    item = raw_iam_user()
    item["ReadOnly"] = "true"
    r = normalize(item)
    assert r["read_only"] is True


def test_read_only_string_false():
    item = raw_root()
    item["ReadOnly"] = "false"
    r = normalize(item)
    assert r["read_only"] is False


def test_read_only_native_bool():
    """CloudTrailEvent blob carries a native bool."""
    item = raw_assumed_role()
    r = normalize(item)
    assert r["read_only"] is True


# ---------------------------------------------------------------------------
# event_time coercions
# ---------------------------------------------------------------------------

def test_event_time_uses_boto_datetime():
    dt = datetime.datetime(2026, 8, 20, 8, 0, 0, tzinfo=_UTC)
    item = raw_iam_user()
    item["EventTime"] = dt
    r = normalize(item)
    assert r["event_time"] == dt


def test_event_time_iso_fallback():
    """No EventTime at top level → ISO string in CloudTrailEvent blob parsed."""
    item = {
        "EventId": "ev-iso",
        "EventName": "PutObject",
        "EventSource": "s3.amazonaws.com",
        "CloudTrailEvent": json.dumps({
            "eventTime": "2026-07-01T06:30:00Z",
            "userIdentity": {"type": "IAMUser", "userName": "iso-user", "accountId": "0"},
        }),
    }
    r = normalize(item)
    assert r["event_time"].year == 2026
    assert r["event_time"].month == 7
    assert r["event_time"].tzinfo is not None


def test_event_time_absent_returns_min():
    item = {"EventId": "ev-bare", "EventName": "X", "EventSource": "ec2.amazonaws.com"}
    r = normalize(item)
    assert r["event_time"] == datetime.datetime.min.replace(tzinfo=_UTC)


# ---------------------------------------------------------------------------
# resources extraction
# ---------------------------------------------------------------------------

def test_resources_extracted():
    r = normalize(raw_assumed_role())
    assert len(r["resources"]) == 1
    assert r["resources"][0]["arn"] == "arn:aws:s3:::my-bucket/key"
    assert r["resources"][0]["type"] == "AWS::S3::Object"


def test_resources_empty_by_default():
    r = normalize(raw_iam_user())
    assert r["resources"] == []


# ---------------------------------------------------------------------------
# access_key_id
# ---------------------------------------------------------------------------

def test_access_key_from_uid():
    r = normalize(raw_iam_user())
    assert r["access_key_id"] == "AKIA1EXAMPLE"


def test_access_key_fallback_to_top_level():
    item = {
        "EventId": "ev-ak",
        "EventTime": datetime.datetime(2026, 8, 25, 0, 0, 0, tzinfo=_UTC),
        "EventName": "SomeAction",
        "EventSource": "sts.amazonaws.com",
        "AccessKeyId": "AKIA_TOPLEVEL",
        "CloudTrailEvent": json.dumps({
            "eventName": "SomeAction",
            "eventSource": "sts.amazonaws.com",
            "userIdentity": {"type": "IAMUser", "userName": "u", "accountId": "0"},
        }),
    }
    r = normalize(item)
    assert r["access_key_id"] == "AKIA_TOPLEVEL"


# ---------------------------------------------------------------------------
# Minimal item (top-level fields, no CloudTrailEvent)
# ---------------------------------------------------------------------------

def test_minimal_item_fallbacks():
    r = normalize(raw_minimal(), region="eu-west-1")
    assert r["event_name"] == "DescribeSecurityGroups"
    assert r["event_source"] == "ec2.amazonaws.com"
    assert r["aws_region"] == "eu-west-1"
    assert r["read_only"] is True
