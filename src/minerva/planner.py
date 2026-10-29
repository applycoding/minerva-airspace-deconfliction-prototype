"""Bounded grid search for simulation trajectories in UTM Zone 12N."""
from dataclasses import replace
import heapq
import itertools
import math
import time
from shapely.geometry import LineString, Point, Polygon
from .coords import lonlat_to_utm12n, utm12n_to_lonlat
from .models import FlightPlan, Waypoint4D, PlannerResult, PlannerStatus
from .conflict import check_all_conflicts, check_zone_conflicts, zone_polygon
from .tunnel import build_tunnel

WEIGHTS = {'shortest_time': (0., 0.), 'avoid_zones': (5., .5), 'avoid_radio': (.5, 8.)}
DIRECTIONS = ((0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1))


def solve_wind_triangle(airspeed_mps, azimuth_rad, wind_from_deg, wind_speed_mps):
    theta = math.radians(wind_from_deg)
    wx, wy = -wind_speed_mps*math.sin(theta), -wind_speed_mps*math.cos(theta)
    along = wx*math.sin(azimuth_rad)+wy*math.cos(azimuth_rad)
    discriminant = airspeed_mps**2-max(0.,wind_speed_mps**2-along**2)
    if discriminant < 0:
        return None
    speed = along+math.sqrt(discriminant)
    return speed if speed > 1e-9 else None


def edge_cost(a, b, objective, zones, existing_plans):
    """Soft proximity costs; hard exclusions are always checked separately."""
    wz, wr = WEIGHTS[objective]
    if not wz and not wr:
        return b.epoch_s-a.epoch_s
    line = LineString(((a.x_m,a.y_m),(b.x_m,b.y_m)))
    zone_risk = max((1./(1.+line.distance(zone_polygon(tuple(z.polygon_utm)))/250.) for z in zones), default=0.) if wz else 0.
    radio_risk = max((1./(1.+line.distance(Point(p.radio.gcs_x_m,p.radio.gcs_y_m))/1000.) for p in existing_plans),default=0.)
    return (b.epoch_s-a.epoch_s)*(1+wz*zone_risk+wr*radio_risk)


