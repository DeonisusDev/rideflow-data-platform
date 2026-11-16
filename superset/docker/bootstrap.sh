#!/usr/bin/env bash
# Idempotent Superset bootstrap: metadata DB, admin, dashboards-as-code import, ClickHouse connection.
set -euo pipefail

superset db upgrade
superset fab create-admin --username admin --firstname RideFlow --lastname Admin \
  --email admin@rideflow.local --password "${SUPERSET_ADMIN_PASSWORD}" || true
superset init

BUNDLE=/app/rideflow/dashboards
if [ -f "$BUNDLE/metadata.yaml" ]; then
  # The repo keeps the export unzipped (reviewable YAML); Superset imports a zip.
  # Exports mask the DB password, and import refuses masked passwords — inject it from env
  # into the in-container zip only (never into the repo).
  python - <<'PY'
import os, pathlib, zipfile
root = pathlib.Path("/app/rideflow/dashboards")
with zipfile.ZipFile("/tmp/rideflow_dashboards.zip", "w") as z:
    for p in root.rglob("*.yaml"):
        text = p.read_text()
        if p.parent.name == "databases":
            text = text.replace(":XXXXXXXXXX@", f":{os.environ['CLICKHOUSE_PASSWORD']}@")
        z.writestr(str(pathlib.Path("rideflow_dashboards") / p.relative_to(root)), text)
PY
  superset import-dashboards -p /tmp/rideflow_dashboards.zip -u admin
fi

# Exports never contain passwords: (re)set the connection URI from env after import.
superset set-database-uri -d "RideFlow ClickHouse" \
  -u "clickhousedb://${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}@clickhouse:8123/default"

exec /app/docker/entrypoints/run-server.sh
