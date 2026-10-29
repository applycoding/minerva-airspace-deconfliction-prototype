"""Simulation-only bounded planner acceptance and independent validation."""
from dataclasses import replace
import math
import multiprocessing
import statistics
import time
import numpy as np
import pytest
from minerva.models import PlannerStatus
from minerva.planner import plan_4d_path, solve_wind_triangle, edge_cost
from minerva.test_rig.scenarios import build_t4_scenarios, local_zone, waypoint, make_plan, t4_feasible_witness
from minerva.test_rig.path_validator import validate_path


def _run_requests(connection):
    for request in build_t4_scenarios():
        started = time.perf_counter()
        result = plan_4d_path(**request)
        connection.send((result,time.perf_counter()-started))
    connection.close()


def test_t4_hundred_requests():
    # A separate process gives a real, cross-platform deadline even if search hangs.
    context = multiprocessing.get_context('spawn')
    parent,child = context.Pipe(duplex=False)
    process = context.Process(target=_run_requests,args=(child,))
    process.start()
    times = []
    found = 0
    try:
        for request in build_t4_scenarios():
            assert validate_path(t4_feasible_witness(request),request['zones'],request['existing_plans'],request['weather']) == []
            assert parent.poll(10.), 'Request exceeded hard 10 second timeout'
            result,elapsed = parent.recv()
            assert elapsed<10.
            assert isinstance(result.status,PlannerStatus)
            times.append(elapsed)
            if result.status == PlannerStatus.FOUND:
                found += 1
                assert validate_path(result.plan,request['zones'],request['existing_plans'],request['weather']) == []
        process.join(5)
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.terminate(); process.join()
        parent.close(); child.close()
    median,p95 = statistics.median(times),float(np.percentile(times,95))
    print(f'T4 FOUND={found}/100 independently validated={found}/{found}; median={median:.6f}s p95={p95:.6f}s')
    assert found>=95
    assert median<=2.


def request():
    return build_t4_scenarios()[0]


def test_wind_triangle_numerics():
    assert solve_wind_triangle(20,0,180,30)==pytest.approx(50)
    assert solve_wind_triangle(20,0,0,30) is None
    assert solve_wind_triangle(20,0,90,10)==pytest.approx(math.sqrt(300))
    assert solve_wind_triangle(20,0,90,21) is None


@pytest.mark.parametrize('at_goal',[False,True])
def test_start_goal_zone(at_goal):
    r = request()
    wp = waypoint(501000,5500000,120,0) if at_goal else r['start_wp']
    r['zones'] = [local_zone(wp.x_m,wp.y_m)]
    assert plan_4d_path(**r).status == PlannerStatus.REJECTED_START_GOAL


@pytest.mark.parametrize('mode',['missing','stale','gust'])
def test_rejected_weather(mode):
    r = request()
    r['weather'] = None if mode=='missing' else replace(r['weather'],**({'valid_end_epoch_s':999} if mode=='stale' else {'gust_mps':100}))
    assert plan_4d_path(**r).status == PlannerStatus.REJECTED_WEATHER


def test_turns_and_climb_timing():
    r = request()
    r['zones'] = [local_zone(500500,5500000,100)]
    r['limits'] = replace(r['limits'],max_climb_mps=.4,max_descent_mps=.4)
    result = plan_4d_path(**r)
    assert result.status == PlannerStatus.FOUND
    assert len(result.plan.waypoints)>2
    assert validate_path(result.plan,r['zones'],[],r['weather']) == []
    damaged = replace(result.plan,waypoints=[waypoint(500000,5500000,150,1000),waypoint(500250,5500000,150,1010),waypoint(500250,5500250,150,1020)])
    assert 'Turn limit' in validate_path(damaged,[],[],r['weather'])


