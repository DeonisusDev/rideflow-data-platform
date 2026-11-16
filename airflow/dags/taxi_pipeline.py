"""RideFlow · NYC Taxi pipeline (one run = one month)

TLC CDN → S3 landing zone (SeaweedFS) → ClickHouse raw (partition per month, loaded via s3())
→ dbt: staging with DQ labels → fct_trips (incremental, insert_overwrite) → aggregates + tests
→ Parquet for the site.

Every step is idempotent, so `airflow dags backfill` or clearing a run is always safe.
Months to load: start_date … TAXI_END_DATE (kept small to fit a laptop).
"""

from __future__ import annotations

import os
from datetime import datetime

from airflow.sdk import dag, task
from airflow.timetables.interval import CronDataIntervalTimetable
from dbt_common import dbt_group

END = datetime.fromisoformat(os.environ.get("TAXI_END_DATE", "2024-03-31"))


@dag(
    dag_id="taxi_pipeline",
    schedule=CronDataIntervalTimetable("@monthly", timezone="UTC"),
    start_date=datetime(2024, 1, 1),
    end_date=END,
    catchup=True,
    max_active_runs=1,  # one month at a time keeps ClickHouse within its memory limit
    tags=["rideflow", "batch", "taxi"],
    doc_md=__doc__,
)
def taxi_pipeline():
    @task
    def land_to_lake(data_interval_start: datetime | None = None) -> str:
        from rideflow_ingest import tlc

        return tlc.land(data_interval_start.date())

    @task
    def load_raw(_key: str, data_interval_start: datetime | None = None) -> int:
        from rideflow_ingest import tlc

        return tlc.load(data_interval_start.date())

    @task
    def publish_site_data() -> dict:
        from rideflow_ingest import publish

        return publish.publish("taxi")

    load_raw(land_to_lake()) >> dbt_group("dbt", ["tag:taxi"]) >> publish_site_data()


taxi_pipeline()
