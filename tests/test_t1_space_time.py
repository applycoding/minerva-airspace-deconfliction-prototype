from dataclasses import replace
import pytest
from minerva.conflict import check_leg_pair_exact, extend_waypoints_with_time_buffer, check_all_conflicts, SpatialIndex
from minerva.test_rig.oracle import sample_space_time
from minerva.test_rig.scenarios import build_t1_scenarios, hand_space_time_fixtures, make_plan, calm_weather
from minerva.tunnel import build_tunnel


def test_t1_seeded_200():
    data = build_t1_scenarios()
    assert data['excluded_band_count'] > 0
    assert len(data['scenarios']) == 200
    assert sum(expected for _,_,expected in data['scenarios']) == 100
    for a,b,expected in data['scenarios']:
        oracle = sample_space_time(a.waypoints,b.waypoints)
        exact = any(check_leg_pair_exact(la,lb,100.,30.)[0] for la in extend_waypoints_with_time_buffer(a.waypoints,15.) for lb in extend_waypoints_with_time_buffer(b.waypoints,15.))
        assert exact == oracle['hit'] == expected
        assert oracle['max_relative_step_m'] <= 1.+1e-12


@pytest.mark.parametrize('name,a,b,expected',hand_space_time_fixtures())
def test_t1_hand(name,a,b,expected):
    result = check_leg_pair_exact(a,b,100.,30.)
    assert result[0] == expected, name
    assert sample_space_time(list(a),list(b),time_buf_s=0)['hit'] == expected
    if name == 'sub_sample':
        assert result[3] == pytest.approx(0.)
        assert result[1] == pytest.approx(.1134,abs=1e-10)
        assert result[2] == pytest.approx(.1334,abs=1e-10)


def test_interval_intersection_and_strict_boundaries():
    a = make_plan('a',[(0,0,100,0),(0,0,100,10)])
    b = make_plan('b',[(-200,0,200,0),(200,0,120,10)])
    assert not check_leg_pair_exact(tuple(a.waypoints),tuple(b.waypoints),100,30)[0]
    b.waypoints = [replace(w,alt_m=130) for w in a.waypoints]
    assert not check_leg_pair_exact(tuple(a.waypoints),tuple(b.waypoints),100,30)[0]
    b.waypoints = [replace(w,alt_m=129) for w in a.waypoints]
    hit,start,end,h,v = check_leg_pair_exact(tuple(a.waypoints),tuple(b.waypoints),100,30)
    assert hit and (start,end,h,v) == (0,10,0,29)


def test_holds_weather_and_tunnel_thresholds():
    a = make_plan('a',[(0,0,100,0),(100,0,100,10)])
    b = make_plan('b',[(100,0,100,25),(200,0,100,35)])
    legs = extend_waypoints_with_time_buffer(a.waypoints,15)
    assert len(legs) == 3
    assert (legs[0][0].epoch_s,legs[-1][-1].epoch_s) == (-15,25)
    assert legs[0][0].x_m == legs[0][1].x_m == 0
    assert any(r.kind == 'SPACE_TIME' for r in check_all_conflicts(a,[b],[],calm_weather()))
    assert any(r.kind == 'WEATHER_WIND' for r in check_all_conflicts(a,[],[],None))
    for weather,expected in ((calm_weather(),False),(replace(calm_weather(),gust_mps=15),False),(replace(calm_weather(),gust_mps=15.1),True),(replace(calm_weather(),valid_end_epoch_s=9),True)):
        assert bool(check_all_conflicts(a,[],[],weather)) == expected
    b = make_plan('b',[(0,150,150,0),(100,150,150,10)])
    assert not any(r.kind == 'SPACE_TIME' for r in check_all_conflicts(a,[b],[],calm_weather()))
    for p in (a,b):
        p.tunnel = build_tunnel(p.plan_id,p.waypoints)
    assert any(r.kind == 'SPACE_TIME' for r in check_all_conflicts(a,[b],[],calm_weather()))
    a.tunnel.time_buf_s = 40
    assert check_all_conflicts(a,[b],[],calm_weather()) == check_all_conflicts(a,[b],[],calm_weather(),index=SpatialIndex([b]))
