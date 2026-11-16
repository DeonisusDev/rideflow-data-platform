"""Open-Meteo → ClickHouse raw.weather_hourly.

Pulls hourly weather for NYC from the free Open-Meteo archive API (no key needed).
Timestamps are requested in UTC to avoid DST-ambiguous local hours; ClickHouse
renders them in America/New_York via the column type.
Re-running for the same range is safe: raw table is a ReplacingMergeTree.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime

import requests

from rideflow_ingest.clickhouse import get_client

log = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = {
    # api name        -> raw column
    "temperature_2m": "temperature_c",
    "precipitation": "precipitation_mm",
    "rain": "rain_mm",
    "snowfall": "snowfall_cm",
    "wind_speed_10m": "wind_speed_kmh",
    "weather_code": "weather_code",
}
COLUMNS = ["location", "latitude", "longitude", "ts", *HOURLY_VARS.values(), "_source", "_ingested_at"]


@dataclass(frozen=True)
class Location:
    name: str
    lat: float
    lon: float


NYC = Location("nyc", 40.7128, -74.0060)


def fetch(loc: Location, start: date, end: date, session: requests.Session | None = None) -> list[list]:
    """Return rows ready for insert into raw.weather_hourly."""
    params = {
        "latitude": loc.lat,
        "longitude": loc.lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "GMT",
    }
    resp = (session or requests).get(ARCHIVE_URL, params=params, timeout=60)
    resp.raise_for_status()
    hourly = resp.json()["hourly"]

    ingested_at = datetime.now(UTC)
    rows = []
    for i, t in enumerate(hourly["time"]):
        ts = datetime.fromisoformat(t).replace(tzinfo=UTC)
        values = [hourly[api][i] for api in HOURLY_VARS]
        rows.append([loc.name, loc.lat, loc.lon, ts, *values, "open-meteo-archive", ingested_at])
    return rows


def load(rows: list[list]) -> int:
    if not rows:
        return 0
    get_client().insert("raw.weather_hourly", rows, column_names=COLUMNS)
    return len(rows)


def ingest(start: date, end: date, loc: Location = NYC) -> int:
    rows = fetch(loc, start, end)
    n = load(rows)
    log.info("weather: loaded %s rows for %s %s..%s", n, loc.name, start, end)
    return n
