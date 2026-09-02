from __future__ import annotations

import datetime
import json

_UTC = datetime.timezone.utc


def normalize(raw_item: dict, region: str = "") -> dict:
    """Normalize one LookupEvents response item into a stable, API-agnostic record.

    Parses the CloudTrailEvent JSON blob and resolves userIdentity to a clean
    (principal_type, username, account_id) triple covering all known identity types.
    No raw API field names escape this function.
    """
    ct = _parse_blob(raw_item.get("CloudTrailEvent"))
    uid = ct.get("userIdentity") or {}
    principal_type, username, account_id = _resolve_identity(uid)

    return {
        "event_id": ct.get("eventID") or raw_item.get("EventId", ""),
        "event_time": _coerce_time(raw_item.get("EventTime"), ct.get("eventTime")),
        "event_name": ct.get("eventName") or raw_item.get("EventName", ""),
        "event_source": ct.get("eventSource") or raw_item.get("EventSource", ""),
        "principal_type": principal_type,
        "username": username,
        "account_id": account_id,
        "aws_region": ct.get("awsRegion") or region,
        "source_ip": ct.get("sourceIPAddress", ""),
        "user_agent": ct.get("userAgent", ""),
        "request_id": ct.get("requestID", ""),
        "read_only": _coerce_bool(ct.get("readOnly", raw_item.get("ReadOnly"))),
        "error_code": ct.get("errorCode") or None,
        "error_message": ct.get("errorMessage") or None,
        "resources": _extract_resources(
            ct.get("resources") or raw_item.get("Resources") or []
        ),
        "access_key_id": uid.get("accessKeyId") or raw_item.get("AccessKeyId", ""),
    }


# ---------------------------------------------------------------------------
# Identity resolution
# ---------------------------------------------------------------------------

def _resolve_identity(uid: dict) -> tuple[str, str, str]:
    """Return (principal_type, username, account_id).

    Handles every CloudTrail identity type. username is always non-empty.

    Types seen in the wild:
      IAMUser, Root, AssumedRole, FederatedUser, AWSService, AWSAccount,
      SAMLUser, WebIdentityUser — plus absent/malformed userIdentity.
    """
    if not uid:
        return "Unknown", "unknown", ""

    p_type = uid.get("type", "Unknown")
    account_id = uid.get("accountId", "")

    match p_type:
        case "IAMUser":
            username = uid.get("userName", "") or _pid_suffix(uid)
        case "Root":
            username = "root"
        case "AssumedRole":
            username = _resolve_assumed_role(uid)
        case "FederatedUser":
            # principalId is typically "account_id:username"
            username = _pid_suffix(uid) or uid.get("federatedUserId", "federated-user")
        case "AWSService":
            username = uid.get("invokedBy", "aws-service")
        case "AWSAccount":
            # Cross-account; principalId may be "account_id:user"
            username = _pid_suffix(uid) or f"account:{account_id}"
        case "SAMLUser":
            username = uid.get("userName") or _pid_suffix(uid) or "saml-user"
        case "WebIdentityUser":
            username = uid.get("userName") or _pid_suffix(uid) or "web-identity-user"
        case _:
            username = uid.get("userName") or _pid_suffix(uid) or "unknown"

    return p_type, username or "unknown", account_id


def _resolve_assumed_role(uid: dict) -> str:
    """Human-readable name for an AssumedRole: '<role-name>/<session-name>'.

    Examples:
      "DeployRole/i-0abc123def"   (EC2 instance profile)
      "Admin/alice"               (developer assuming a role)
      "GitHubActionsRole/repo:owner/repo:ref:refs/heads/main"
    Falls back gracefully when sessionContext is absent or incomplete.
    """
    issuer = ((uid.get("sessionContext") or {}).get("sessionIssuer") or {})
    role_name = issuer.get("userName", "")

    # Session name is the final segment of the assumed-role ARN.
    arn = uid.get("arn", "")
    session_name = arn.rsplit("/", 1)[-1] if "/" in arn else ""

    if role_name and session_name:
        return f"{role_name}/{session_name}"
    if role_name:
        return role_name
    # No sessionContext available — parse principalId "AROA...:session-name"
    return _pid_suffix(uid) or "assumed-role"


def _pid_suffix(uid: dict) -> str:
    """Return the part after ':' in principalId (the human-meaningful segment)."""
    pid = uid.get("principalId", "")
    if not pid:
        return ""
    return pid.split(":", 1)[-1] if ":" in pid else pid


# ---------------------------------------------------------------------------
# Type coercions
# ---------------------------------------------------------------------------

def _coerce_time(
    boto_dt: datetime.datetime | None,
    iso_str: str | None,
) -> datetime.datetime:
    """Prefer the boto3-deserialized datetime; fall back to parsing the ISO string."""
    if isinstance(boto_dt, datetime.datetime):
        return boto_dt if boto_dt.tzinfo else boto_dt.replace(tzinfo=_UTC)
    if iso_str:
        try:
            dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=_UTC)
        except ValueError:
            pass
    return datetime.datetime.min.replace(tzinfo=_UTC)


def _coerce_bool(value: object) -> bool:
    """Handle both native bool (CloudTrailEvent blob) and string (LookupEvents top-level)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def _extract_resources(raw: list) -> list[dict]:
    return [
        {
            "arn": r.get("ResourceName") or r.get("ARN", ""),
            "type": r.get("ResourceType", ""),
        }
        for r in raw
    ]


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_blob(ct_json: str | None) -> dict:
    if not ct_json:
        return {}
    try:
        return json.loads(ct_json)
    except (json.JSONDecodeError, TypeError):
        return {}
