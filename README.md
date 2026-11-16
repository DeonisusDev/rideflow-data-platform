# RideFlow — Data Engineering Portfolio

Одна data-платформа вымышленного сервиса такси/доставки в NYC, закрывающая 15 классических DE-проектов,
+ статический сайт-визитка с живыми данными (DuckDB-WASM в браузере): **https://deonisusdev.github.io/rideflow-data-platform/**

**Стек:** Airflow 3 · ClickHouse · dbt · SeaweedFS (S3) · Superset · Astro + DuckDB-WASM · Docker Compose · GitHub Actions. В планах: Kafka, Debezium, Feast.

| Блок | Статус |
|---|---|
| 01 Batch Lakehouse (Weather ✅, NYC Taxi ✅, Superset ✅) | готово |
| 02 CDC · Customer 360 · Reverse ETL | план |
| 03 Streaming (Clickstream, IoT) | план |
| 04 Observability (DQ, Lineage, Cost) | план |
| 05 ML Feature Platform | план |

## Быстрый старт
```bash
make env          # .env из шаблона
make up-batch     # ClickHouse + Postgres + Airflow → http://localhost:8080
make backfill-weather from=2024-01-01 to=2026-11-15
make up-bi        # ClickHouse + Superset → http://localhost:8088 (admin / admin, дашборд импортируется из YAML)
make site-install site-dev   # → http://localhost:4321
make help
```
Профили compose позволяют уложиться в 8 GB RAM: одновременно поднимается только один «тяжёлый» профиль.

## Поток данных (блок 01)
- `taxi_pipeline` (@monthly, catchup): TLC CDN → S3 lake (SeaweedFS) → ClickHouse `raw.yellow_trips` через `s3()`
  (партиция = месяц) → dbt: `stg_yellow_trips` (DQ-разметка) → `fct_trips` (incremental insert_overwrite)
  → `agg_demand_hourly`, `agg_zone_monthly`, `dq_trip_rejections` → Parquet.
- `weather_pipeline` (@daily): Open-Meteo → ClickHouse `raw.weather_hourly` (ReplacingMergeTree) → `dim_weather_hour`.
- Тесты — гейт через Cosmos (каждая модель = задача + её тесты), включая сверку raw ↔ fct.
- Перезапуск прогона на последней версии DAG: `make rerun dag=taxi_pipeline run=scheduled__2024-01-01T00:00:00+00:00`.

## BI: Superset как код
- Дашборд `RideFlow · Операционные метрики` лежит в `superset/dashboards/` (YAML, экспорт Superset в распакованном виде).
- `make up-bi` при старте упаковывает YAML, подставляет пароль ClickHouse из `.env` (в экспорте он замаскирован) и импортирует.
- Изменили дашборд в UI → `make superset-export` → коммит. Исходный дашборд собран через API: `scripts/superset_bootstrap.py`.

Сервисы: Superset http://localhost:8088 · Airflow http://localhost:8080 · ClickHouse http://localhost:8123 · S3 http://localhost:8333

## Лицензия
Код — [MIT](LICENSE). Данные: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), погода — [Open-Meteo](https://open-meteo.com/) (CC BY 4.0).
