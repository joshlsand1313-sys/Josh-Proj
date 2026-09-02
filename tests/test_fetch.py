"""Fetcher tests using botocore.stub.Stubber (no real AWS calls)."""
from __future__ import annotations

import datetime
import json

import boto3
import botocore.exceptions
import pytest
from botocore.stub import Stubber

from cloudtrail_report.fetch import CredentialError, fetch_events

from conftest import raw_iam_user

_UTC = datetime.timezone.utc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stubbed_client():
    """Real CloudTrail client with fake credentials so Stubber can intercept."""
    return boto3.client(
        "cloudtrail",
        region_name="us-east-1",
        aws_access_key_id="fake-key",
        aws_secret_access_key="fake-secret",
        aws_session_token="fake-token",
    )


def _patch_session(monkeypatch, client):
    """Monkeypatch boto3.Session in the fetch module to return *client*."""
    import unittest.mock
    mock_session = unittest.mock.MagicMock()
    mock_session.client.return_value = client
    monkeypatch.setattr(
        "cloudtrail_report.fetch.boto3.Session",
        lambda **kw: mock_session,
    )


# ---------------------------------------------------------------------------
# Single-page response
# ---------------------------------------------------------------------------

def test_single_page_returns_normalized_records(monkeypatch):
    client = _stubbed_client()
    _patch_session(monkeypatch, client)

    with Stubber(client) as stub:
        stub.add_response(
            "lookup_events",
            {"Events": [raw_iam_user()]},
        )
        result = fetch_events(profile=None, primary_region="us-east-1", days=1)

    assert len(result) == 1
    assert result[0]["username"] == "alice"
    assert result[0]["event_name"] == "DescribeInstances"


# ---------------------------------------------------------------------------
# Pagination via NextToken
# ---------------------------------------------------------------------------

def test_pagination_collects_all_pages(monkeypatch):
    client = _stubbed_client()
    _patch_session(monkeypatch, client)

    ev1 = raw_iam_user()
    ev2 = {
        "EventId": "ev-page2",
        "EventTime": datetime.datetime(2026, 8, 25, 11, 0, 0, tzinfo=_UTC),
        "EventName": "PutObject",
        "EventSource": "s3.amazonaws.com",
        "ReadOnly": "false",
        "CloudTrailEvent": json.dumps({
            "eventID": "ev-page2",
            "eventName": "PutObject",
            "eventSource": "s3.amazonaws.com",
            "awsRegion": "us-east-1",
            "userIdentity": {"type": "IAMUser", "userName": "alice", "accountId": "123"},
        }),
    }

    with Stubber(client) as stub:
        stub.add_response(
            "lookup_events",
            {"Events": [ev1], "NextToken": "page2-token"},
        )
        stub.add_response(
            "lookup_events",
            {"Events": [ev2]},
        )
        result = fetch_events(profile=None, primary_region="us-east-1", days=1)

    assert len(result) == 2
    # Results are sorted by event_time ascending
    assert result[0]["event_name"] == "DescribeInstances"
    assert result[1]["event_name"] == "PutObject"


# ---------------------------------------------------------------------------
# Throttling retry
# ---------------------------------------------------------------------------

def test_throttling_retries_and_succeeds(monkeypatch):
    client = _stubbed_client()
    _patch_session(monkeypatch, client)
    monkeypatch.setattr("cloudtrail_report.fetch.time.sleep", lambda _: None)

    with Stubber(client) as stub:
        stub.add_client_error("lookup_events", service_error_code="ThrottlingException")
        stub.add_response("lookup_events", {"Events": [raw_iam_user()]})
        result = fetch_events(profile=None, primary_region="us-east-1", days=1)

    assert len(result) == 1


# ---------------------------------------------------------------------------
# Auth errors → CredentialError
# ---------------------------------------------------------------------------

def test_access_denied_raises_credential_error(monkeypatch):
    client = _stubbed_client()
    _patch_session(monkeypatch, client)

    with Stubber(client) as stub:
        stub.add_client_error("lookup_events", service_error_code="AccessDeniedException")
        with pytest.raises(CredentialError, match="Permission denied"):
            fetch_events(profile=None, primary_region="us-east-1", days=1)


def test_profile_not_found_raises_credential_error(monkeypatch):
    def bad_session(**kw):
        raise botocore.exceptions.ProfileNotFound(profile="nosuchprofile")

    monkeypatch.setattr("cloudtrail_report.fetch.boto3.Session", bad_session)
    with pytest.raises(CredentialError, match="profile"):
        fetch_events(profile="nosuchprofile", primary_region="us-east-1", days=1)
