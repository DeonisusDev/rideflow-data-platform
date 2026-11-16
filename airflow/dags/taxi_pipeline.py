"""RideFlow · NYC Taxi — ingestion and transformation as two data-aware DAGs.

taxi_ingest (@monthly, catchup, one run = one month)
    wait_for_file  → TLC publishes with a ~2 month lag; reschedule-mode sensor waits instead of failing
    land_to_lake   → TLC CDN → S3 landing zone (SeaweedFS), skipped if already there
    load_raw       → ClickHouse INSERT … SELECT FROM s3(), replaces that month's partition
    ⇒ emits Asset "clickhouse://raw/yellow_trips"

taxi_transform (scheduled on that Asset)
    dbt (Cosmos: one task per model + its tests) → publish Parquet for the site

Decoupling matters for backfills: 30+ months of ingest only trigger a handful of
transform runs (pending asset events are consumed together), instead of rebuilding
every aggregate 30+ times.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow.sdk import Asset, PokeReturnValue, dag, task
from airflow.timetables.interval import CronDataIntervalTimetable
from dbt_common import dbt_group

RAW_TRIPS = Asset("clickhouse://clickhouse:9000/raw/yellow_trips")
START = datetime.fromisoformat(os.environ.get("TAXI_START_DATE", "2024-01-01"))


@dag(
    dag_id="taxi_ingest",
    schedule=CronDataIntervalTimetable("@monthly", timezone="UTC"),
    start_date=START,
    catchup=True,
    max_active_runs=2,  # download+insert is light; transform is the heavy part and runs separately
    tags=["rideflow", "batch", "taxi", "ingest"],
    doc_md=__doc__,
)
def taxi_ingest():
    @task.sensor(poke_interval=timedelta(hours=12), timeout=timedelta(days=90), mode="reschedule")
    def wait_for_file(data_interval_start: datetime | None = None) -> PokeReturnValue:
        from rideflow_ingest import tlc

        return PokeReturnValue(is_done=tlc.is_published(data_interval_start.date()))

    @task
    def land_to_lake(data_interval_start: datetime | None = None) -> str:
        from rideflow_ingest import tlc

        return tlc.land(data_interval_start.date())

    @task(outlets=[RAW_TRIPS])
    def load_raw(_key: str, data_interval_start: datetime | None = None) -> int:
        from rideflow_ingest import tlc

        return tlc.load(data_interval_start.date())

    landed = land_to_lake()
    wait_for_file() >> landed
    load_raw(landed)


@dag(
    dag_id="taxi_transform",
    schedule=[RAW_TRIPS],
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["rideflow", "batch", "taxi", "dbt"],
    doc_md=__doc__,
)
def taxi_transform():
    @task
    def publish_site_data() -> dict:
        from rideflow_ingest import publish

        return publish.publish("taxi")

    dbt_group("dbt", ["tag:taxi"]) >> publish_site_data()


taxi_ingest()
taxi_transform()
