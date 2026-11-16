SHELL := /bin/bash
COMPOSE := docker compose
-include .env
export

.PHONY: help env up-core up-batch down nuke ps logs ch backfill-weather dbt site-install site-dev site-build lint rerun dbt-parse

help: ## Show targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from template (with your UID and a random JWT secret)
	@test -f .env || (cp .env.example .env && sed -i "s/AIRFLOW_UID=.*/AIRFLOW_UID=$$(id -u)/; s/AIRFLOW_JWT_SECRET=.*/AIRFLOW_JWT_SECRET=$$(openssl rand -hex 16)/" .env)

up-core: ## ClickHouse + Postgres + MinIO
	$(COMPOSE) --profile core up -d --wait

up-batch: ## core + Airflow  → http://localhost:8080
	$(COMPOSE) --profile batch up -d --build --wait

down: ## Stop everything (keeps data)
	$(COMPOSE) --profile '*' down

nuke: ## Stop everything and DELETE volumes
	$(COMPOSE) --profile '*' down -v

ps: ## Service status + memory
	$(COMPOSE) --profile '*' ps
	@docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}'

logs: ## Tail logs (s=<service>)
	$(COMPOSE) --profile '*' logs -f $(s)

ch: ## ClickHouse client
	$(COMPOSE) exec clickhouse clickhouse-client --user $(CLICKHOUSE_USER) --password $(CLICKHOUSE_PASSWORD)

backfill-weather: ## Backfill weather: make backfill-weather from=2024-01-01 to=2024-03-31
	$(COMPOSE) exec airflow-scheduler airflow dags trigger weather_pipeline \
		-c '{"start_date":"$(from)","end_date":"$(to)"}'

dbt: ## Run dbt inside Airflow image: make dbt cmd="build"
	$(COMPOSE) exec -w /opt/rideflow/dbt/rideflow airflow-scheduler /opt/airflow/dbt_venv/bin/dbt $(cmd)

dbt-parse: ## Rebuild dbt manifest after changing models (DAGs render from it)
	$(MAKE) dbt cmd="parse --quiet"

site-install: ## Install site deps
	cd site && npm ci

site-dev: ## Site dev server → http://localhost:4321
	cd site && npm run dev

site-build: ## Static build into site/dist
	cd site && npm run build

lint: ## Python lint
	uvx ruff check ingestion airflow/dags

rerun: ## Re-run a DAG run on the latest DAG version: make rerun dag=taxi_pipeline run=scheduled__2024-01-01T00:00:00+00:00
	@python3 scripts/af_rerun.py "$(dag)" "$(run)"
