FROM apache/superset:5.0.0

USER root
# ClickHouse SQLAlchemy dialect (clickhousedb://) into Superset's venv
RUN uv pip install --python /app/.venv/bin/python --no-cache "clickhouse-connect>=0.8,<1"
COPY superset/superset_config.py /app/pythonpath/superset_config.py
COPY superset/docker/bootstrap.sh /app/docker/rideflow-bootstrap.sh
USER superset
