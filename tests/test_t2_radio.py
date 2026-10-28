from dataclasses import replace
import math
import pytest
from minerva.conflict import check_radio_conflict
from minerva.test_rig.oracle import evaluate_radio
from minerva.test_rig.scenarios import build_t2_scenarios, make_plan


def compare(a,b):
    actual = check_radio_conflict(a,b)
    expected = evaluate_radio(a,b)
    assert {(r.plan_a_id,r.plan_b_or_zone_id) for r in actual} == {(r['tx_id'],r['rx_id']) for r in expected if r['hit']}
    for record in actual:
        power = next(r['power_dbm'] for r in expected if r['tx_id'] == record.plan_a_id)
        assert record.rx_power_dbm == pytest.approx(power,abs=1e-10)
    return actual


def test_t2_seeded_50():
    scenarios = build_t2_scenarios()
    assert len(scenarios) == 50
    for a,b in scenarios:
        compare(a,b)


def test_clamp_guard_threshold_and_both_directions():
    a = make_plan('a',[(0,0,2,0),(0,0,2,10)])
    b = make_plan('b',[(100000,0,2,0),(100000,0,2,10)])
    b.radio.gcs_x_m = 0
    a.radio.gcs_x_m = 100000
    records = compare(a,b)
    assert len(records) == 2
    power = 24-32.44-20*math.log10(.01)-20*math.log10(2400)
    assert all(r.rx_power_dbm == pytest.approx(power) for r in records)
    b.radio.rx_threshold_dbm = power
    assert len(compare(a,b)) == 1
    b.radio.rx_threshold_dbm = power-1e-6
    assert len(compare(a,b)) == 2
    b.radio.freq_mhz = 2413
    b.radio.guard_mhz = 3
    assert compare(a,b) == []
    b.radio.freq_mhz -= .001
    assert len(compare(a,b)) == 2
    b.waypoints = [replace(w,epoch_s=w.epoch_s+11) for w in b.waypoints]
    assert compare(a,b) == []


def test_fixed_receiver_not_aircraft_and_clipped_leg_minimum():
    a = make_plan('a',[(-1000,0,2,0),(1000,0,2,10)])
    b = make_plan('b',[(100000,0,2,4),(100000,0,2,6)])
    b.radio.gcs_x_m = 0
    a.radio.rx_threshold_dbm = 100
    records = compare(a,b)
    assert len(records) == 1 and records[0].plan_a_id == 'a'
    assert records[0].start_epoch_s == 4 and records[0].end_epoch_s == 6
    b.waypoints = [replace(w,epoch_s=w.epoch_s+4) for w in b.waypoints]
    records = compare(a,b)
    assert records[0].rx_power_dbm < -65
