"""Author the "RideFlow · Операционные метрики" dashboard via the Superset REST API.

Used once to create the dashboard; the exported YAML in superset/dashboards/ is the
source of truth after that (imported automatically by `make up-bi`).
Re-running replaces the dashboard and its charts.

    python3 scripts/superset_bootstrap.py && make superset-export
"""

from __future__ import annotations

import json

from superset_api import BASE, check, find, session

DB_NAME = "RideFlow ClickHouse"
DASHBOARD = "RideFlow · Операционные метрики"


def simple(col: str, agg: str, label: str) -> dict:
    return {"expressionType": "SIMPLE", "column": {"column_name": col}, "aggregate": agg, "label": label}


def sql(expr: str, label: str) -> dict:
    return {"expressionType": "SQL", "sqlExpression": expr, "label": label}


def main() -> None:
    s = session()
    db = find(s, "database", "database_name", DB_NAME)
    assert db, f"database {DB_NAME!r} not found — is the bi profile up?"

    # ---- datasets (physical tables in marts) ----
    ds = {}
    for table in ["agg_demand_hourly", "agg_zone_monthly", "dq_trip_rejections"]:
        existing = find(s, "dataset", "table_name", table)
        if existing:
            ds[table] = existing["id"]
            continue
        ds[table] = check(s.post(f"{BASE}/api/v1/dataset/", json={
            "database": db["id"], "schema": "marts", "table_name": table,
        }))["id"]

    # virtual dataset: ranking is a query concern, so the chart only has to sort 15 rows
    top_zones_sql = (
        "SELECT zone, borough, sum(revenue) AS revenue, sum(pickups) AS pickups\n"
        "FROM marts.agg_zone_monthly\nGROUP BY zone, borough\nORDER BY revenue DESC\nLIMIT 15"
    )
    existing = find(s, "dataset", "table_name", "top_zones_by_revenue")
    ds["top_zones_by_revenue"] = existing["id"] if existing else check(s.post(f"{BASE}/api/v1/dataset/", json={
        "database": db["id"], "schema": "marts", "table_name": "top_zones_by_revenue", "sql": top_zones_sql,
    }))["id"]

    # ---- drop previous version of the dashboard + its charts ----
    old = find(s, "dashboard", "dashboard_title", DASHBOARD)
    if old:
        charts = check(s.get(f"{BASE}/api/v1/dashboard/{old['id']}/charts"))["result"]
        check(s.delete(f"{BASE}/api/v1/dashboard/{old['id']}"))
        for c in charts:
            check(s.delete(f"{BASE}/api/v1/chart/{c['id']}"))

    dash_id = check(s.post(f"{BASE}/api/v1/dashboard/", json={
        "dashboard_title": DASHBOARD, "slug": "rideflow-ops", "published": True,
    }))["id"]

    trips, revenue = simple("trips", "SUM", "Поездки"), simple("revenue", "SUM", "Выручка, $")
    weather_label = {"expressionType": "SQL", "label": "Погода", "sqlExpression": "if(is_wet, 'Осадки', 'Сухо')"}
    charts = [
        # (name, viz, dataset, params, width, height)
        ("Поездки", "big_number_total", "agg_demand_hourly",
         {"metric": trips, "y_axis_format": "SMART_NUMBER"}, 3, 30),
        ("Выручка", "big_number_total", "agg_demand_hourly",
         {"metric": revenue, "y_axis_format": "$,.3s"}, 2, 30),
        ("Средний чек", "big_number_total", "agg_demand_hourly",
         {"metric": sql("sum(revenue) / sum(trips)", "Средний чек"), "y_axis_format": "$,.2f"}, 2, 30),
        ("Отбраковано DQ", "big_number_total", "dq_trip_rejections",
         {"metric": sql("sumIf(rows, dq_status != 'ok') / sum(rows)", "Доля брака"), "y_axis_format": ".1%"}, 2, 30),
        # period is computed from the data, so the dashboard never claims a stale range
        ("Период данных", "table", "agg_demand_hourly",
         {"query_mode": "aggregate", "groupby": [], "row_limit": 1,
          "metrics": [sql("formatDateTime(min(day), '%d.%m.%Y')", "с"),
                      sql("formatDateTime(max(day), '%d.%m.%Y')", "по"),
                      sql("uniqExact(toStartOfMonth(day))", "месяцев")]}, 3, 30),
        ("Поездки по дням", "echarts_timeseries_line", "agg_demand_hourly",
         {"x_axis": "hour_ts", "time_grain_sqla": "P1D", "metrics": [trips], "groupby": [],
          "row_limit": 10000, "show_legend": False, "rich_tooltip": True, "y_axis_format": "SMART_NUMBER",
          "zoomable": True}, 8, 50),
        ("Причины отбраковки", "table", "dq_trip_rejections",
         {"query_mode": "aggregate", "groupby": ["dq_status"], "metrics": [simple("rows", "SUM", "Строк")],
          "adhoc_filters": [{"expressionType": "SQL", "sqlExpression": "dq_status != 'ok'", "clause": "WHERE"}],
          "order_desc": True, "timeseries_limit_metric": simple("rows", "SUM", "Строк"), "row_limit": 20,
          "show_cell_bars": True}, 4, 50),
        ("Спрос по часу: сухо vs осадки", "echarts_timeseries_bar", "agg_demand_hourly",
         {"x_axis": "hour_of_day", "metrics": [simple("trips", "AVG", "Поездок в час")], "groupby": [weather_label],
          "row_limit": 1000, "show_legend": True, "y_axis_format": "SMART_NUMBER",
          "x_axis_sort_asc": True}, 6, 50),
        ("Нагрузка: день недели (1 = пн) × час", "heatmap_v2", "agg_demand_hourly",
         {"x_axis": "hour_of_day", "groupby": "day_of_week", "metric": simple("trips", "AVG", "Поездок в час"),
          "linear_color_scheme": "oranges", "normalize_across": "heatmap", "show_values": False,
          "sort_x_axis": "alpha_asc", "sort_y_axis": "alpha_asc", "row_limit": 1000, "y_axis_format": "SMART_NUMBER",
          "xscale_interval": 2, "yscale_interval": 1}, 6, 50),
        ("Топ-15 зон по выручке", "echarts_timeseries_bar", "top_zones_by_revenue",
         {"x_axis": "zone", "metrics": [revenue], "groupby": [], "orientation": "horizontal",
          "x_axis_sort": "Выручка, $", "x_axis_sort_asc": True,  # horizontal bars: ascending = biggest on top
          "row_limit": 15, "y_axis_format": "$,.3s", "show_legend": False}, 12, 60),
    ]

    layout, row_ids, row, used = {}, [], [], 0
    def flush():
        nonlocal row, used
        if row:
            rid = f"ROW-{len(row_ids)}"
            layout[rid] = {"type": "ROW", "id": rid, "children": [c for c in row],
                           "parents": ["ROOT_ID", "GRID_ID"], "meta": {"background": "BACKGROUND_TRANSPARENT"}}
            for c in row:
                layout[c]["parents"] = ["ROOT_ID", "GRID_ID", rid]
            row_ids.append(rid)
        row, used = [], 0

    for i, (name, viz, table, params, width, height) in enumerate(charts):
        params = {"viz_type": viz, "datasource": f"{ds[table]}__table", "adhoc_filters": [], **params}
        chart_id = check(s.post(f"{BASE}/api/v1/chart/", json={
            "slice_name": name, "viz_type": viz, "datasource_id": ds[table], "datasource_type": "table",
            "params": json.dumps(params), "dashboards": [dash_id],
        }))["id"]
        if used + width > 12:
            flush()
        # uuid lets an import re-link the layout to charts whose numeric ids changed
        uuid = check(s.get(f"{BASE}/api/v1/chart/", params={
            "q": f"(columns:!(uuid),filters:!((col:id,opr:eq,value:{chart_id})))"}))["result"][0]["uuid"]
        key = f"CHART-{i}"
        layout[key] = {"type": "CHART", "id": key, "children": [],
                       "meta": {"chartId": chart_id, "uuid": uuid, "width": width, "height": height,
                                "sliceName": name}}
        row.append(key)
        used += width
    flush()

    layout.update({
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": row_ids, "parents": ["ROOT_ID"]},
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": DASHBOARD}},
    })
    check(s.put(f"{BASE}/api/v1/dashboard/{dash_id}", json={
        "position_json": json.dumps(layout),
        "json_metadata": json.dumps({"color_scheme": "supersetColors", "refresh_frequency": 0,
                                     "cross_filters_enabled": True}),
    }))
    print(f"dashboard {dash_id}: {BASE}/superset/dashboard/rideflow-ops/")


if __name__ == "__main__":
    main()
