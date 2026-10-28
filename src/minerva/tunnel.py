import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from shapely.geometry import LineString, mapping
from shapely import transform
from .coords import utm12n_to_lonlat
from .models import Tunnel4D, TunnelSegment4D


def build_tunnel(plan_id, waypoints, horiz_half_width_m=100.0, vert_margin_m=30.0, time_buf_s=15.0):
    if len(waypoints) < 2:
        raise ValueError('Tunnel requires at least two waypoints')
    if not all(math.isfinite(v) for v in (horiz_half_width_m, vert_margin_m, time_buf_s)) or min(horiz_half_width_m, vert_margin_m) <= 0 or time_buf_s < 0:
        raise ValueError('Invalid tunnel margins')
    for wp in waypoints:
        if not all(math.isfinite(v) for v in asdict(wp).values()) or wp.alt_m < 0 or not -90 <= wp.lat_deg <= 90 or not -180 <= wp.lon_deg <= 180:
            raise ValueError('Invalid waypoint')
    segments = []
    for i, (a, b) in enumerate(zip(waypoints, waypoints[1:])):
        if b.epoch_s <= a.epoch_s:
            raise ValueError('Waypoint times must strictly increase')
        segments.append(TunnelSegment4D(i, a.x_m, a.y_m, b.x_m, b.y_m, horiz_half_width_m, vert_margin_m,
                                       max(0.0, min(a.alt_m, b.alt_m) - vert_margin_m),
                                       max(a.alt_m, b.alt_m) + vert_margin_m,
                                       a.epoch_s - time_buf_s, b.epoch_s + time_buf_s))
    return Tunnel4D(plan_id, 2 * horiz_half_width_m, horiz_half_width_m, vert_margin_m, time_buf_s,
                    min(s.low_m for s in segments), max(s.high_m for s in segments),
                    segments[0].start_epoch_s, segments[-1].end_epoch_s, segments)


def _boundary_values(value):
    if isinstance(value, dict):
        return {k: datetime.fromtimestamp(v, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z') if k.endswith('epoch_s') else _boundary_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_boundary_values(v) for v in value]
    return value


def export_tunnel_json(tunnel, out_path):
    Path(out_path).write_text(json.dumps(_boundary_values(asdict(tunnel)), indent=2, allow_nan=False) + '\n')


def export_tunnel_geojson(plan, out_path):
    if plan.tunnel is None or plan.tunnel.plan_id != plan.plan_id:
        raise ValueError('Plan requires its own tunnel for export')
    features = []
    for segment in plan.tunnel.segments:
        corridor = LineString([(segment.start_x_m, segment.start_y_m), (segment.end_x_m, segment.end_y_m)]).buffer(segment.horiz_half_width_m)
        geographic = transform(corridor, utm12n_to_lonlat, interleaved=False)
        properties = dict(plan_id=plan.plan_id, width_m=plan.tunnel.width_m, time_buf_s=plan.tunnel.time_buf_s, **asdict(segment))
        features.append(dict(type='Feature', geometry=mapping(geographic), properties=_boundary_values(properties)))
    Path(out_path).write_text(json.dumps(dict(type='FeatureCollection', features=features), indent=2, allow_nan=False) + '\n')
