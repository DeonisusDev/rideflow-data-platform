"""Shared ClickHouse client factory (config from env, same names as docker-compose)."""

import os

import clickhouse_connect
from clickhouse_connect.driver.client import Client


def get_client() -> Client:
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "localhost"),
        port=int(os.environ.get("CLICKHOUSE_HTTP_PORT", "8123")),
        username=os.environ["CLICKHOUSE_USER"],
        password=os.environ["CLICKHOUSE_PASSWORD"],
    )