def plan_4d_path(start_wp, goal_lat, goal_lon, goal_alt_m, limits, radio, objective,
                 zones, existing_plans, weather, grid_step_m=250., alt_step_m=30., max_expansions=40000):
    started = time.perf_counter()
    expansions = 0
    def result(status, plan=None, message=''):
        return PlannerResult(status,plan,expansions,time.perf_counter()-started,message)
    if objective not in WEIGHTS:
        raise ValueError('Unknown planner objective')
    if grid_step_m <= 0 or alt_step_m <= 0 or max_expansions < 0:
        raise ValueError('Invalid grid or expansion budget')
    if weather is None or not weather.valid_start_epoch_s <= start_wp.epoch_s <= weather.valid_end_epoch_s or max(weather.wind_speed_mps,weather.gust_mps) > limits.max_wind_mps:
        return result(PlannerStatus.REJECTED_WEATHER)
    sx,sy = lonlat_to_utm12n(start_wp.lon_deg,start_wp.lat_deg)
    gx,gy = lonlat_to_utm12n(goal_lon,goal_lat)
    start = replace(start_wp,x_m=sx,y_m=sy)
    goal = Waypoint4D(goal_lat,goal_lon,goal_alt_m,start.epoch_s,gx,gy)
    plan_id = 'planned'
    while any(p.plan_id == plan_id for p in existing_plans):
        plan_id += '_'
    def plan(points):
        p = FlightPlan(plan_id,'PLANNED',4,'DRAFT',start.epoch_s,limits,radio,points,None)
        p.tunnel = build_tunnel(p.plan_id,points)
        return p
    if min(start.alt_m,goal_alt_m) < 0 or math.hypot(gx-sx,gy-sy) < 1e-6:
        return result(PlannerStatus.REJECTED_START_GOAL)
    for wp in (start,goal):
        if check_zone_conflicts(plan([wp,replace(wp,epoch_s=wp.epoch_s+.001)]),zones):
            return result(PlannerStatus.REJECTED_START_GOAL)
    step = max(grid_step_m,limits.min_turn_radius_m)
    # Six cells of lateral detour and four vertical layers around the endpoints.
    nx,ny = math.ceil(abs(gx-sx)/step)+6,math.ceil(abs(gy-sy)/step)+6
    zlo,zhi = max(0.,min(start.alt_m,goal_alt_m)-4*alt_step_m),max(start.alt_m,goal_alt_m)+4*alt_step_m
    collision_plans = []
    for other in existing_plans:
        oh,ov = (other.tunnel.horiz_half_width_m,other.tunnel.vert_margin_m) if other.tunnel else (0.,0.)
        h,v = max(100.,100.+oh),max(30.,30.+ov)
        radio_overlap = abs(radio.freq_mhz-other.radio.freq_mhz) < (radio.bw_mhz+other.radio.bw_mhz)/2+max(radio.guard_mhz,other.radio.guard_mhz)
        far = (max(w.x_m for w in other.waypoints)+h < sx-nx*step
               or min(w.x_m for w in other.waypoints)-h > sx+nx*step
               or max(w.y_m for w in other.waypoints)+h < sy-ny*step
               or min(w.y_m for w in other.waypoints)-h > sy+ny*step
               or max(w.alt_m for w in other.waypoints)+v < zlo
               or min(w.alt_m for w in other.waypoints)-v > zhi)
        if radio_overlap or not far:
            collision_plans.append(other)
    wind = weather.wind_speed_mps
    theta = math.radians(weather.wind_from_deg)
    wx,wy = -wind*math.sin(theta),-wind*math.cos(theta)
    def transition(a,b,previous):
        dx,dy,dz = b.x_m-a.x_m,b.y_m-a.y_m,b.alt_m-a.alt_m
        length = math.hypot(dx,dy)
        if length < 1e-6:
            if not limits.hover_allowed or dz != 0 or wind > limits.max_airspeed_mps:
                return None
            duration,heading = 10.,previous
        else:
            if length+1e-6 < limits.min_turn_radius_m:
                return None
            heading = math.atan2(dx,dy)
            if previous is not None and abs(math.remainder(heading-previous,2*math.pi)) > math.pi/4+1e-8:
                return None
            speed = solve_wind_triangle(.85*limits.max_airspeed_mps,heading,weather.wind_from_deg,wind)
            if speed is None:
                return None
            rate = limits.max_climb_mps if dz >= 0 else limits.max_descent_mps
            duration = max(length/speed,abs(dz)/rate)
            if math.hypot(dx/duration-wx,dy/duration-wy) > limits.max_airspeed_mps+1e-9:
                return None
        b = replace(b,epoch_s=a.epoch_s+duration)
        if check_all_conflicts(plan([a,b]),collision_plans,zones,weather):
            return None
        return b,heading
    serial = itertools.count()
    root = (0,0,0,None,0)
    # Each retained label stores its own parent so later improvements cannot alter timing.
    labels = [(root,start,None,None,0.)]
    best = {root:0.}
    queue = [(0.,abs(start.alt_m-goal_alt_m),next(serial),0)]
    def heuristic(w):
        return math.hypot(gx-w.x_m,gy-w.y_m)/(.85*limits.max_airspeed_mps+wind)
    while queue:
        _,_,_,idx = heapq.heappop(queue)
        state,a,previous,parent,cost = labels[idx]
        if cost != best.get(state):
            continue
        if expansions >= max_expansions or time.perf_counter()-started >= 9.5:
            return result(PlannerStatus.BUDGET_EXHAUSTED)
        expansions += 1
        if state == ('goal',):
            points = []
            endidx = idx
            while endidx is not None:
                _,wp,_,endidx,_ = labels[endidx]
                points.append(wp)
            p = plan(list(reversed(points)))
            if not check_all_conflicts(p,existing_plans,zones,weather):
                return result(PlannerStatus.FOUND,p,f'Grid cost {cost:.6f}')
            continue
        ix,iy,iz,octant,waits = state
        # The exact endpoint is a boundary node, checked like every other edge.
        terminal = transition(a,goal,previous) if math.hypot(gx-a.x_m,gy-a.y_m) <= step*1.5 else None
        if terminal is not None:
            b,_ = terminal
            final_cost = cost+edge_cost(a,b,objective,zones,existing_plans)
            heapq.heappush(queue,(final_cost,0.,next(serial),len(labels)))
            labels.append((('goal',),b,None,idx,final_cost))
            best[('goal',)] = min(final_cost,best.get(('goal',),math.inf))
        options = range(8) if octant is None else ((octant-1)%8,octant,(octant+1)%8)
        for h in options:
            dx,dy = DIRECTIONS[h]
            for dz in (-1,0,1):
                x,y,z = ix+dx,iy+dy,iz+dz
                alt = start.alt_m+z*alt_step_m
                if abs(x)>nx or abs(y)>ny or not zlo <= alt <= zhi:
                    continue
                lon,lat = utm12n_to_lonlat(sx+x*step,sy+y*step)
                b = Waypoint4D(lat,lon,alt,0.,sx+x*step,sy+y*step)
                moved = transition(a,b,previous)
                if moved:
                    b,heading = moved
                    new = (x,y,z,h,waits)
                    newcost = cost+edge_cost(a,b,objective,zones,existing_plans)
                    if newcost < best.get(new,math.inf):
                        best[new] = newcost
                        labels.append((new,b,heading,idx,newcost))
                        heapq.heappush(queue,(newcost+heuristic(b),abs(b.alt_m-goal_alt_m),next(serial),len(labels)-1))
        if limits.hover_allowed and waits < 6:
            moved = transition(a,replace(a),previous)
            if moved:
                b,heading = moved
                new = (ix,iy,iz,octant,waits+1)
                newcost = cost+edge_cost(a,b,objective,zones,existing_plans)
                if newcost < best.get(new,math.inf):
                    best[new] = newcost
                    labels.append((new,b,heading,idx,newcost))
                    heapq.heappush(queue,(newcost+heuristic(b),abs(b.alt_m-goal_alt_m),next(serial),len(labels)-1))
    return result(PlannerStatus.NO_PATH_WITHIN_GRID)
