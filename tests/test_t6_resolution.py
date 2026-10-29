from copy import deepcopy
from dataclasses import replace
from minerva.conflict import check_all_conflicts
from minerva.resolver import resolve_conflicts, precedence_key, within_limits
from minerva.test_rig.scenarios import build_t6_scenarios


def test_sixty_labelled_cases():
    counts = {'resolvable':0,'unresolvable':0}
    for candidate,active,zones,weather,frequencies,label in build_t6_scenarios():
        before = deepcopy((candidate,active,zones,weather))
        proposal = resolve_conflicts(candidate,active,zones,weather,frequencies)
        assert (candidate,active,zones,weather) == before
        assert proposal.requires_operator == (label=='unresolvable')
        if label=='resolvable':
            assert proposal.modified_plan is not None
            assert proposal.conflicts_remaining == 0
            assert within_limits(proposal.modified_plan,weather)
            assert check_all_conflicts(proposal.modified_plan,active,zones,weather) == []
        else:
            assert proposal.modified_plan is None
        counts[label] += 1
    assert counts == {'resolvable':20,'unresolvable':40}
    print('T6 60/60 labels matched; 20 resolved, 40 escalated; inputs unchanged')


def test_priority_and_creation_order():
    p = build_t6_scenarios()[0][0]
    plans = [replace(p,plan_id='low',priority=4),replace(p,plan_id='new',priority=1,created_epoch_s=20),replace(p,plan_id='old',priority=1,created_epoch_s=10),replace(p,plan_id='crewed',is_crewed=True,priority=4)]
    assert [p.plan_id for p in sorted(plans,key=precedence_key)] == ['crewed','old','new','low']


def test_ladder_time_then_altitude():
    cases = build_t6_scenarios()
    for index,action in ((0,'TIME_SHIFT'),(1,'ALTITUDE_SHIFT')):
        p,active,zones,weather,freqs,_ = cases[index]
        proposal = resolve_conflicts(p,active,zones,weather,freqs)
        assert proposal.action_type == action


def test_reroute_after_time_and_altitude_fail():
    from minerva.test_rig.scenarios import local_zone, calm_weather
    from minerva.test_rig.path_validator import validate_path
    p = build_t6_scenarios()[0][0]
    p.limits = replace(p.limits,min_turn_radius_m=100.)
    zones = [local_zone(500500,5500000,75)]
    proposal = resolve_conflicts(p,[],zones,calm_weather(),[])
    assert proposal.action_type == 'RE_ROUTE'
    assert validate_path(proposal.modified_plan,zones,[],calm_weather()) == []


def test_radio_shift_is_last_mitigation():
    from minerva.test_rig.scenarios import make_plan, calm_weather
    p = build_t6_scenarios()[0][0]
    other = make_plan('radio_only',[(500000,5502000,150,0),(501000,5502000,150,10000)])
    proposal = resolve_conflicts(p,[other],[],calm_weather(),[5800.])
    assert proposal.action_type == 'RADIO_CHANNEL_SHIFT'
    assert proposal.modified_plan.radio.freq_mhz == 5800.
    assert check_all_conflicts(proposal.modified_plan,[other],[],calm_weather()) == []


def test_clean_candidate_and_failed_channel_escalation():
    from minerva.test_rig.scenarios import make_plan, calm_weather
    p = build_t6_scenarios()[0][0]
    assert resolve_conflicts(p,[],[],calm_weather(),[]).action_type == 'NO_CHANGE'
    other = make_plan('radio_only',[(500000,5502000,150,0),(501000,5502000,150,10000)])
    result = resolve_conflicts(p,[other],[],calm_weather(),[2401.])
    assert result.requires_operator
    assert result.conflicts_remaining>0
