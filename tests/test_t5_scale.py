from minerva.test_rig.scenarios import benchmark_t5


def test_t5_scale():
    report = benchmark_t5()
    assert set(report['counts']) == {10,50,200,500}
    assert report['runner']['logical_cpus'] > 0
    assert report['runner']['ram_bytes'] > 0
    for count,data in report['counts'].items():
        assert data['identical'] and data['conflict_count'] > 0
        for mode in ('exhaustive','indexed'):
            assert 0 < data[mode]['median_s'] <= data[mode]['p95_s']
            if count in (200,500):
                assert data[mode]['median_s'] <= {200:1.,500:3.}[count]
    print(report)


def test_index_mixed_margins_buffers_and_snapshot():
    from copy import deepcopy
    from dataclasses import FrozenInstanceError
    import pytest
    from minerva.conflict import SpatialIndex, check_all_conflicts
    from minerva.test_rig.scenarios import build_t5_scenario, calm_weather
    from minerva.tunnel import build_tunnel
    candidate,plans = build_t5_scenario(50)
    for i,plan in enumerate(plans):
        plan.tunnel = build_tunnel(plan.plan_id,plan.waypoints,horiz_half_width_m=50+i*10,vert_margin_m=20+i,time_buf_s=i)
    candidate.tunnel = build_tunnel(candidate.plan_id,candidate.waypoints,time_buf_s=35)
    index = SpatialIndex(plans)
    assert check_all_conflicts(candidate,plans,[],calm_weather()) == check_all_conflicts(candidate,plans,[],calm_weather(),index=index)
    with pytest.raises(FrozenInstanceError):
        index.entries = ()
    snapshot = deepcopy(index.entries)
    plans[0].waypoints[0].x_m += 10000
    assert index.entries == snapshot
    index = SpatialIndex(plans,default_t_buf_s=0)
    assert check_all_conflicts(candidate,plans,[],calm_weather()) == check_all_conflicts(candidate,plans,[],calm_weather(),index=index)
    assert check_all_conflicts(candidate,plans,[],calm_weather(),default_t_buf_s=60) == check_all_conflicts(candidate,plans,[],calm_weather(),default_t_buf_s=60,index=index)
