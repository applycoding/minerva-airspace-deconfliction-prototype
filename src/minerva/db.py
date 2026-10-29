import json
import math
import os
import sqlite3
import time
from dataclasses import asdict, fields
from pathlib import Path
from .models import (FlightPlan, DroneLimits, RadioSpec, Waypoint4D, Tunnel4D,
                     TunnelSegment4D, RestrictedZone, WeatherObservation)
from .coords import lonlat_to_utm12n


class StaleStateError(RuntimeError):
    pass


def resolve_db_path(explicit_path=None):
    if explicit_path is not None:
        return Path(explicit_path)
    if os.environ.get('MINERVA_DB_PATH'):
        return Path(os.environ['MINERVA_DB_PATH'])
    if os.name == 'nt':
        return Path(os.environ['LOCALAPPDATA']) / 'Minerva' / 'minerva.sqlite3'
    return Path.home() / '.local/share/minerva/minerva.sqlite3'


def init_db(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    conn.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
    # Preserve operator overrides without changing the handbook columns.
    conn.execute('CREATE TABLE IF NOT EXISTS zone_overrides (zone_id TEXT PRIMARY KEY REFERENCES restricted_zones(zone_id) ON DELETE CASCADE, active INTEGER, ceiling_m REAL)')
    conn.commit()
    return conn


def _finite(value):
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(v) for v in value)
    return not isinstance(value, (int, float)) or math.isfinite(value)


def validate_plan_invariants(plan):
    if len(plan.waypoints) < 2 or not _finite(asdict(plan)):
        raise ValueError('Plan requires at least two waypoints and finite numeric values')
    if any(b.epoch_s <= a.epoch_s for a, b in zip(plan.waypoints, plan.waypoints[1:])):
        raise ValueError('Waypoint timestamps must be strictly increasing')
    if plan.priority not in (1, 2, 3, 4):
        raise ValueError('Priority must be 1 to 4')
    for wp in plan.waypoints:
        if not -90 <= wp.lat_deg <= 90 or not -180 <= wp.lon_deg <= 180 or wp.alt_m < 0:
            raise ValueError('Invalid waypoint coordinates or altitude')
    limits = plan.limits
    if min(limits.max_airspeed_mps, limits.max_climb_mps, limits.max_descent_mps) <= 0 or min(limits.min_turn_radius_m, limits.max_wind_mps) < 0:
        raise ValueError('Invalid airframe limits')
    radio = plan.radio
    if min(radio.freq_mhz, radio.bw_mhz) <= 0 or radio.guard_mhz < 0 or not -90 <= radio.gcs_lat_deg <= 90 or not -180 <= radio.gcs_lon_deg <= 180:
        raise ValueError('Invalid radio parameters')
    if plan.tunnel:
        t = plan.tunnel
        if t.plan_id != plan.plan_id or min(t.width_m, t.horiz_half_width_m, t.vert_margin_m) <= 0 or t.time_buf_s < 0 or t.high_m < t.low_m or t.end_epoch_s <= t.start_epoch_s:
            raise ValueError('Invalid tunnel')


def get_db_revision(conn):
    return conn.execute('SELECT revision FROM db_state_meta WHERE id=1').fetchone()[0]


def _insert(conn, table, values):
    keys = ','.join(values)
    placeholders = ','.join('?' for _ in values)
    conn.execute(f'INSERT INTO {table} ({keys}) VALUES ({placeholders})', tuple(values.values()))


def approve_and_persist_plan(conn, plan, expected_revision, supersede_plan_id=None):
    validate_plan_invariants(plan)
    try:
        conn.execute('BEGIN IMMEDIATE')
        if get_db_revision(conn) != expected_revision:
            raise StaleStateError('Database revision changed; recheck conflicts before approval')
        if supersede_plan_id is not None:
            row = conn.execute('SELECT is_crewed, status FROM flight_plans WHERE plan_id=?', (supersede_plan_id,)).fetchone()
            if row is None or row['is_crewed'] or row['status'] != 'APPROVED' or supersede_plan_id == plan.plan_id:
                raise ValueError('Only a distinct approved uncrewed plan may be superseded')
            conn.execute("UPDATE flight_plans SET status='SUPERSEDED' WHERE plan_id=?", (supersede_plan_id,))
        header = {k: getattr(plan, k) for k in ('plan_id', 'callsign', 'priority', 'created_epoch_s', 'is_crewed')}
        header['status'] = 'CREWED_ACTIVE' if plan.is_crewed else 'APPROVED'
        header.update(asdict(plan.limits))
        _insert(conn, 'flight_plans', header)
        for i, wp in enumerate(plan.waypoints):
            _insert(conn, 'waypoints_4d', dict(plan_id=plan.plan_id, seq_index=i, **asdict(wp)))
        _insert(conn, 'radio_allocations', dict(plan_id=plan.plan_id, **asdict(plan.radio)))
        if plan.tunnel:
            data = asdict(plan.tunnel)
            segments = data.pop('segments')
            _insert(conn, 'tunnels_4d', data)
            for segment in segments:
                _insert(conn, 'tunnel_segments_4d', dict(plan_id=plan.plan_id, **segment))
        conn.execute('UPDATE db_state_meta SET revision=revision+1 WHERE id=1')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return expected_revision + 1