def test_objective_costs():
    a,b = waypoint(500000,5500000,100,0),waypoint(501000,5500000,100,40)
    zones = [local_zone(500500,5500400)]
    other = make_plan('rf',[(500500,5501000,100,0),(501500,5501000,100,100)])
    costs = [edge_cost(a,b,obj,zones,[other]) for obj in ('shortest_time','avoid_zones','avoid_radio')]
    assert costs[0] == 40.
    assert costs[0]<costs[1]<costs[2]


def test_budget_and_no_postprocessing():
    r = request()
    assert plan_4d_path(**r,max_expansions=0).status == PlannerStatus.BUDGET_EXHAUSTED
    result = plan_4d_path(**r)
    assert result.status == PlannerStatus.FOUND
    assert all(math.hypot(b.x_m-a.x_m,b.y_m-a.y_m)>=r['limits'].min_turn_radius_m-1e-6 for a,b in zip(result.plan.waypoints,result.plan.waypoints[1:]))


def test_strong_tailwind_and_headwind_paths():
    r = request()
    r['zones'] = []
    r['goal_alt_m'] = r['start_wp'].alt_m
    r['limits'] = replace(r['limits'],max_airspeed_mps=20.,max_wind_mps=50.)
    r['weather'] = replace(r['weather'],wind_from_deg=270.,wind_speed_mps=30.,gust_mps=30.)
    result = plan_4d_path(**r)
    assert result.status == PlannerStatus.FOUND
    assert validate_path(result.plan,[],[],r['weather']) == []
    r['weather'] = replace(r['weather'],wind_from_deg=90.)
    result = plan_4d_path(**r)
    assert result.status == PlannerStatus.NO_PATH_WITHIN_GRID


def test_stretched_climb_rechecks_airspeed():
    r = request()
    r['zones'] = []
    r['goal_alt_m'] = 270.
    r['limits'] = replace(r['limits'],max_airspeed_mps=20.,max_wind_mps=50.,max_climb_mps=.01)
    r['weather'] = replace(r['weather'],wind_from_deg=270.,wind_speed_mps=30.,gust_mps=30.)
    # At least one climb is needed; stretched edges cannot counter this tailwind.
    result = plan_4d_path(**r,max_expansions=100)
    assert result.status in (PlannerStatus.NO_PATH_WITHIN_GRID,PlannerStatus.BUDGET_EXHAUSTED)
    assert result.plan is None


def test_validator_rejects_corrupt_limits_weather_and_reservations():
    r = request()
    result = plan_4d_path(**r)
    assert result.status == PlannerStatus.FOUND
    p = result.plan
    fast = replace(p,waypoints=[replace(w,epoch_s=p.waypoints[0].epoch_s+(w.epoch_s-p.waypoints[0].epoch_s)/100) for w in p.waypoints])
    assert 'Airspeed' in validate_path(fast,[],[],r['weather'])
    assert 'Zone' in validate_path(p,[local_zone(p.waypoints[0].x_m,p.waypoints[0].y_m)],[],r['weather'])
    other = replace(p,plan_id='other')
    errors = validate_path(p,[],[other],r['weather'])
    assert 'Space/time' in errors
    assert 'Radio' in errors
    assert validate_path(p,[],[],None) == ['Missing weather']


def test_optional_hover_edges_use_exact_checker(monkeypatch):
    import minerva.planner as planner
    exact = planner.check_all_conflicts
    holds = []
    def recording_check(candidate,*args,**kwargs):
        a,b = candidate.waypoints[0],candidate.waypoints[-1]
        if (a.x_m,a.y_m)==(b.x_m,b.y_m):
            holds.append(b.epoch_s-a.epoch_s)
        return exact(candidate,*args,**kwargs)
    monkeypatch.setattr(planner,'check_all_conflicts',recording_check)
    r = request()
    assert r['limits'].hover_allowed
    assert planner.plan_4d_path(**r).status == PlannerStatus.FOUND
    assert holds and all(dt==pytest.approx(10.) for dt in holds)
    holds.clear()
    r['limits'] = replace(r['limits'],hover_allowed=False)
    assert planner.plan_4d_path(**r).status == PlannerStatus.FOUND
    assert holds == []
