"""Candidate-only mitigation proposals; approved reservations remain immutable."""
from copy import deepcopy
from dataclasses import replace
import math
from .conflict import check_all_conflicts
from .models import ResolutionProposal, PlannerStatus
from .planner import plan_4d_path
from .tunnel import build_tunnel


def precedence_key(plan):
    """Lower keys take precedence; creation time breaks equal priorities."""
    return (not plan.is_crewed,plan.priority,plan.created_epoch_s,plan.plan_id)


def within_limits(plan, weather):
    if weather is None or len(plan.waypoints)<2:
        return False
    theta = math.radians(weather.wind_from_deg)
    wx,wy = -weather.wind_speed_mps*math.sin(theta),-weather.wind_speed_mps*math.cos(theta)
    previous = None
    for a,b in zip(plan.waypoints,plan.waypoints[1:]):
        dt = b.epoch_s-a.epoch_s
        if dt<=0 or min(a.alt_m,b.alt_m)<0:
            return False
        dx,dy,dz = b.x_m-a.x_m,b.y_m-a.y_m,b.alt_m-a.alt_m
        length = math.hypot(dx,dy)
        if math.hypot(dx/dt-wx,dy/dt-wy)>plan.limits.max_airspeed_mps+1e-9 or dz/dt>plan.limits.max_climb_mps+1e-9 or -dz/dt>plan.limits.max_descent_mps+1e-9:
            return False
        if length<1e-8:
            if not plan.limits.hover_allowed:
                return False
            continue
        if length+1e-8<plan.limits.min_turn_radius_m:
            return False
        heading = math.atan2(dx,dy)
        if previous is not None and abs(math.remainder(heading-previous,2*math.pi))>math.pi/4+1e-8:
            return False
        previous = heading
    return True


def resolve_conflicts(candidate, active_plans, zones, weather, alternate_freqs_mhz):
    active = sorted(active_plans,key=precedence_key)
    original = check_all_conflicts(candidate,active,zones,weather)
    def proposal(action, plan, operator=False):
        return ResolutionProposal(candidate.plan_id,action,action.replace('_',' ').capitalize(),plan,operator,len(original) if operator else 0)
    if candidate.is_crewed or candidate.status in ('APPROVED','CREWED_ACTIVE'):
        return proposal('OPERATOR_ESCALATION',None,True)
    def checked(p):
        p.tunnel = build_tunnel(p.plan_id,p.waypoints,
            candidate.tunnel.horiz_half_width_m if candidate.tunnel else 100.,
            candidate.tunnel.vert_margin_m if candidate.tunnel else 30.,
            candidate.tunnel.time_buf_s if candidate.tunnel else 15.)
        return within_limits(p,weather) and not check_all_conflicts(p,active,zones,weather)
    if not original and within_limits(candidate,weather):
        return proposal('NO_CHANGE',deepcopy(candidate))
    for shift in (60,120,180,300,600):
        p = deepcopy(candidate)
        p.waypoints = [replace(w,epoch_s=w.epoch_s+shift) for w in p.waypoints]
        if checked(p):
            return proposal('TIME_SHIFT',p)
    for shift in (60,-60,120,-120):
        p = deepcopy(candidate)
        p.waypoints = [replace(w,alt_m=w.alt_m+shift) for w in p.waypoints]
        if checked(p):
            return proposal('ALTITUDE_SHIFT',p)
    first,last = candidate.waypoints[0],candidate.waypoints[-1]
    routed = plan_4d_path(first,last.lat_deg,last.lon_deg,last.alt_m,candidate.limits,candidate.radio,'shortest_time',zones,active,weather)
    if routed.status == PlannerStatus.FOUND:
        p = deepcopy(candidate)
        p.waypoints = routed.plan.waypoints
        if checked(p):
            return proposal('RE_ROUTE',p)
    if original and all(r.kind=='RADIO' for r in original):
        for frequency in alternate_freqs_mhz:
            if frequency<=0 or not math.isfinite(frequency):
                continue
            p = deepcopy(candidate)
            p.radio.freq_mhz = frequency
            if checked(p):
                return proposal('RADIO_CHANNEL_SHIFT',p)
    return proposal('OPERATOR_ESCALATION',None,True)
