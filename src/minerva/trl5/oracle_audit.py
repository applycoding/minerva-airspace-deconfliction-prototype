"""Independent post-scenario reservation audit, including durable reload."""
from dataclasses import asdict
from shapely.geometry import LineString, Point, Polygon
from ..test_rig.path_validator import validate_path
from ..test_rig.oracle import sample_space_time, evaluate_radio
from ..conflict import check_all_conflicts


def audit(driver):
    window = driver.window
    plans = window.active(); approved = [p for p in plans if p.status=='APPROVED']
    errors = {}; samples = 0; max_step = 0.; containment = []; clearances = []
    pair_hits = []; rf_hits = []
    clean_checker_records=[]
    for p in approved:
        # The validator independently checks flight limits, zones, space/time and RF.
        failures = validate_path(p,window.zones,[o for o in plans if o.plan_id!=p.plan_id],window.current_weather(p))
        if failures: errors[p.plan_id] = failures
        clean_checker_records.extend(asdict(c) for c in check_all_conflicts(p,plans,window.zones,window.current_weather(p)))
        t = p.tunnel
        if t is None:
            containment.append(False)
        else:
            containment.append(len(t.segments)==len(p.waypoints)-1)
            for a,b,s in zip(p.waypoints,p.waypoints[1:],t.segments):
                center = LineString(((s.start_x_m,s.start_y_m),(s.end_x_m,s.end_y_m)))
                containment.append(center.buffer(s.horiz_half_width_m).covers(LineString(((a.x_m,a.y_m),(b.x_m,b.y_m))))
                                   and s.low_m<=min(a.alt_m,b.alt_m)<=max(a.alt_m,b.alt_m)<=s.high_m
                                   and s.start_epoch_s<=a.epoch_s<b.epoch_s<=s.end_epoch_s)
        for other in plans:
            if other.plan_id==p.plan_id: continue
            h = max(100.,p.tunnel.horiz_half_width_m+(other.tunnel.horiz_half_width_m if other.tunnel else 0.))
            v = max(30.,p.tunnel.vert_margin_m+(other.tunnel.vert_margin_m if other.tunnel else 0.))
            buf = max(15.,p.tunnel.time_buf_s,other.tunnel.time_buf_s if other.tunnel else 0.)
            result = sample_space_time(p.waypoints,other.waypoints,h,v,buf)
            samples += result['samples']; max_step = max(max_step,result['max_relative_step_m'])
            if result['hit']: pair_hits.append([p.plan_id,other.plan_id])
            rf_hits.extend(r for r in evaluate_radio(p,other) if r['hit'])
    for p in plans:
        for role,wp in [('start',p.waypoints[0]),('goal',p.waypoints[-1])]:
            clearances.append(dict(plan_id=p.plan_id,role=role,lat_deg=wp.lat_deg,lon_deg=wp.lon_deg,
                clearance_m=min(Point(wp.x_m,wp.y_m).distance(Polygon(z.polygon_utm)) for z in window.zones)))
        r=p.radio
        clearances.append(dict(plan_id=p.plan_id,role='gcs',lat_deg=r.gcs_lat_deg,lon_deg=r.gcs_lon_deg,
            clearance_m=min(Point(r.gcs_x_m,r.gcs_y_m).distance(Polygon(z.polygon_utm)) for z in window.zones)))
    reload_equal = driver.restart()
    result = dict(approved_count=len(approved),active_count=len(plans),validation_errors=errors,
                  oracle_residual_conflicts=len(pair_hits)+len(rf_hits)+sum('Zone' in e for e in errors.values()),
                  space_time_hits=pair_hits,rf_hits=rf_hits,oracle_samples=samples,max_relative_step_m=max_step,
                  containment_checks=len(containment),tunnel_containment_percent=100.*sum(containment)/len(containment) if containment else 0.,
                  db_reload_exact_match=reload_equal,clearances=clearances,
                  minimum_site_clearance_m=min((c['clearance_m'] for c in clearances),default=0.))
    result['deconflicted_checker_conflicts']=clean_checker_records
    driver.event('independent_audit',**result)
    return result
