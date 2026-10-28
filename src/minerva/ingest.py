import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from .coords import (lonlat_to_utm12n, utm12n_to_lonlat,
                     build_conservative_circle_utm, feet_to_metres, knots_to_mps)
from .models import RestrictedZone, FlightPlan, Waypoint4D, DroneLimits, RadioSpec, WeatherObservation
from .db import validate_plan_invariants, get_active_weather

FL_ERROR = 'Flight levels (FL) are not supported; specify altitude in feet or metres above ground reference'


def parse_utc(value):
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError('Time must be finite')
        return float(value)
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('Time must include UTC offset')
    return dt.timestamp()


def load_zones_geojson(path, overrides_path=None):
    overrides = json.loads(Path(overrides_path).read_text()) if overrides_path else {}
    zones = []
    for feature in json.loads(Path(path).read_text())['features']:
        p, g = feature['properties'], feature['geometry']
        if g['type'] == 'Point':
            utm = build_conservative_circle_utm(*g['coordinates'], p['radius_m'], 256)
            geo = [utm12n_to_lonlat(*xy) for xy in utm]
        elif g['type'] == 'Polygon':
            geo = [tuple(xy) for xy in g['coordinates'][0][:-1]]
            utm = [lonlat_to_utm12n(*xy) for xy in geo]
        else:
            raise ValueError('Only polygon zones and circle centres are supported')
        override = overrides.get(p['zone_id'], {})
        active, ceiling = override.get('active'), override.get('ceiling_m')
        if active is not None and not isinstance(active, bool):
            raise ValueError('Zone active override must be boolean')
        if ceiling is not None and (not math.isfinite(ceiling) or ceiling < p['floor_m']):
            raise ValueError('Invalid zone ceiling override')
        zones.append(RestrictedZone(p['zone_id'], p['name'], geo, utm, p['floor_m'], p['ceiling_m'], p['seasonal_rule'], p['handbook_issue'], p['source_note'], active, ceiling))
    return zones


def is_zone_active(zone, epoch_s):
    ceiling = zone.ceiling_m
    if zone.seasonal_rule == 'CYR229':
        dt = datetime.fromtimestamp(epoch_s, timezone.utc)
        summer = datetime(dt.year, 4, 1, tzinfo=timezone.utc).timestamp()
        winter = datetime(dt.year, 12, 1, 7, 1, tzinfo=timezone.utc).timestamp()
        ceiling = 100000.0 if summer <= epoch_s < winter else 4572.0
    if zone.override_ceiling_m is not None:
        ceiling = zone.override_ceiling_m
    return (True if zone.override_active is None else zone.override_active, zone.floor_m, ceiling)


def _altitude(value, unit=None):
    text = str(value).strip()
    if re.search(r'\bFL?\s*\d', text, re.I) or str(unit).upper() in ('FL', 'F'):
        raise ValueError(FL_ERROR)
    match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*(ft|m)?', text, re.I)
    if not match or (match[2] or unit) not in ('ft', 'm', 'FT', 'M'):
        raise ValueError('Specify altitude in ft or m above ground reference')
    number = float(match[1])
    return float(Decimal(match[1]) * Decimal('0.3048')) if (match[2] or unit).lower() == 'ft' else number


