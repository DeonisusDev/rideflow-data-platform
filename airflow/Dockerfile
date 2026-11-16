FROM apache/airflow:3.1.0-python3.12

# Airflow-side deps (installed against Airflow's own constraints)
COPY airflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /tmp/requirements.txt

# dbt lives in its own virtualenv so its pins never fight Airflow's (Cosmos recommended setup)
COPY dbt/requirements.txt /tmp/dbt-requirements.txt
RUN python -m venv /opt/airflow/dbt_venv \
 && /opt/airflow/dbt_venv/bin/pip install --no-cache-dir -r /tmp/dbt-requirements.txt
