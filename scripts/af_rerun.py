"""Clear (re-run) an Airflow DAG run via the REST API on the latest DAG version."""

import json
import sys
import urllib.parse
import urllib.request

API = "http://localhost:8080"
dag, run = sys.argv[1], sys.argv[2]
token = json.load(urllib.request.urlopen(f"{API}/auth/token"))["access_token"]
req = urllib.request.Request(
    f"{API}/api/v2/dags/{dag}/dagRuns/{urllib.parse.quote(run, safe='')}/clear",
    data=json.dumps({"dry_run": False, "run_on_latest_version": True}).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    print(f"{run}: HTTP {resp.status}")
