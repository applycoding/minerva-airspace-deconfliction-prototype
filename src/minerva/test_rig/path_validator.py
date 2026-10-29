"""Independent flight-limit and sampled reservation validation. Simulation only."""
import math
from shapely.geometry import LineString, Point, Polygon
from ..ingest import is_zone_active
from .oracle import sample_space_time, evaluate_radio, _legs


def validate_path(plan, zones, existing_plans, weather):
    """Return a list of failures without using planner or conflict helpers."""
    errors = []
    wps,limits = plan.waypoints,plan.limits
    if len(wps) < 2:
        return ['Fewer than two waypoints']
    if weather is None:
        return ['Missing weather']
    if weather.valid_start_epoch_s > wps[0].epoch_s or weather.valid_end_epoch_s < wps[-1].epoch_s or max(weather.wind_speed_mps,weather.gust_mps)>limits.max_wind_mps:
        errors.append('Weather limits')
    theta = math.radians(weather.wind_from_deg)
    wind = (-weather.wind_speed_mps*math.sin(theta),-weather.wind_speed_mps*math.cos(theta))
    previous = None
    waits = 0
    for a,b in zip(wps,wps[1:]):
        dt = b.epoch_s-a.epoch_s
        if dt <= 0:
            errors.append('Nonpositive duration'); continue
        dx,dy,dz = b.x_m-a.x_m,b.y_m-a.y_m,b.alt_m-a.alt_m
        length = math.hypot(dx,dy)
        if min(a.alt_m,b.alt_m)<0 or not all(math.isfinite(v) for v in (a.x_m,a.y_m,a.alt_m,a.epoch_s,b.x_m,b.y_m,b.alt_m,b.epoch_s)):
            errors.append('Invalid coordinate')
        if math.hypot(dx/dt-wind[0],dy/dt-wind[1]) > limits.max_airspeed_mps+1e-7:
            errors.append('Airspeed')
        if dz/dt > limits.max_climb_mps+1e-7 or -dz/dt > limits.max_descent_mps+1e-7:
            errors.append('Vertical rate')
        if length < 1e-6:
            waits += 1
            if not limits.hover_allowed or abs(dt-10)>1e-6 or dz != 0 or waits>6:
                errors.append('Invalid hover')
            continue
        if length+1e-6 < limits.min_turn_radius_m:
            errors.append('Fillet length')
        heading = math.atan2(dx,dy)
        if previous is not None and abs(math.remainder(heading-previous,2*math.pi))>math.pi/4+1e-7:
            errors.append('Turn limit')
        previous = heading
        along = (wind[0]*dx+wind[1]*dy)/length
        cross = (wind[0]*dy-wind[1]*dx)/length
        square = (.85*limits.max_airspeed_mps)**2-cross**2
        if square < -1e-7 or along+math.sqrt(max(0,square)) <= 0:
            errors.append('Wind triangle'); continue
        expected = max(length/(along+math.sqrt(max(0,square))),abs(dz)/(limits.max_climb_mps if dz>=0 else limits.max_descent_mps))
        if abs(dt-expected)>1e-6:
            errors.append('Edge timing')
    h,v,buf = (plan.tunnel.horiz_half_width_m,plan.tunnel.vert_margin_m,plan.tunnel.time_buf_s) if plan.tunnel else (100.,30.,15.)
    for zone in zones:
        poly = Polygon(zone.polygon_utm)
        for (ta,pa),(tb,pb) in _legs(wps,buf):
            # Clip the line to the vertical interval independently at each sample slab.
            count = max(1,math.ceil((tb-ta)/.1))
            for i in range(count):
                t0,t1 = ta+(tb-ta)*i/count,ta+(tb-ta)*(i+1)/count
                active,floor,ceiling = is_zone_active(zone,(t0+t1)/2)
                if not active:
                    continue
                left,right = (t0-ta)/(tb-ta),(t1-ta)/(tb-ta)
                dz = pb[2]-pa[2]
                if dz:
                    cuts = sorted(((floor-v-pa[2])/dz,(ceiling+v-pa[2])/dz))
                    left,right = max(left,cuts[0]),min(right,cuts[1])
                elif not floor-v <= pa[2] <= ceiling+v:
                    continue
                if left>right:
                    continue
                p,q = pa+(pb-pa)*left,pa+(pb-pa)*right
                geom = Point(p[:2]) if tuple(p[:2])==tuple(q[:2]) else LineString((p[:2],q[:2]))
                if geom.distance(poly)<=h+1e-9:
                    errors.append('Zone'); break
    for other in existing_plans:
        if other.plan_id == plan.plan_id:
            continue
        oh,ov,ot = (other.tunnel.horiz_half_width_m,other.tunnel.vert_margin_m,other.tunnel.time_buf_s) if other.tunnel else (0.,0.,0.)
        if sample_space_time(wps,other.waypoints,max(100,h+oh),max(30,v+ov),max(15,buf,ot))['hit']:
            errors.append('Space/time')
        if any(r['hit'] for r in evaluate_radio(plan,other)):
            errors.append('Radio')
    return errors
