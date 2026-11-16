"""Export marts from ClickHouse to Parquet for the static site (read by DuckDB-WASM).

Each pipeline publishes its own datasets; manifest.json is merged, not overwritten.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from rideflow_ingest.clickhouse import get_client

log = logging.getLogger(__name__)

# dataset -> {file name: query}. Keep exports small: the browser downloads them whole.
DATASETS: dict[str, dict[str, str]] = {
    "weather": {
        "weather_daily.parquet": "SELECT * FROM marts.weather_daily ORDER BY day",
        "weather_hourly.parquet": "SELECT * FROM marts.dim_weather_hour ORDER BY hour_ts",
    },
    "taxi": {
        "demand_hourly.parquet": "SELECT * FROM marts.agg_demand_hourly ORDER BY hour_ts",
        "zones_monthly.parquet": "SELECT * FROM marts.agg_zone_monthly ORDER BY month, pickups DESC",
        "dq_rejections.parquet": "SELECT * FROM marts.dq_trip_rejections ORDER BY source_month, rows DESC",
    },
}

# headline numbers that would be too heavy to compute in the browser
STATS: dict[str, dict[str, str]] = {
    "taxi": {
        "trips_valid": "SELECT count() FROM marts.fct_trips",
        # only months fct_trips has processed (see assert_trips_reconcile), so the rejection rate is consistent
        "trips_raw": "SELECT count() FROM raw.yellow_trips "
        "WHERE _loaded_at <= (SELECT max(_loaded_at) FROM marts.fct_trips)",
        "months": "SELECT uniqExact(_source_month) FROM marts.fct_trips",
        "revenue_usd": "SELECT round(sum(total_amount)) FROM marts.fct_trips",
        "period_from": "SELECT toString(min(pickup_date)) FROM marts.fct_trips",
        "period_to": "SELECT toString(max(pickup_date)) FROM marts.fct_trips",
    },
}


def publish(dataset: str, out_dir: str | None = None) -> dict:
    out = Path(out_dir or os.environ.get("SITE_DATA_DIR", "site/public/data"))
    out.mkdir(parents=True, exist_ok=True)
    client = get_client()

    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.setdefault("files", {})
    manifest.setdefault("stats", {})

    for name, query in DATASETS[dataset].items():
        tmp = out / f".{name}.tmp"
        tmp.write_bytes(client.raw_query(query, fmt="Parquet"))
        tmp.replace(out / name)  # atomic: the site never sees a half-written file
        rows = client.query(f"SELECT count() FROM ({query})").result_rows[0][0]
        manifest["files"][name] = {"rows": rows, "bytes": (out / name).stat().st_size}
        log.info("published %s (%s rows)", name, rows)

    for key, query in STATS.get(dataset, {}).items():
        value = client.query(query).result_rows[0][0]
        manifest["stats"][key] = int(value) if isinstance(value, int | float) else value

    manifest["generated_at"] = datetime.now(UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest
