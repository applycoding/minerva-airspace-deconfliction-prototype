"""Seeded operator scenarios using shipped files, real Qt, SQLite and UDP."""
from dataclasses import replace, asdict
from datetime import datetime, timezone
import math
import random
import time
import numpy as np
from ..models import FlightPlan, DroneLimits, RadioSpec, Waypoint4D, TrackMatchStatus
from ..coords import lonlat_to_utm12n, utm12n_to_lonlat
from ..tunnel import build_tunnel
from ..live import interpolate
from ..resources import data_dir
from ..test_rig.sim import SimulatedDrone
from ..test_rig.oracle import sample_space_time, evaluate_radio

EPOCH = datetime(2026,10,29,16,tzinfo=timezone.utc).timestamp()
SEED = 20261118
IDS = dict(S1='S1_INGEST_PLAN_RF_DB',S2='S2_SWARM_16_DECONFLICTION',S3='S3_LIVE_TRACK_MATCHING',
           S4='S4_CONFORMANCE_AND_PACKET_LOSS',S5='S5_DYNAMIC_REROUTE',S6='S6_ARDUPILOT_SITL')
ORIGIN = lonlat_to_utm12n(-111.42,50.15)
GCS = [(50.15,-111.42),(50.17,-111.43),(50.19,-111.44)]


def target(result, name, description, expected, measured, passed):
    result['targets'].append(dict(target_id=result['scenario_id'].split('_')[0]+'.'+name,
        description=description,expected=expected,measured=measured,passed=bool(passed)))


def point(x,y,alt,epoch):
    lon,lat = utm12n_to_lonlat(x,y)
    return Waypoint4D(lat,lon,alt,epoch,x,y)


