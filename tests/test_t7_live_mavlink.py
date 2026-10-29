from copy import deepcopy
from dataclasses import replace
import time
import pytest
from minerva.live import LiveTracker, UDPReceiver, interpolate
from minerva.test_rig.sim import VirtualClock, SimulatedDrone
from minerva.test_rig.scenarios import make_plan, waypoint, calm_weather
from minerva.models import TrackMatchStatus, PlannerStatus
from minerva.tunnel import build_tunnel
from minerva.db import approve_and_persist_plan, get_db_revision, list_active_plans, StaleStateError
from minerva.conflict import check_all_conflicts


def fixture_plan():
    p = make_plan('live',[(500000,5500000,150,1000),(502000,5500000,150,1100)])
    p.tunnel = build_tunnel(p.plan_id,p.waypoints)
    return p


@pytest.mark.parametrize('known',[True,False])
def test_track_match_udp(known):
    plan = fixture_plan(); other = deepcopy(plan); other.plan_id='other'
    for w in other.waypoints: w.y_m+=1000
    clock = VirtualClock()
    receiver = UDPReceiver(); drone = SimulatedDrone(receiver.address,clock,7,2)
    key = (drone.address,7,2)
    tracker = LiveTracker([plan,other],{key:plan.plan_id} if known else {},clock)
    matches = 0
    try:
        for i in range(10):
            drone.send(interpolate(plan,clock()))
            reports = receiver.poll(tracker)
            assert len(reports)==1
            report = reports[0]
            if known or i>=4:
                assert report.plan_id=='live'
                assert report.status==(TrackMatchStatus.MATCHED_KNOWN_ID if known else TrackMatchStatus.MATCHED_TRAJECTORY)
                assert not report.outside and not report.drift
                matches += 1
            else: assert report.status==TrackMatchStatus.UNMATCHED
            clock.advance(1)
        assert matches==(10 if known else 6)
        print(f'T7 {matches}/{matches} correct matches; known={known}')
    finally:
        drone.close(); receiver.close()


def test_ambiguity_margin_and_source_identity():
    plan = fixture_plan(); twin = replace(deepcopy(plan),plan_id='twin')
    clock = VirtualClock(); receiver = UDPReceiver(); drone = SimulatedDrone(receiver.address,clock)
    tracker = LiveTracker([plan,twin],clock=clock)
    try:
        for i in range(5):
            drone.send(interpolate(plan,clock())); report = receiver.poll(tracker)[0]; clock.advance(1)
        assert report.status==TrackMatchStatus.AMBIGUOUS and report.plan_id is None
        for w in twin.waypoints: w.y_m+=15
        # 10 m from first, 5 m from second: exactly the required 2x margin.
        for i in range(5):
            wp = interpolate(plan,clock()); drone.send(waypoint(wp.x_m,wp.y_m+10,wp.alt_m,clock()))
            report = receiver.poll(tracker)[0]; clock.advance(1)
        assert report.plan_id=='twin'
        tracker.known_ids[(('127.0.0.1',drone.address[1]+1),1,1)]='live'
        assert report.status==TrackMatchStatus.MATCHED_TRAJECTORY
    finally: drone.close(); receiver.close()


def test_drift_two_intervals_and_separate_reroute(conn):
    plan = fixture_plan(); approve_and_persist_plan(conn,plan,0)
    clock = VirtualClock(); receiver = UDPReceiver(); drone = SimulatedDrone(receiver.address,clock)
    tracker = LiveTracker([plan],{(drone.address,1,1):plan.plan_id},clock)
    try:
        drone.send(plan.waypoints[0]); assert not receiver.poll(tracker)[0].drift
        crossing = clock()+1
        for i in range(2):
            clock.advance(1)
            expected = interpolate(plan,clock())
            drone.send(waypoint(expected.x_m,expected.y_m+250,150,clock()))
            report = receiver.poll(tracker)[0]
            assert report.outside and report.drift==(i==1)
        latency = clock()-crossing
        assert latency<=2 and len(tracker.alerts)==1
        assert tracker.alerts[0].kind=='LIVE_DRIFT'
        before = list_active_plans(conn)
        start = time.perf_counter()
        result = tracker.compute_reroute(report,before,[],calm_weather())
        elapsed = time.perf_counter()-start
        assert result.status==PlannerStatus.FOUND and elapsed<=5
        assert check_all_conflicts(result.plan,[],[],calm_weather())==[]
        assert list_active_plans(conn)==before and get_db_revision(conn)==1
        with pytest.raises(StaleStateError): tracker.accept_reroute(conn,result,plan.plan_id,0)
        assert tracker.accept_reroute(conn,result,plan.plan_id,1)==2
        active = list_active_plans(conn)
        assert len(active)==1 and active[0].plan_id==result.plan.plan_id
        assert conn.execute('SELECT status FROM flight_plans WHERE plan_id=?',(plan.plan_id,)).fetchone()[0]=='SUPERSEDED'
        print(f'T7 drift latency={latency:.1f} report intervals; re-route={elapsed:.6f} s; SQLite accepted')
    finally: drone.close(); receiver.close()


