"""Continuous linear-motion checks. Radio results are free-space screening only."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import math
from shapely import STRtree
from shapely.geometry import box, Point, LineString, Polygon
from .models import ConflictRecord
from .ingest import is_zone_active


def extend_waypoints_with_time_buffer(waypoints, t_buf_s):
    if t_buf_s < 0:
        raise ValueError('Negative time buffer')
    legs = list(zip(waypoints, waypoints[1:]))
    if t_buf_s:
        legs.insert(0, (replace(waypoints[0], epoch_s=waypoints[0].epoch_s-t_buf_s), waypoints[0]))
        legs.append((waypoints[-1], replace(waypoints[-1], epoch_s=waypoints[-1].epoch_s+t_buf_s)))
    return legs


def _motion(leg, t):
    a, b = leg
    dt = b.epoch_s-a.epoch_s
    if dt <= 0:
        raise ValueError('Leg duration must be positive')
    p = (a.x_m, a.y_m, a.alt_m)
    v = tuple((end-start)/dt for start, end in zip(p, (b.x_m,b.y_m,b.alt_m)))
    return tuple(x+speed*(t-a.epoch_s) for x,speed in zip(p,v)), v


def _linear_interval(p, v, limit, duration):
    if abs(v) <= 1e-12:
        return (0., duration) if abs(p) < limit else None
    roots = sorted(((-limit-p)/v, (limit-p)/v))
    lo, hi = max(0.,roots[0]), min(duration,roots[1])
    return (lo,hi) if lo < hi else None


def check_leg_pair_exact(leg_a, leg_b, h_sep_m, v_sep_m, tol=1e-9):
    start = max(leg_a[0].epoch_s,leg_b[0].epoch_s)
    end = min(leg_a[1].epoch_s,leg_b[1].epoch_s)
    miss = (False, start, end, math.inf, math.inf)
    if start > end:
        return miss
    pa,va = _motion(leg_a,start); pb,vb = _motion(leg_b,start)
    p = tuple(a-b for a,b in zip(pa,pb)); v = tuple(a-b for a,b in zip(va,vb))
    h,vlim = h_sep_m-tol,v_sep_m-tol
    duration = end-start
    if duration == 0:
        horizontal = math.hypot(*p[:2]); vertical = abs(p[2])
        return (horizontal < h and vertical < vlim,start,end,horizontal,vertical)
    iv = _linear_interval(p[2],v[2],vlim,duration)
    if iv is None:
        return miss
    a = v[0]**2+v[1]**2
    if a <= 1e-18:
        if math.hypot(*p[:2]) >= h:
            return miss
        ih = (0.,duration)
    else:
        # Closest-approach form avoids cancellation in the discriminant.
        centre = -(p[0]*v[0]+p[1]*v[1])/a
        closest = (p[0]+v[0]*centre)**2+(p[1]+v[1]*centre)**2
        if closest >= h*h:
            return miss
        radius = math.sqrt((h*h-closest)/a)
        ih = (max(0.,centre-radius),min(duration,centre+radius))
    lo,hi = max(iv[0],ih[0]), min(iv[1],ih[1])
    if lo >= hi:
        return miss
    th = min(hi,max(lo,-(p[0]*v[0]+p[1]*v[1])/a)) if a > 1e-18 else lo
    tv = min(hi,max(lo,-p[2]/v[2])) if abs(v[2]) > 1e-12 else lo
    return True,start+lo,start+hi,math.hypot(p[0]+v[0]*th,p[1]+v[1]*th),abs(p[2]+v[2]*tv)


def _record(kind, a, b, start, end, h=0., v=0., power=None, detail=''):
    return ConflictRecord(f'{kind}:{a}:{b}:{start:.9f}:{end:.9f}:{detail}',kind,a,b,start,end,h,v,power,'HIGH',detail)


def _margins(plan):
    return (plan.tunnel.horiz_half_width_m,plan.tunnel.vert_margin_m,plan.tunnel.time_buf_s) if plan.tunnel else (0.,0.,0.)


def check_radio_conflict(plan_a, plan_b):
    ra,rb = plan_a.radio,plan_b.radio
    start = max(plan_a.waypoints[0].epoch_s,plan_b.waypoints[0].epoch_s)
    end = min(plan_a.waypoints[-1].epoch_s,plan_b.waypoints[-1].epoch_s)
    if start > end or abs(ra.freq_mhz-rb.freq_mhz) >= (ra.bw_mhz+rb.bw_mhz)/2+max(ra.guard_mhz,rb.guard_mhz):
        return []
    records = []
    for tx,rx in ((plan_a,plan_b),(plan_b,plan_a)):
        distance = math.inf
        g = (rx.radio.gcs_x_m,rx.radio.gcs_y_m,2.)
        for leg in zip(tx.waypoints,tx.waypoints[1:]):
            lo,hi = max(start,leg[0].epoch_s),min(end,leg[1].epoch_s)
            if lo > hi:
                continue
            p,v = _motion(leg,lo)
            q = tuple(x-y for x,y in zip(p,g)); speed2 = sum(x*x for x in v)
            dt = min(hi-lo,max(0.,-sum(x*y for x,y in zip(q,v))/speed2)) if speed2 else 0.
            distance = min(distance,math.sqrt(sum((x+y*dt)**2 for x,y in zip(q,v))))
        distance = max(10.,distance)
        power = tx.radio.tx_power_dbm+tx.radio.tx_gain_dbi+rx.radio.rx_gain_dbi-32.44-20*math.log10(distance/1000)-20*math.log10(tx.radio.freq_mhz)
        if power > rx.radio.rx_threshold_dbm+1e-9:
            records.append(_record('RADIO',tx.plan_id,rx.plan_id,start,end,power=power,detail='Aircraft TX to fixed GCS RX; free-space screening'))
    return records


def check_zone_conflicts(plan, zones):
    h,v,buf = _margins(plan)
    if plan.tunnel is None:
        h,v,buf = 100.,30.,15.
    records = []
    for zone in zones:
        polygon = Polygon(zone.polygon_utm)
        for i,leg in enumerate(extend_waypoints_with_time_buffer(plan.waypoints,buf)):
            a,b = leg
            cuts = {a.epoch_s,b.epoch_s}
            if zone.seasonal_rule == 'CYR229':
                for year in range(datetime.fromtimestamp(a.epoch_s,timezone.utc).year,datetime.fromtimestamp(b.epoch_s,timezone.utc).year+1):
                    for month,day,hour,minute in ((4,1,0,0),(12,1,7,1)):
                        t = datetime(year,month,day,hour,minute,tzinfo=timezone.utc).timestamp()
                        if a.epoch_s < t < b.epoch_s:
                            cuts.add(t)
            cuts = sorted(cuts)
            for start,end in zip(cuts,cuts[1:]):
                active,floor,ceiling = is_zone_active(zone,(start+end)/2)
                if not active:
                    continue
                p,velocity = _motion(leg,start)
                iv = _linear_interval(p[2]-(floor+ceiling)/2,velocity[2],(ceiling-floor)/2+v+1e-9,end-start)
                if iv is None:
                    continue
                lo,hi = start+iv[0],start+iv[1]
                p0,_ = _motion(leg,lo); p1,_ = _motion(leg,hi)
                geom = Point(p0[:2]) if p0[:2] == p1[:2] else LineString((p0[:2],p1[:2]))
                if geom.distance(polygon) <= h+1e-9:
                    records.append(_record('NO_FLY_ZONE',plan.plan_id,zone.zone_id,lo,hi,detail=f'Leg {i}; tunnel intersects active zone'))
    return records


@dataclass(frozen=True, init=False, eq=False)
class SpatialIndex:
    """Snapshot of leg envelopes; query indices map to immutable leg metadata."""
    def __init__(self, active_plans, default_t_buf_s=15.):
        entries = tuple((p.plan_id,i,(replace(a),replace(b))) for p in active_plans for i,(a,b) in enumerate(extend_waypoints_with_time_buffer(p.waypoints,max(default_t_buf_s,_margins(p)[2]))))
        object.__setattr__(self,'entries',entries)
        object.__setattr__(self,'tree',STRtree([box(min(a.x_m,b.x_m),min(a.y_m,b.y_m),max(a.x_m,b.x_m),max(a.y_m,b.y_m)) for _,_,(a,b) in entries]))
        object.__setattr__(self,'buffers',tuple((p.plan_id,max(default_t_buf_s,_margins(p)[2])) for p in active_plans))

    def query(self, leg, h_sep_m):
        a,b = leg
        bounds = box(min(a.x_m,b.x_m)-h_sep_m,min(a.y_m,b.y_m)-h_sep_m,max(a.x_m,b.x_m)+h_sep_m,max(a.y_m,b.y_m)+h_sep_m)
        return [self.entries[int(i)] for i in self.tree.query(bounds)]


def check_all_conflicts(candidate, active_plans, zones, weather, default_h_sep_m=100., default_v_sep_m=30., default_t_buf_s=15., index=None):
    records = []
    start,end = candidate.waypoints[0].epoch_s,candidate.waypoints[-1].epoch_s
    if weather is None or weather.valid_start_epoch_s > start or weather.valid_end_epoch_s < end:
        records.append(_record('WEATHER_WIND',candidate.plan_id,'WEATHER',start,end,detail='REJECTED_WEATHER: missing or stale observation'))
    elif max(weather.wind_speed_mps,weather.gust_mps) > candidate.limits.max_wind_mps:
        records.append(_record('WEATHER_WIND',candidate.plan_id,'WEATHER',start,end,detail='Wind or gust exceeds airframe limit'))
    records.extend(check_zone_conflicts(candidate,zones))
    ca = _margins(candidate)
    for other in active_plans:
        if other.plan_id == candidate.plan_id:
            continue
        records.extend(check_radio_conflict(candidate,other))
        cb = _margins(other)
        h,v = max(default_h_sep_m,ca[0]+cb[0]),max(default_v_sep_m,ca[1]+cb[1])
        buf = max(default_t_buf_s,ca[2],cb[2])
        # Larger pair-specific holds require a fresh exhaustive leg view.
        indexed = index is not None and (other.plan_id,buf) in index.buffers
        other_legs = extend_waypoints_with_time_buffer(other.waypoints,buf)
        for i,leg in enumerate(extend_waypoints_with_time_buffer(candidate.waypoints,buf)):
            targets = sorted((j,l) for pid,j,l in index.query(leg,h) if pid == other.plan_id) if indexed else enumerate(other_legs)
            for j,target in targets:
                hit,lo,hi,mh,mv = check_leg_pair_exact(leg,target,h,v)
                if hit:
                    records.append(_record('SPACE_TIME',candidate.plan_id,other.plan_id,lo,hi,mh,mv,detail=f'Legs {i}/{j}'))
    return sorted(records,key=lambda r:r.conflict_id)
