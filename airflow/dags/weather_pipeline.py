"""RideFlow · Weather pipeline

Open-Meteo archive API → ClickHouse raw → dbt (staging → marts, with tests) → Parquet for the site.

Daily run re-ingests a trailing window (archive API lags ~5 days, so late-arriving
data is picked up on later runs; the raw table dedupes). For a backfill, trigger
manually with params start_date / end_date.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from airflow.sdk import Param, dag, task
from dbt_common import dbt_group

TRAILING_DAYS = 10


@dag(
    dag_id="weather_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["rideflow", "batch", "weather"],
    params={
        "start_date": Param(None, type=["null", "string"], format="date", description="Backfill start (YYYY-MM-DD)"),
        "end_date": Param(None, type=["null", "string"], format="date", description="Backfill end (YYYY-MM-DD)"),
    },
    doc_md=__doc__,
)
def weather_pipeline():
    @task
    def extract_load(params: dict, logical_date: datetime | None = None) -> int:
        from rideflow_ingest import weather

        # Manual runs in Airflow 3 have no logical_date → fall back to today
        today = (logical_date or datetime.now(UTC)).date()
        if params.get("start_date"):
            start = date.fromisoformat(params["start_date"])
            end = date.fromisoformat(params["end_date"]) if params.get("end_date") else today
        else:
            end = today
            start = end - timedelta(days=TRAILING_DAYS)
        return weather.ingest(start, end)

    transform = dbt_group("dbt", ["tag:weather"])

    @task
    def publish_site_data() -> dict:
        from rideflow_ingest import publish

        return publish.publish("weather")

    extract_load() >> transform >> publish_site_data()


weather_pipeline()