def test_altitude_time_and_consecutive_reset():
    plan = fixture_plan(); clock = VirtualClock(); receiver = UDPReceiver(); drone = SimulatedDrone(receiver.address,clock)
    tracker = LiveTracker([plan],{(drone.address,1,1):plan.plan_id},clock)
    try:
        for alt,drift in [(190,False),(150,False),(190,False),(190,True)]:
            wp = interpolate(plan,clock()); drone.send(replace(wp,alt_m=alt))
            report = receiver.poll(tracker)[0]
            assert report.drift==drift
            clock.advance(1)
        clock.advance(200)
        drone.send(plan.waypoints[-1]); report = receiver.poll(tracker)[0]
        assert report.outside
    finally: drone.close(); receiver.close()


def test_direct_datagram_drift_and_acceptance(conn):
    """Codec-to-tracker check supplements, but does not replace, UDP evidence."""
    import struct
    from minerva.live import encode_mavlink_v2_frame
    plan = fixture_plan(); approve_and_persist_plan(conn,plan,0)
    clock = VirtualClock(); source = ('127.0.0.1',12345)
    tracker = LiveTracker([plan],{(source,1,1):'live'},clock)
    for i in range(3):
        wp = interpolate(plan,clock())
        wp = waypoint(wp.x_m,wp.y_m+(250 if i else 0),150,clock())
        payload = struct.pack('<IiiiihhhH',i*1000,round(wp.lat_deg*1e7),round(wp.lon_deg*1e7),850000,150000,0,0,0,0)
        report = tracker.process_datagram(encode_mavlink_v2_frame(33,payload),source)[0]
        assert report.drift==(i==2)
        clock.advance(1)
    start = time.perf_counter()
    result = tracker.compute_reroute(report,list_active_plans(conn),[],calm_weather())
    elapsed = time.perf_counter()-start
    assert result.status==PlannerStatus.FOUND and elapsed<=5
    assert check_all_conflicts(result.plan,[],[],calm_weather())==[]
    assert get_db_revision(conn)==1
    tracker.accept_reroute(conn,result,'live',1)
    assert len(list_active_plans(conn))==1
    assert list_active_plans(conn)[0].plan_id==result.plan.plan_id
    print(f'Direct datagrams: drift on second outside report; re-route {elapsed:.6f} s; accepted revision 2')


def test_direct_unknown_match_and_ambiguity():
    import struct
    from minerva.live import encode_mavlink_v2_frame
    plan = fixture_plan(); other = deepcopy(plan); other.plan_id='other'
    for w in other.waypoints: w.y_m+=40
    clock = VirtualClock(); source = ('127.0.0.1',12345)
    tracker = LiveTracker([plan,other],clock=clock)
    for i in range(10):
        wp = interpolate(plan,clock())
        wp = waypoint(wp.x_m,wp.y_m+(20 if i>=5 else 0),150,clock())
        payload = struct.pack('<IiiiihhhH',i*1000,round(wp.lat_deg*1e7),round(wp.lon_deg*1e7),850000,150000,0,0,0,0)
        report = tracker.process_datagram(encode_mavlink_v2_frame(33,payload),source)[0]
        if i==4:
            assert report.plan_id=='live' and report.status==TrackMatchStatus.MATCHED_TRAJECTORY
        if i==9:
            assert report.plan_id is None and report.status==TrackMatchStatus.AMBIGUOUS
        clock.advance(1)