def load_crewed_plans(path):
    """JSON plans or text records: PLAN id callsign; WP lat lon altitude UTC; END."""
    raw = Path(path).read_text()
    if raw.lstrip().startswith(('{', '[')):
        data = json.loads(raw)
        records = data['plans'] if isinstance(data, dict) else data
    else:
        records, current = [], None
        for line in raw.splitlines():
            parts = line.split()
            if not parts or parts[0].startswith('#'):
                continue
            if parts[0] == 'PLAN' and len(parts) == 3:
                current = dict(plan_id=parts[1], callsign=parts[2], waypoints=[])
                records.append(current)
            elif parts[0] == 'WP' and len(parts) in (5, 6) and current is not None:
                current['waypoints'].append(dict(lat_deg=float(parts[1]), lon_deg=float(parts[2]), altitude=' '.join(parts[3:-1]), time_utc=parts[-1]))
            elif parts == ['END']:
                current = None
            else:
                if re.search(r'\bFL?\d', line, re.I):
                    raise ValueError(FL_ERROR)
                raise ValueError('Invalid crewed text record')
    plans = []
    for record in records:
        wps = []
        for w in record['waypoints']:
            altitude = _altitude(w['altitude'], w.get('altitude_unit'))
            x, y = lonlat_to_utm12n(w['lon_deg'], w['lat_deg'])
            wps.append(Waypoint4D(w['lat_deg'], w['lon_deg'], altitude, parse_utc(w['time_utc']), x, y))
        if not wps:
            raise ValueError('Crewed plan requires waypoints')
        limits = DroneLimits(**record.get('limits', dict(max_airspeed_mps=300., max_climb_mps=30., max_descent_mps=30., min_turn_radius_m=0., max_wind_mps=100.)))
        radio = RadioSpec(**record.get('radio', dict(freq_mhz=121.5, bw_mhz=0.025, tx_power_dbm=40., tx_gain_dbi=0., rx_gain_dbi=0., rx_threshold_dbm=-100., gcs_lat_deg=wps[0].lat_deg, gcs_lon_deg=wps[0].lon_deg)))
        radio.gcs_x_m, radio.gcs_y_m = lonlat_to_utm12n(radio.gcs_lon_deg, radio.gcs_lat_deg)
        plan = FlightPlan(record['plan_id'], record['callsign'], record.get('priority', 1), 'CREWED_ACTIVE', parse_utc(record['created_utc']) if 'created_utc' in record else wps[0].epoch_s, limits, radio, wps, None, True)
        validate_plan_invariants(plan)
        plans.append(plan)
    return plans


def parse_weather_text(path):
    """Each line has an explicit ISO UTC start/end followed by a METAR.

    The explicit window supplies year/month and freshness without guessing from
    the METAR day-of-month. Variable direction is rejected for a vector model.
    """
    observations = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        window, metar = line.split(maxsplit=1)
        start, end = map(parse_utc, window.split('/'))
        match = re.search(r'(?:METAR\s+|SPECI\s+)?([A-Z]{4})\s+(\d{6})Z\s+(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?(KT|MPS)\b', metar)
        if not match or end <= start:
            raise ValueError('METAR requires wind and a valid explicit UTC window')
        station, stamp, direction, speed, gust, unit = match.groups()
        dt = datetime.fromtimestamp(start, timezone.utc)
        if stamp != dt.strftime('%d%H%M') or direction == 'VRB' or int(direction) > 360:
            raise ValueError('METAR time must match window start; variable wind direction is unsupported')
        convert = knots_to_mps if unit == 'KT' else float
        sustained = convert(float(speed))
        observations.append(WeatherObservation(station, start, end, float(direction), sustained, convert(float(gust)) if gust else sustained, False, metar))
    return observations


def resolve_weather_for_window(conn_or_list, start_epoch_s, end_epoch_s, synthetic_wind=None):
    if not all(map(math.isfinite, (start_epoch_s, end_epoch_s))) or end_epoch_s < start_epoch_s:
        raise ValueError('Invalid weather window')
    if isinstance(conn_or_list, sqlite3.Connection):
        obs = get_active_weather(conn_or_list, start_epoch_s, end_epoch_s)
    else:
        covering = [o for o in conn_or_list if o.valid_start_epoch_s <= start_epoch_s and o.valid_end_epoch_s >= end_epoch_s]
        obs = max(covering, key=lambda o: o.valid_start_epoch_s) if covering else None
    if obs:
        return obs
    if synthetic_wind is not None:
        if not synthetic_wind.is_synthetic:
            raise ValueError('Operator fallback must be marked synthetic')
        if synthetic_wind.valid_start_epoch_s <= start_epoch_s and synthetic_wind.valid_end_epoch_s >= end_epoch_s:
            return synthetic_wind
    return None
