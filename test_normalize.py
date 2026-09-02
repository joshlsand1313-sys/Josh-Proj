import datetime
import json

from cloudtrail_report.normalize import normalize

fake = {
    "EventId": "abc-123",
    "EventTime": datetime.datetime(2024, 1, 15, 10, 0, 0),
    "EventName": "DescribeInstances",
    "EventSource": "ec2.amazonaws.com",
    "ReadOnly": "true",
    "CloudTrailEvent": json.dumps({
        "eventID": "abc-123",
        "userIdentity": {
            "type": "IAMUser",
            "userName": "alice",
            "accountId": "123456789012",
        },
        "awsRegion": "us-east-1",
        "sourceIPAddress": "1.2.3.4",
        "userAgent": "aws-cli",
    }),
}

result = normalize(fake)
print("OK")
print("username:", result["username"])
print("principal_type:", result["principal_type"])
print("read_only:", result["read_only"])
