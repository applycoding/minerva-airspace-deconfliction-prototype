"""Fixed, non-recursive checks of the implemented first four slices."""
import json
import tempfile
from pathlib import Path
from minerva.coords import lonlat_to_utm12n, utm12n_to_lonlat
from minerva.db import init_db, approve_and_persist_plan, list_active_plans, save_zones, save_weather
from minerva.ingest import load_zones_geojson, load_crewed_plans, parse_weather_text
from minerva.resources import data_dir
from minerva.tunnel import build_tunnel, export_tunnel_json, export_tunnel_geojson


def self_check():
    data = data_dir()
    zones = load_zones_geojson(data / 'zones/suffield.geojson')
    if len(zones) != 3 or len(zones[2].polygon_utm) != 256:
        raise RuntimeError('Zone data check failed')
    plans = load_crewed_plans(data / 'crewed/sample_crewed_plans.json')
    weather = parse_weather_text(data / 'weather/cyxh_metar_calm.txt')
    plan = plans[0]
    plan.tunnel = build_tunnel(plan.plan_id, plan.waypoints)
    x, y = lonlat_to_utm12n(-111.18, 50.27)
    lon, lat = utm12n_to_lonlat(x, y)
    x2, y2 = lonlat_to_utm12n(lon, lat)
    if abs(x-x2) + abs(y-y2) >= .01:
        raise RuntimeError('Projection check failed')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        conn = init_db(path / 'check.sqlite3')
        try:
            save_zones(conn, zones)
            save_weather(conn, weather)
            from minerva.db import get_db_revision
            approve_and_persist_plan(conn, plan, get_db_revision(conn))
            if list_active_plans(conn)[0].tunnel != plan.tunnel:
                raise RuntimeError('Persistence round trip failed')
            export_tunnel_json(plan.tunnel, path / 'tunnel.json')
            export_tunnel_geojson(plan, path / 'tunnel.geojson')
            if len(json.loads((path / 'tunnel.geojson').read_text())['features']) != 1:
                raise RuntimeError('Tunnel export check failed')
        finally:
            conn.close()
    print('Self-check passed: slices 1–4; simulation only, never flown.')
    return 0