def mission(pid, dx=0, dy=0, alt=60., start=EPOCH+120, length=1000., speed=20., frequency=2400., half=50., vertical=15., buffer=15.):
    x,y = ORIGIN[0]+dx,ORIGIN[1]+dy
    limits = DroneLimits(speed,8.,8.,0.,14.,True)
    lat,lon = GCS[int(abs(dy)//400)%3]
    gx,gy = lonlat_to_utm12n(lon,lat)
    radio = RadioSpec(frequency,2.,30.,2.,2.,-105.,lat,lon,gx,gy,5.)
    points = [point(x,y,alt,start),point(x+length,y,alt,start+length/(.85*speed))]
    plan = FlightPlan(pid,pid,2,'DRAFT',start,limits,radio,points,None)
    plan.tunnel = build_tunnel(pid,points,half,vertical,buffer)
    return plan


def shifted_point(wp, dx=0., dy=0., dz=0., epoch=None):
    return point(wp.x_m+dx,wp.y_m+dy,wp.alt_m+dz,wp.epoch_s if epoch is None else epoch)


def zone_request(pid, alt=60., start=EPOCH+120, frequency=915.):
    cx,cy = lonlat_to_utm12n(-111.18333333,50.26666667)
    a = point(cx-6200,cy,alt,start)
    b = point(cx+6200*math.cos(math.radians(245)),cy+6200*math.sin(math.radians(245)),alt,start)
    b.epoch_s = start+math.hypot(b.x_m-a.x_m,b.y_m-a.y_m)/(.85*35.)
    p = mission(pid,alt=alt,start=start,speed=35.,frequency=frequency,half=100.,vertical=30.)
    p.waypoints=[a,b]; p.tunnel=build_tunnel(pid,p.waypoints)
    return p


def imports(driver,name):
    plans=driver.window.ingest_crewed_file(data_dir()/'trl5'/name)
    driver.event('crewed_import',file=f'data/trl5/{name}',plans=[asdict(p) for p in plans])
    return plans


def weather(driver,name):
    obs=driver.window.ingest_metar_file(data_dir()/'trl5'/name)
    driver.event('weather_import',file=f'data/trl5/{name}',observations=[asdict(o) for o in obs])


def s1(d,r,**kwargs):
    crewed=imports(d,'s1_crewed.json'); before=[asdict(p) for p in crewed]
    d.screenshot('after_ingest')
    raw=zone_request('UAS-S1-01')
    records=d.check(raw); detections=[any(c.kind=='NO_FLY_ZONE' and c.plan_b_or_zone_id=='CYR231' for c in records)]
    d.approve(d.plan(raw))
    c=crewed[0]
    request=mission('UAS-S1-02',dy=2200,alt=c.waypoints[0].alt_m,start=EPOCH+120,speed=1.2,frequency=2422.)
    detections.append(any(c.kind=='SPACE_TIME' for c in d.check(request)))
    proposal=d.resolve()
    if proposal.modified_plan is None: raise AssertionError('Crewed request did not resolve')
    d.approve(proposal.modified_plan)
    # A long, separate link allocation keeps all automatic delay trials overlapping.
    request=mission('UAS-S1-03',dy=3500,start=EPOCH+200,length=1000.,speed=20.,frequency=2425.)
    records=d.check(request); detections.append(any(c.kind=='RADIO' for c in records))
    d.screenshot('rf_conflict')
    proposal=d.resolve()
    if proposal.modified_plan is None: raise AssertionError('RF request did not resolve')
    d.approve(proposal.modified_plan)
    r['metrics']['rf_resolution_action']=proposal.action_type
    target(r,'RF_ALLOCATION','RF interference resolves by channel reassignment','RADIO_CHANNEL_SHIFT',proposal.action_type,proposal.action_type=='RADIO_CHANNEL_SHIFT')
    weather(d,'highwind.txt')
    fourth=mission('UAS-S1-04',dy=5000,frequency=5805.)
    d.load(fourth); proposal=d.resolve()
    target(r,'OPERATOR','No solution escalates to an operator',True,proposal.requires_operator,proposal.requires_operator and proposal.modified_plan is None)
    d.window.record_operator_decision(fourth.plan_id,'Delay departure +360 s; require a covering calm METAR before approval')
    weather(d,'calm.txt')
    fourth.waypoints=[replace(w,epoch_s=w.epoch_s+360) for w in fourth.waypoints]; fourth.tunnel=build_tunnel(fourth.plan_id,fourth.waypoints,50.,15.,15.)
    d.approve(fourth)
    weather(d,'highwind.txt'); high=mission('UAS-S1-05',dy=6000,frequency=6200.)
    detections.append(any(c.kind=='WEATHER_WIND' for c in d.check(high)))
    started=time.perf_counter(); rejected=d.window.run_planner(); d.timings.append(time.perf_counter()-started)
    d.event('weather_rejected',plan_id=high.plan_id,status=rejected.status.value,wall_s=d.timings[-1])
    detections.append(rejected.plan is None and rejected.status.value=='REJECTED_WEATHER')
    weather(d,'stale.txt'); stale=mission('UAS-S1-06',dy=6500,frequency=6300.)
    detections.append(any(c.kind=='WEATHER_WIND' for c in d.check(stale)))
    started=time.perf_counter(); rejected=d.window.run_planner(); d.timings.append(time.perf_counter()-started)
    d.event('weather_rejected',plan_id=stale.plan_id,status=rejected.status.value,wall_s=d.timings[-1])
    detections.append(rejected.plan is None and rejected.status.value=='REJECTED_WEATHER')
    weather(d,'calm.txt')
    target(r,'DETECTION','Zone, crewed, RF, gust and stale-weather checks and planner rejection', '100%',dict(detected=sum(detections),planted=len(detections)),all(detections))
    target(r,'CREWED_IMMUTABLE','Crewed records unchanged',True,[asdict(p) for p in d.window.active() if p.is_crewed]==before,[asdict(p) for p in d.window.active() if p.is_crewed]==before)
    approved=[p for p in d.window.active() if not p.is_crewed]
    target(r,'APPROVED','Four accepted requests',4,len(approved),len(approved)==4)
    d.screenshot('approved_tunnels')


def s2(d,r,**kwargs):
    imports(d,'s2_crewed.json'); crew_before=[asdict(p) for p in d.window.active() if p.is_crewed]
    planted=[]; detected=[]; timings=[]
    first=None
    for i in range(16):
        started=time.perf_counter()
        if i>=14:
            request=zone_request(f'UAS-S2-{i+1:02}',alt=200.+200*(i-14),frequency=2400.)
        else:
            request=mission(f'UAS-S2-{i+1:02}',dy=i*400.,start=EPOCH+120,frequency=2400.,length=1000.)
        raw=request
        if first is not None and i<14:
            # A proposed intermediate transit through the first departure pad is unsafe.
            raw=replace(request,waypoints=[request.waypoints[0],replace(first.waypoints[0],epoch_s=EPOCH+125),request.waypoints[-1]])
            raw.tunnel=build_tunnel(raw.plan_id,raw.waypoints,50.,15.,15.)
        records=d.check(raw)
        expected=[]
        for other in d.window.active():
            if any(x['hit'] for x in evaluate_radio(raw,other)): expected.append(('RADIO',other.plan_id))
            if sample_space_time(raw.waypoints,other.waypoints,max(100.,raw.tunnel.horiz_half_width_m+(other.tunnel.horiz_half_width_m if other.tunnel else 0)),max(30.,raw.tunnel.vert_margin_m+(other.tunnel.vert_margin_m if other.tunnel else 0)))['hit']:
                expected.append(('SPACE_TIME',other.plan_id))
        if i>=14: expected.append(('NO_FLY_ZONE','CYR231'))
        for kind,other in expected:
            planted.append([raw.plan_id,kind,other]);detected.append(any(c.kind==kind and c.plan_b_or_zone_id==other for c in records))
        # Operator selects a separated channel; A* removes unsafe intermediate transits.
        request.radio=replace(request.radio,freq_mhz=2400.+40*i)
        d.window.record_operator_decision(request.plan_id,f'Allocate {request.radio.freq_mhz} MHz and plan between submitted endpoints')
        planned=d.plan(request,objective='avoid_radio' if i==1 else 'shortest_time')
        stored=d.approve(planned)
        if first is None: first=stored
        timings.append(time.perf_counter()-started)
    active=d.window.active(); uas=[p for p in active if not p.is_crewed]
    common_start=max(p.waypoints[0].epoch_s for p in active); common_end=min(p.waypoints[-1].epoch_s for p in active)
    r['metrics'].update(planted_conflicts=planted,per_plan_wall_s=timings,simultaneous_overlap_s=common_end-common_start)
    target(r,'DETECTION','All independently planted conflicts detected; at least 14','100%, >=14',dict(planted=len(planted),detected=sum(detected)),len(planted)>=14 and all(detected))
    target(r,'SIMULTANEOUS','16 drones and two crewed plans have a common active interval','16+2',dict(drones=len(uas),crewed=len(active)-len(uas),overlap_s=common_end-common_start),len(uas)==16 and len(active)==18 and common_end>common_start)
    target(r,'LATENCY','Planning and allocation per plan, max <=5 s and p95 <=3 s','max <=5, p95 <=3',dict(max_s=max(timings),p95_s=float(np.percentile(timings,95))),max(timings)<=5 and np.percentile(timings,95)<=3)
    target(r,'CREWED_IMMUTABLE','Crewed records unchanged',True,[asdict(p) for p in active if p.is_crewed]==crew_before,[asdict(p) for p in active if p.is_crewed]==crew_before)
    d.screenshot('swarm_16_map')


def start_udp(d,plans,known_count=None,sysids=None):
    panel=d.window.live_panel; panel.start()
    drones=[]
    for i,p in enumerate(plans):
        drone=SimulatedDrone(panel.receiver.address,d.clock,sysid=(sysids[i] if sysids else i+1))
        drones.append(drone)
        if known_count is None or i<known_count:
            panel.mapping.setText(f'{drone.address[1]}, {drone.sysid}, 1, {p.plan_id}'); panel.map_id()
    d.event('udp_started',receiver=panel.receiver.address,senders=[dict(address=x.address,sysid=x.sysid) for x in drones])
    return drones


def stream(d,drones,plans,duration,transform=None,drop=None):
    count=round(duration/.5)
    start=plans[0].waypoints[0].epoch_s
    sent=[0]*len(drones); dropped=[0]*len(drones)
    try:
        for index in range(count):
            due=start+index*.5
            d.pump(max(0.,due-d.clock()))
            for j,(drone,plan) in enumerate(zip(drones,plans)):
                wp=interpolate(plan,due)
                if transform: wp=transform(j,index,wp,due)
                if drop and drop(j,index):
                    dropped[j]+=1; d.event('seeded_packet_drop',drone=j,report_index=index,nominal_epoch_s=due)
                    continue
                drone.send(wp);sent[j]+=1
            d.pump(.06)
        d.pump(.06)
    finally:
        for drone in drones: drone.close()
    d.event('udp_finished',sent=sent,dropped=dropped,report_interval_s=.5)
    return sent,dropped


def s3(d,r,live_duration=30.,**kwargs):
    start=d.clock()+.5
    ys=[i*400. for i in range(10)]+[4500.,4700.]
    plans=[d.approve(mission(f'PLAN-S3-{i+1:02}',dy=y,start=start,frequency=2400+40*i)) for i,y in enumerate(ys)]
    drones=start_udp(d,plans,8,[1,2,3,4,5,6,7,8,109,110,111,112])
    keys=[(drone.address,drone.sysid,1) for drone in drones]
    def transform(j,index,wp,epoch):
        return shifted_point(wp,dy=100. if j==10 else -100. if j==11 else 0.)
    sent,dropped=stream(d,drones,plans,live_duration,transform)
    histories=[[x for x in d.window.live_panel.report_history if x.key==key] for key in keys]
    known=[bool(h) and all(x.status==TrackMatchStatus.MATCHED_KNOWN_ID and x.plan_id==p.plan_id for x in h) for h,p in zip(histories[:8],plans[:8])]
    unknown=[len(h)>=5 and all(x.status==TrackMatchStatus.UNMATCHED and x.plan_id is None for x in h[:4]) and all(x.status==TrackMatchStatus.MATCHED_TRAJECTORY and x.plan_id==p.plan_id for x in h[4:]) for h,p in zip(histories[8:10],plans[8:10])]
    ambiguous=[len(h)>=5 and all(x.status==TrackMatchStatus.AMBIGUOUS and x.plan_id is None for x in h[4:]) for h in histories[10:]]
    r['metrics'].update(udp_senders=12,sent_positions=sum(sent),received_positions=sum(map(len,histories)),flight_duration_s=live_duration,
        confusion_table=[dict(sysid=key[1],expected=plans[i].plan_id if i<10 else 'AMBIGUOUS',reports=len(histories[i]),fifth_status=histories[i][4].status.value if len(histories[i])>=5 else None) for i,key in enumerate(keys)])
    target(r,'KNOWN_ID','All eight known tracks match on first and subsequent reports','100%',dict(correct=sum(known),total=8),all(known))
    target(r,'UNKNOWN_K5','Both unknown tracks match by K=5 without false association','2/2',sum(unknown),all(unknown))
    target(r,'AMBIGUOUS','Both ambiguous tracks abstain after K=5','2/2',sum(ambiguous),all(ambiguous))
    target(r,'UDP_12','Twelve simultaneous independent UDP sockets; all sent positions received',sum(sent),sum(map(len,histories)),len(set(k[0] for k in keys))==12 and sum(map(len,histories))==sum(sent))
    target(r,'NOMINAL','No drift alerts on ten nominal tracks',0,sum(x.drift for h in histories[:10] for x in h),not any(x.drift for h in histories[:10] for x in h))
    d.screenshot('live_panel_matching')


def s4(d,r,**kwargs):
    start=d.clock()+.5
    plans=[d.approve(mission(f'PLAN-S4-{chr(65+i)}',dy=i*600.,alt=60.,start=start,frequency=2400+40*i)) for i in range(5)]
    drones=start_udp(d,plans)
    keys=[(x.address,x.sysid,1) for x in drones]
    crossing={1:40,2:42,3:48,4:40}
    # Exactly nine of ninety position datagrams are dropped, including the first exit.
    rng=random.Random(SEED); drops=set(rng.sample([i for i in range(90) if i not in (39,40,41,42)],8))|{40}
    def transform(j,index,wp,epoch):
        if j in (1,4) and index>=crossing[j]: return shifted_point(wp,dy=85.)
        if j==2 and index>=crossing[j]: return shifted_point(wp,dz=30.)
        if j==3 and index>=crossing[j]: return interpolate(plans[j],epoch-20.)
        return wp
    sent,dropped=stream(d,drones,plans,45.,transform,lambda j,i:j==4 and i in drops)
    histories=[[x for x in d.window.live_panel.report_history if x.key==key] for key in keys]
    target(r,'FALSE_ALERTS','Nominal track remains conforming',0,sum(x.drift for x in histories[0]),len(histories[0])==90 and not any(x.outside for x in histories[0]))
    intervals={};types={1:'LATERAL',2:'VERTICAL',3:'TEMPORAL',4:'LATERAL'}
    for j in range(1,5):
        alerts=[x for x in histories[j] if x.drift]
        if alerts:
            # Nominal transmitted report indices, including deliberate drops.
            delay=round((alerts[0].waypoint.epoch_s-start)/.5)-crossing[j]+1
            intervals[plans[j].plan_id]=delay
            correct=alerts[0].violation_type==types[j]
        else: delay=None;correct=False
        target(r,f'EXIT_{j}',f'{types[j]} alert within {3 if j==4 else 2} report intervals',3 if j==4 else 2,delay,correct and delay is not None and 0<delay<=(3 if j==4 else 2))
    r['metrics'].update(detection_report_intervals=intervals,loss_sent=sent[4],loss_dropped=dropped[4],loss_fraction=dropped[4]/90.,seeded_dropped_indices=sorted(drops))
    target(r,'LOSS','Seeded outgoing packet loss is exactly 10%',.1,dropped[4]/90.,dropped[4]==9)
    d.screenshot('conformance_alerts')


def s5(d,r,**kwargs):
    start=d.clock()+.5
    a=mission('UAS-S5-01',dy=3000.,start=start,frequency=2400.,length=800.)
    b=mission('UAS-S5-02',dx=2000.,start=EPOCH+1,alt=70.,frequency=2440.,length=1000.)
    b.waypoints[-1]=point(b.waypoints[0].x_m,b.waypoints[0].y_m+1000.,70.,EPOCH+1+1000/17.)
    b.tunnel=build_tunnel(b.plan_id,b.waypoints,50.,15.,15.)
    c=mission('UAS-S5-03',dx=4000.,start=start,alt=70.,frequency=2480.)
    plans=[d.approve(p) for p in (a,b,c)];drones=start_udp(d,plans)
    keys=[(x.address,x.sysid,1) for x in drones]
    panel=d.window.live_panel
    try:
        for index in range(3):
            d.pump(max(0.,start+index*.5-d.clock()))
            for j,(drone,p) in enumerate(zip(drones,plans)):
                wp=interpolate(p,d.clock());drone.send(shifted_point(wp,dy=85. if j==0 else 0.))
            d.pump(.08)
        target(r,'DRIFT','Drift alert received before re-route',True,panel.reports[keys[0]].drift,panel.reports[keys[0]].drift)
        drift_reports=[x for x in panel.report_history if x.key==keys[0] and x.outside]
        first_alert=next((i+1 for i,x in enumerate(drift_reports) if x.drift),None)
        target(r,'DRIFT_INTERVALS','Lateral drift detected within two reports',2,first_alert,first_alert is not None and first_alert<=2 and drift_reports[first_alert-1].violation_type=='LATERAL')
        result,elapsed=d.reroute(keys[0]);a2=d.accept()
        imports(d,'s5_popup.json'); crew_before=[asdict(p) for p in d.window.active() if p.is_crewed]
        d.load(plans[1]); conflicts=d.window.check_candidate()
        target(r,'POPUP','Pop-up crewed conflict detected',True,any(c.kind=='SPACE_TIME' for c in conflicts),any(c.kind=='SPACE_TIME' for c in conflicts))
        d.screenshot('popup_conflict')
        result,elapsed=d.reroute(keys[1]);b2=d.accept()
        recovered=[]
        for drone,key,p in zip(drones[:2],keys[:2],(a2,b2)):
            for index in range(2):
                drone.send(interpolate(p,d.clock()));d.pump(.5)
            recovered.append(not panel.reports[key].outside)
        target(r,'RECOVERY','Both accepted re-routes conform within two updates','2/2',sum(recovered),all(recovered))
        d.screenshot('reroute_accepted')
        imports(d,'s5_box.json')
        drones[2].send(interpolate(plans[2],d.clock()));d.pump(.08)
        # Box-in occupies the live start, so no safe outgoing edge can be committed.
        result,elapsed=d.reroute(keys[2])
        target(r,'NO_SOLUTION','Box-in returns no path within five seconds','no plan, <=5 s',dict(status=result.status.value,wall_s=elapsed),result.plan is None and elapsed<=5.)
        if result.plan is None: panel.hold_land()
        target(r,'OPERATOR','Operator hold/land decision recorded; no unsafe replacement',1,d.window.conn.execute('SELECT count(*) FROM operator_decisions').fetchone()[0],d.window.conn.execute('SELECT count(*) FROM operator_decisions').fetchone()[0]==1 and all(p.plan_id!=plans[2].plan_id for p in d.window.active()))
        target(r,'SUPERSEDED','Two accepted old reservations remain as superseded history',2,d.window.conn.execute("SELECT count(*) FROM flight_plans WHERE status='SUPERSEDED' AND plan_id IN ('UAS-S5-01','UAS-S5-02')").fetchone()[0],d.window.conn.execute("SELECT count(*) FROM flight_plans WHERE status='SUPERSEDED' AND plan_id IN ('UAS-S5-01','UAS-S5-02')").fetchone()[0]==2)
        after=[asdict(p) for p in d.window.active() if p.plan_id=='CREWED-POPUP-501']
        target(r,'CREWED_IMMUTABLE','Pop-up crewed plan unchanged',True,after==crew_before,after==crew_before)
        d.screenshot('operator_escalation')
        arrivals=[]
        while d.clock()<max(a2.waypoints[-1].epoch_s,b2.waypoints[-1].epoch_s)+.5:
            for drone,p in zip(drones[:2],(a2,b2)):
                drone.send(interpolate(p,d.clock()))
            d.pump(.5)
        for key,p in zip(keys[:2],(a2,b2)):
            report=panel.reports[key]
            arrivals.append(math.hypot(report.waypoint.x_m-p.waypoints[-1].x_m,report.waypoint.y_m-p.waypoints[-1].y_m)<=15. and not report.outside)
        target(r,'ARRIVAL','Both simulated drones fly the accepted route to within 15 m','2/2',sum(arrivals),all(arrivals))
    finally:
        for drone in drones: drone.close()

SCENARIOS=dict(S1=s1,S2=s2,S3=s3,S4=s4,S5=s5)
