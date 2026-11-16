"""S3 data lake (SeaweedFS locally, any S3 in the cloud)."""

import os
from functools import cache

import boto3
from botocore.exceptions import ClientError

BUCKET = os.environ.get("S3_BUCKET", "lake")


def endpoint() -> str:
    return os.environ.get("S3_ENDPOINT", "http://localhost:8333")


def credentials() -> tuple[str, str]:
    return os.environ["S3_ACCESS_KEY"], os.environ["S3_SECRET_KEY"]


@cache
def client():
    key, secret = credentials()
    s3 = boto3.client("s3", endpoint_url=endpoint(), aws_access_key_id=key, aws_secret_access_key=secret,
                      region_name="us-east-1")
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=BUCKET)
    return s3


def object_size(key: str) -> int | None:
    try:
        return client().head_object(Bucket=BUCKET, Key=key)["ContentLength"]
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def url(key: str) -> str:
    """Path-style URL as seen from inside the compose network (used by ClickHouse s3())."""
    return f"{endpoint()}/{BUCKET}/{key}"
