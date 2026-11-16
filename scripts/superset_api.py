"""Tiny Superset REST client (login + CSRF) shared by the bootstrap/export scripts."""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests

BASE = os.environ.get("SUPERSET_URL", "http://localhost:8088")


def _env(key: str, default: str) -> str:
    env = Path(__file__).resolve().parent.parent / ".env"
    if key in os.environ:
        return os.environ[key]
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1]
    return default


def session() -> requests.Session:
    s = requests.Session()
    token = s.post(f"{BASE}/api/v1/security/login", json={
        "username": "admin", "password": _env("SUPERSET_ADMIN_PASSWORD", "admin"),
        "provider": "db", "refresh": True,
    }).json()["access_token"]
    s.headers["Authorization"] = f"Bearer {token}"
    csrf = s.get(f"{BASE}/api/v1/security/csrf_token/").json()["result"]
    s.headers.update({"X-CSRFToken": csrf, "Referer": BASE})
    return s


def check(resp: requests.Response) -> dict:
    if not resp.ok:
        raise RuntimeError(f"{resp.request.method} {resp.url} → {resp.status_code}: {resp.text[:500]}")
    return resp.json() if resp.content else {}


def find(s: requests.Session, resource: str, col: str, value: str) -> dict | None:
    q = json.dumps({"filters": [{"col": col, "opr": "eq", "value": value}]})
    res = check(s.get(f"{BASE}/api/v1/{resource}/", params={"q": q}))["result"]
    return res[0] if res else None
