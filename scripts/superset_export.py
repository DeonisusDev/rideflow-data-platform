"""Export the RideFlow dashboard (with charts, datasets, DB) to superset/dashboards/ as plain YAML.

Superset exports a zip; we unpack it so the dashboard is reviewable/diffable in git.
`make up-bi` zips it back and imports on startup (see superset/docker/bootstrap.sh).
"""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path

from superset_api import BASE, find, session

OUT = Path(__file__).resolve().parent.parent / "superset" / "dashboards"


def main() -> None:
    s = session()
    dash = find(s, "dashboard", "slug", "rideflow-ops")
    assert dash, "dashboard rideflow-ops not found"
    resp = s.get(f"{BASE}/api/v1/dashboard/export/", params={"q": f"!({dash['id']})"})
    resp.raise_for_status()

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        for name in z.namelist():
            rel = Path(*Path(name).parts[1:])  # strip the top-level "dashboard_export_<ts>/" folder
            target = OUT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
    files = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*.yaml"))
    print(f"exported {len(files)} files to {OUT}:\n  " + "\n  ".join(files))


if __name__ == "__main__":
    main()
