"""Run independent, measured scenarios against the desktop application."""
import os
from pathlib import Path
import time
import traceback
import numpy as np
from .scenarios import EPOCH, SEED, IDS, SCENARIOS, target
from .report_writer import environment, provenance, write_reports, LIMITS


def run_campaign(report_dir, scenarios=None, require_sitl=False, sitl_dir=None, live_duration=30.):
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from .gui_driver import GuiDriver
    from .oracle_audit import audit
    selected=list(scenarios or IDS)
    invalid=set(selected)-set(IDS)
    if invalid: raise ValueError('Unknown scenario IDs: '+','.join(sorted(invalid)))
    if require_sitl and 'S6' not in selected: selected.append('S6')
    root=Path(report_dir); root.mkdir(parents=True,exist_ok=True)
    report=dict(schema_version='1.0.0',campaign='MINERVA_TRL5_VALIDATION',author='Arpan Bom',
        statement='Simulation only; never flown.',seed=SEED,environment=environment(),**provenance(),
        limits=LIMITS,scenarios=[],selected_scenarios=selected)
    for sid in selected:
        started=time.perf_counter()
        result=dict(scenario_id=IDS[sid],status='FAIL',wall_time_s=0.,targets=[],metrics={},screenshots=[],event_log=f'events/{IDS[sid]}.jsonl',sqlite_db=f'db/{IDS[sid]}.sqlite3')
        print(f'{sid}: running',flush=True)
        driver=None
        try:
            if sid=='S6':
                from .sitl_harness import availability, run_sitl
                status,reason=availability(sitl_dir)
                if status:
                    result.update(status=status,reason=reason)
                    (root/'events').mkdir(exist_ok=True)
                    import json
                    (root/result['event_log']).write_text(json.dumps(dict(event='scenario_unavailable',status=status,reason=reason))+'\n',encoding='utf-8')
                    result['sqlite_db']=None
                else:
                    driver=GuiDriver(root,IDS[sid],EPOCH)
                    run_sitl(driver,result,sitl_dir)
            else:
                driver=GuiDriver(root,IDS[sid],EPOCH)
                SCENARIOS[sid](driver,result,live_duration=live_duration)
        except Exception:
            result['error']=traceback.format_exc()
            target(result,'EXECUTION','Scenario executes without an exception',True,result['error'],False)
            if driver: driver.event('exception',traceback=result['error'])
        finally:
            if driver:
                try:
                    if driver.timings:
                        times=driver.timings
                        result['metrics'].update(planner_max_wall_s=max(times),planner_p95_wall_s=float(np.percentile(times,95)),planner_wall_s=times)
                        target(result,'COMPUTE','Every measured planner/re-route call <=5 s',5.,max(times),max(times)<=5.)
                    if driver.latencies:
                        lat=driver.latencies
                        result['metrics'].update(receive_to_gui_max_s=max(lat),receive_to_gui_p95_s=float(np.percentile(lat,95)),receive_to_gui_s=lat)
                        target(result,'RECEIVE_LATENCY','Receive-to-GUI latency max <=1 s and p95 <=0.25 s','max <=1, p95 <=0.25',dict(max_s=max(lat),p95_s=float(np.percentile(lat,95))),max(lat)<=1. and np.percentile(lat,95)<=.25)
                    alerts=driver.alert_latencies
                    result['metrics'].update(receive_to_alert_s=alerts,receive_to_alert_max_s=max(alerts) if alerts else None,
                                              receive_to_alert_p95_s=float(np.percentile(alerts,95)) if alerts else None)
                    if alerts:
                        target(result,'ALERT_LATENCY','New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s','max <=1, p95 <=0.25',dict(alerts=len(alerts),max_s=max(alerts),p95_s=float(np.percentile(alerts,95))),max(alerts)<=1. and np.percentile(alerts,95)<=.25)
                    audited=audit(driver);result['metrics'].update(audited)
                    target(result,'INDEPENDENT_AUDIT','Independent flight-limit, zone, space/time and RF audit has no residual conflicts',0,dict(residual=audited['oracle_residual_conflicts'],errors=audited['validation_errors']),not audited['validation_errors'] and audited['oracle_residual_conflicts']==0)
                    target(result,'FALSE_CONFLICTS','No conflicts reported on the independently clean approved set',0,len(audited['deconflicted_checker_conflicts']),not audited['deconflicted_checker_conflicts'] and not audited['validation_errors'])
                    target(result,'CONTAINMENT','Nominal paths are contained in their tunnels','100%',audited['tunnel_containment_percent'],audited['tunnel_containment_percent']==100.)
                    target(result,'CLEARANCE','Every active start, goal and GCS is >=500 m outside every zone',500.,audited['minimum_site_clearance_m'],audited['minimum_site_clearance_m']>=500.)
                    target(result,'RELOAD','All active fields and DB revision survive application close/reopen',True,audited['db_reload_exact_match'],audited['db_reload_exact_match'])
                    driver.screenshot('reloaded')
                except Exception:
                    result['audit_error']=traceback.format_exc()
                    target(result,'AUDIT_EXECUTION','Independent audit completes',True,result['audit_error'],False)
                finally:
                    result['screenshots']=driver.screenshots
                    driver.close()
                result['status']='PASS' if result['targets'] and all(t['passed'] for t in result['targets']) else 'FAIL'
            result['wall_time_s']=time.perf_counter()-started
            report['scenarios'].append(result)
            print(f"{sid}: {result['status']} ({result['wall_time_s']:.2f} s)",flush=True)
            for t in result['targets']:
                if not t['passed']: print('  FAILED '+t['target_id']+': '+str(t['measured']),flush=True)
    counts={status:sum(s['status']==status for s in report['scenarios']) for status in ('PASS','FAIL','NOT_RUN','NOT_APPLICABLE')}
    report['summary_counts']=dict(total_scenarios=len(selected),passed=counts['PASS'],failed=counts['FAIL'],not_run=counts['NOT_RUN'],not_applicable=counts['NOT_APPLICABLE'])
    failed=[s['scenario_id'] for s in report['scenarios'] if s['status'] not in ('PASS','NOT_APPLICABLE')]
    report['overall_status']='FAIL' if failed else 'PASS'
    report['verdict_line']='TRL 5 validation FAILED: '+','.join(failed) if failed else 'All TRL 5 scenario targets met'
    trace={'EO1':['S1','S2','S3','S4','S5'],'EO2':['S1','S2','S6'],'EO3':['S1','S2','S5','S6'],'EO4':['S1','S2','S5'],'EO5':['S1','S2','S5','S6'],'EO6':['S1','S2','S5'],'EO7':list(IDS),'X1':['S4','S5','S6'],'X2':['S3','S4','S5','S6']}
    report['outcome_traceability']={}
    for outcome,ids in trace.items():
        relevant=[s for s in report['scenarios'] if s['scenario_id'].split('_')[0] in ids and s['status']!='NOT_APPLICABLE']
        status='FAIL' if any(s['status']!='PASS' for s in relevant) else 'PASS' if set(ids).issubset(set(selected)) else 'NOT_FULLY_EVALUATED'
        report['outcome_traceability'][outcome]=dict(status=status,scenarios=ids)
    write_reports(root,report)
    print(report['verdict_line'],flush=True)
    return 2 if require_sitl and counts['NOT_RUN'] else 1 if failed else 0
