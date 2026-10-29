"""Linux-only external process harness. No flight or telemetry libraries are bundled."""
import hashlib
import importlib.util
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import tempfile
import time
from .scenarios import mission, point, target
from ..live import interpolate
from ..tunnel import build_tunnel



def _version_summary(version_file):
    """Keep only the upstream commit hash and version name from git-version.txt."""
    if not version_file.exists():
        return None
    keep=[line.strip() for line in version_file.read_text(encoding='utf-8',errors='replace').splitlines()
          if line.startswith('commit ') or line.startswith('APMVERSION:')]
    return '\n'.join(keep) or None

def availability(directory):
    if platform.system()!='Linux': return 'NOT_APPLICABLE','External SITL campaign runs on Linux only'
    folder=Path(directory or '/tmp/ardupilot-sitl')
    if not (folder/'arducopter').is_file() or not (folder/'copter.parm').is_file():
        return 'NOT_RUN','SITL binary or copter.parm unavailable'
    if importlib.util.find_spec('pymavlink') is None: return 'NOT_RUN','Test-only pymavlink unavailable'
    return None,None


def run_sitl(d,r,directory):
    # Imported only inside the external Linux test harness, never the desktop runtime.
    from pymavlink import mavutil
    import importlib.metadata
    folder=Path(directory or '/tmp/ardupilot-sitl').resolve(); binary=folder/'arducopter'
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    version_file=folder/'git-version.txt'
    r['metrics'].update(sitl_sha256=digest,sitl_git_version=_version_summary(version_file),
        pymavlink_version=importlib.metadata.version('pymavlink'),sitl_speedup=1,hard_cap_wall_s=300.)
    began=time.perf_counter(); panel=d.window.live_panel;panel.start()
    process=None; link=None; logfile=d.root/'events'/f'{d.id}_sitl_stdout.log'
    r['sitl_stdout_log']=str(logfile.relative_to(d.root))
    telemetry={}; version=None; system_id=1; component_id=1
    with tempfile.TemporaryDirectory(prefix='minerva_sitl_') as temporary, logfile.open('w',encoding='utf-8') as output:
        temp=Path(temporary); extra=temp/'campaign.parm'
        params=['SERIAL1_PROTOCOL 2','TERRAIN_ENABLE 0','WPNAV_SPEED 2000','WPNAV_ACCEL 500','WPNAV_SPEED_UP 500','WPNAV_SPEED_DN 500','PILOT_SPEED_UP 500']
        for n in (1,2,3):
            for group in ('POSITION','RAW_SENS','EXT_STAT','RC_CHAN','RAW_CTRL','EXTRA1','EXTRA2','EXTRA3','PARAMS','ADSB'):
                params.append(f'MAV{n}_{group} {5 if group=="POSITION" else 0}')
        extra.write_text('\n'.join(params)+'\n')
        home=mission('home').waypoints[0]
        args=[str(binary),'--model','+','--speedup','1','--home',f'{home.lat_deg},{home.lon_deg},750,0','--defaults',f'{folder/"copter.parm"},{extra}','-w','--serial1',f'udpclient:127.0.0.1:{panel.receiver.address[1]}']
        d.event('sitl_launch',arguments=args,sha256=digest,extra_parameters=params)
        try:
            process=subprocess.Popen(args,cwd=temp,stdout=output,stderr=subprocess.STDOUT)
            def check_cap():
                if time.perf_counter()-began>=300: raise TimeoutError('SITL scenario exceeded 300 s hard cap')
                if process.poll() is not None: raise RuntimeError(f'SITL exited {process.returncode}')
            def pump(seconds=.05):
                nonlocal version,system_id,component_id
                end=time.perf_counter()+seconds
                while True:
                    check_cap();d.pump(.005)
                    if link:
                        for _ in range(300):
                            msg=link.recv_match(blocking=False)
                            if msg is None: break
                            kind=msg.get_type();telemetry[kind]=msg
                            if kind=='HEARTBEAT': system_id=msg.get_srcSystem();component_id=msg.get_srcComponent()
                            if kind=='STATUSTEXT':
                                text=msg.text
                                if 'ArduCopter' in text: version=text
                                d.event('sitl_status',text=text)
                    if time.perf_counter()>=end:break
            deadline=time.perf_counter()+10
            while link is None:
                check_cap()
                try: link=mavutil.mavlink_connection('tcp:127.0.0.1:5760',retries=1,source_system=255)
                except (OSError,ConnectionError):
                    if time.perf_counter()>deadline: raise
                    d.pump(.1)
            while 'HEARTBEAT' not in telemetry:pump(.1)
            # Request version as independent provenance, in addition to the binary hash.
            link.mav.command_long_send(system_id,component_id,mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,0,148,0,0,0,0,0,0)
            arm_deadline=time.perf_counter()+90;retry=0.
            while not link.motors_armed():
                if time.perf_counter()>arm_deadline: raise TimeoutError('GUIDED arming did not settle within 90 s')
                if time.perf_counter()>=retry:
                    link.set_mode('GUIDED');link.arducopter_arm();retry=time.perf_counter()+2
                pump(.1)
            d.event('sitl_armed',startup_wall_s=time.perf_counter()-began)
            link.mav.command_long_send(system_id,component_id,mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,0,0,0,0,0,0,0,40.)
            takeoff_deadline=time.perf_counter()+40
            while telemetry.get('GLOBAL_POSITION_INT') is None or telemetry['GLOBAL_POSITION_INT'].relative_alt<38000:
                if time.perf_counter()>takeoff_deadline: raise TimeoutError('Takeoff failed to reach 38 m AGL')
                pump(.1)
            # Build and approve a timed northbound mission after climb is established.
            gp=telemetry['GLOBAL_POSITION_INT']
            from ..coords import lonlat_to_utm12n
            x,y=lonlat_to_utm12n(gp.lon/1e7,gp.lat/1e7)
            start=d.clock()+.5
            plan=mission('PLAN-S6-SITL',alt=40.,start=start,speed=10./.85,half=50.,vertical=15.,buffer=30.)
            plan.waypoints=[point(x,y,40.,start),point(x,y+650,40.,start+65.)]
            plan.tunnel=build_tunnel(plan.plan_id,plan.waypoints,50.,15.,30.)
            plan=d.approve(plan)
            # Discover the exact source socket used by the separate simulator.
            while not panel.reports:pump(.1)
            key=next(k for k in panel.reports if k[1]==1 and k[2]==1)
            panel.mapping.setText(f'{key[0][1]}, 1, 1, {plan.plan_id}');panel.map_id()
            def send_target(wp):
                link.mav.set_position_target_global_int_send(0,system_id,component_id,
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,0b110111111000,
                    round(wp.lat_deg*1e7),round(wp.lon_deg*1e7),wp.alt_m,0,0,0,0,0,0,0,0)
            def guide(active,seconds):
                end=time.perf_counter()+seconds
                while time.perf_counter()<end:
                    send_target(interpolate(active,d.clock()+1.5));pump(.1)
            nominal_index=len(panel.report_history)
            guide(plan,20.)
            nominal=[a for a in panel.report_history[nominal_index:] if a.key==key]
            target(r,'KNOWN_ID','Every monitored SITL report matches the mapped ID','100%',dict(matched=sum(a.plan_id==plan.plan_id and a.status.value=='MATCHED_KNOWN_ID' for a in nominal),reports=len(nominal)),bool(nominal) and all(a.plan_id==plan.plan_id and a.status.value=='MATCHED_KNOWN_ID' for a in nominal))
            target(r,'NOMINAL','Every monitored nominal report conforms','100%',dict(conforming=sum(not a.outside for a in nominal),reports=len(nominal)),bool(nominal) and all(not a.outside for a in nominal))
            d.screenshot('sitl_conforming')
            # Off-plan command is held until the real vehicle exits its clearance.
            current=panel.reports[key].waypoint
            deviation=point(current.x_m+120.,current.y_m,40.,d.clock())
            deviation_start=len(panel.report_history);drift_deadline=time.perf_counter()+30
            while not panel.reports[key].drift:
                if time.perf_counter()>drift_deadline:raise TimeoutError('Injected SITL deviation was not detected')
                send_target(deviation);pump(.1)
            exits=[a for a in panel.report_history[deviation_start:] if a.key==key and a.outside]
            first_drift=next(i+1 for i,a in enumerate(exits) if a.drift)
            target(r,'DRIFT_INTERVALS','Lateral exit flagged within two received position reports',2,first_drift,first_drift<=2 and exits[first_drift-1].violation_type=='LATERAL')
            d.screenshot('sitl_drift_alert')
            old_revision=d.window.conn.execute('SELECT revision FROM db_state_meta').fetchone()[0]
            result,elapsed=d.reroute(key)
            if result.plan is None:raise AssertionError('SITL re-route has no solution')
            newplan=d.accept()
            new_revision=d.window.conn.execute('SELECT revision FROM db_state_meta').fetchone()[0]
            target(r,'REVISION','Re-route atomically supersedes original at next DB revision',old_revision+1,new_revision,new_revision==old_revision+1 and d.window.conn.execute('SELECT status FROM flight_plans WHERE plan_id=?',(plan.plan_id,)).fetchone()[0]=='SUPERSEDED')
            recovery_start=len(panel.report_history)
            guide(newplan,1.)
            recovery=[a for a in panel.report_history[recovery_start:] if a.key==key]
            target(r,'RECOVERY','Conformance returns within two reports',2,next((i+1 for i,a in enumerate(recovery) if not a.outside),None),any(not a.outside for a in recovery[:2]))
            arrival_distance=math.inf
            while True:
                latest=panel.reports[key]
                goal=newplan.waypoints[-1]
                arrival_distance=math.hypot(latest.waypoint.x_m-goal.x_m,latest.waypoint.y_m-goal.y_m)
                if d.clock()>=goal.epoch_s and arrival_distance<=15. and not latest.outside:break
                if d.clock()>goal.epoch_s+30:raise TimeoutError(f'SITL arrival failed, {arrival_distance:.1f} m from goal')
                guide(newplan,.2)
            d.screenshot('sitl_rerouted')
            flight=[a for a in panel.report_history[nominal_index:] if a.key==key]
            target(r,'ALL_KNOWN_ID','Known-ID match across nominal, deviation and recovery','100%',dict(matched=sum(a.status.value=='MATCHED_KNOWN_ID' for a in flight),reports=len(flight)),bool(flight) and all(a.status.value=='MATCHED_KNOWN_ID' for a in flight))
            wall=time.perf_counter()-began
            target(r,'ARRIVAL','Arrival within 15 m and campaign hard cap','<=15 m, <=300 s',dict(distance_m=arrival_distance,wall_s=wall),arrival_distance<=15. and wall<=300.)
            av=telemetry.get('AUTOPILOT_VERSION')
            r['metrics'].update(sitl_version_text=version,sitl_flight_sw_version=av.flight_sw_version if av else None,
                sitl_custom_version=bytes(av.flight_custom_version).hex() if av else None,
                sitl_flight_wall_s=wall,arrival_distance_m=arrival_distance,nominal_reports=len(nominal),
                sitl_position_reports=len(flight),ignored_other_message_ids=panel.tracker.parser_statistics.get('ignored_other_message_ids',0),
                unparsed_or_invalid_frames=panel.tracker.dropped_frames-panel.tracker.parser_statistics.get('ignored_other_message_ids',0))
            if av:
                number=av.flight_sw_version
                r['metrics']['sitl_version']=f'{number>>24}.{(number>>16)&255}.{(number>>8)&255} (type {number&255})'
                r['metrics']['sitl_commit_prefix']=bytes(av.flight_custom_version).decode('ascii',errors='replace').rstrip('\0')
            target(r,'PROVENANCE','External version and binary SHA-256 are recorded','version + SHA-256',dict(version=r['metrics'].get('sitl_version'),sha256=digest),bool(r['metrics'].get('sitl_version')) and len(digest)==64)
            d.event('sitl_completed',**r['metrics'])
        finally:
            if link:link.close()
            if process and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            if version:r['metrics']['sitl_version_text']=version
