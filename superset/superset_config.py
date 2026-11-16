"""Superset config for the local RideFlow stack (single node, no Redis/Celery)."""

import os

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
# Metadata in SQLite on a volume: BI state is rebuilt from YAML in the repo anyway.
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db?check_same_thread=false"

FEATURE_FLAGS = {
    "DASHBOARD_RBAC": False,
    "ENABLE_TEMPLATE_PROCESSING": True,
}
# Local only: allow embedding screenshots/iframes from localhost tooling
TALISMAN_ENABLED = False
WTF_CSRF_ENABLED = True
ROW_LIMIT = 50_000
SQLLAB_TIMEOUT = 60
SUPERSET_WEBSERVER_TIMEOUT = 60