def _from_row(cls, row):
    return cls(**{f.name: row[f.name] for f in fields(cls)})


def list_active_plans(conn, start_epoch_s=None, end_epoch_s=None):
    plans = []
    for row in conn.execute("SELECT * FROM flight_plans WHERE status IN ('APPROVED','CREWED_ACTIVE') ORDER BY plan_id"):
        pid = row['plan_id']
        wps = [_from_row(Waypoint4D, w) for w in conn.execute('SELECT * FROM waypoints_4d WHERE plan_id=? ORDER BY seq_index', (pid,))]
        trow = conn.execute('SELECT * FROM tunnels_4d WHERE plan_id=?', (pid,)).fetchone()
        tunnel = None
        if trow:
            data = dict(trow)
            data['segments'] = [_from_row(TunnelSegment4D, s) for s in conn.execute('SELECT * FROM tunnel_segments_4d WHERE plan_id=? ORDER BY seg_index', (pid,))]
            tunnel = Tunnel4D(**data)
        start = tunnel.start_epoch_s if tunnel else wps[0].epoch_s
        end = tunnel.end_epoch_s if tunnel else wps[-1].epoch_s
        if start_epoch_s is not None and end < start_epoch_s or end_epoch_s is not None and start > end_epoch_s:
            continue
        plans.append(FlightPlan(pid, row['callsign'], row['priority'], row['status'], row['created_epoch_s'], _from_row(DroneLimits, row), _from_row(RadioSpec, conn.execute('SELECT * FROM radio_allocations WHERE plan_id=?', (pid,)).fetchone()), wps, tunnel, bool(row['is_crewed'])))
    return plans


def save_zones(conn, zones):
    with conn:
        for z in zones:
            conn.execute('INSERT INTO restricted_zones VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(zone_id) DO UPDATE SET name=excluded.name, polygon_wgs84_json=excluded.polygon_wgs84_json, floor_m=excluded.floor_m, ceiling_m=excluded.ceiling_m, seasonal_rule=excluded.seasonal_rule, handbook_issue=excluded.handbook_issue, source_note=excluded.source_note', (z.zone_id, z.name, json.dumps(z.polygon_wgs84), z.floor_m, z.ceiling_m, z.seasonal_rule, z.handbook_issue, z.source_note))
            conn.execute('INSERT OR REPLACE INTO zone_overrides VALUES (?,?,?)', (z.zone_id, z.override_active, z.override_ceiling_m))
        conn.execute('UPDATE db_state_meta SET revision=revision+1 WHERE id=1')


def list_zones(conn):
    result = []
    for row in conn.execute('SELECT * FROM restricted_zones ORDER BY zone_id'):
        points = [tuple(p) for p in json.loads(row['polygon_wgs84_json'])]
        override = conn.execute('SELECT * FROM zone_overrides WHERE zone_id=?', (row['zone_id'],)).fetchone()
        result.append(RestrictedZone(row['zone_id'], row['name'], points, [lonlat_to_utm12n(*p) for p in points], row['floor_m'], row['ceiling_m'], row['seasonal_rule'], row['handbook_issue'], row['source_note'], None if override['active'] is None else bool(override['active']), override['ceiling_m']))
    return result


def save_weather(conn, observations):
    with conn:
        for obs in observations:
            _insert(conn, 'weather_observations', asdict(obs))
        conn.execute('UPDATE db_state_meta SET revision=revision+1 WHERE id=1')


def get_active_weather(conn, start_epoch_s, end_epoch_s):
    row = conn.execute('SELECT * FROM weather_observations WHERE valid_start_epoch_s<=? AND valid_end_epoch_s>=? ORDER BY valid_start_epoch_s DESC, obs_id DESC LIMIT 1', (start_epoch_s, end_epoch_s)).fetchone()
    return _from_row(WeatherObservation, row) if row else None


def log_conflicts(conn, conflicts):
    with conn:
        for conflict in conflicts:
            _insert(conn, 'conflict_logs', dict(detected_epoch_s=time.time(), **asdict(conflict)))
