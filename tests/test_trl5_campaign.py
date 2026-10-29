"""Fast integrated campaign coverage. External SITL is exercised by its CLI job."""
import json
from pathlib import Path
import sqlite3
from minerva.trl5.runner import run_campaign
from minerva.trl5.scenarios import IDS


def test_ingest_and_short_live_campaign(qapp,tmp_path):
    code=run_campaign(tmp_path,['S1','S3'],live_duration=3.)
    report=json.loads((tmp_path/'report.json').read_text())
    assert code==0, (tmp_path/'report.md').read_text()
    assert report['schema_version']=='1.0.0'
    assert report['author']=='Arpan Bom'
    assert report['statement']=='Simulation only; never flown.'
    assert report['git_commit_sha'] and report['generated_at_utc'].endswith('Z')
    assert report['environment']['cpu_count']>0
    assert report['environment']['package_versions']['shapely']=='2.2.0'
    assert report['seed']==20261118
    assert report['summary_counts']['passed']==2
    assert report['selected_scenarios']==['S1','S3']
    assert report['outcome_traceability']['EO1']['status']=='NOT_FULLY_EVALUATED'
    assert report['overall_status']=='PASS'
    assert report['verdict_line']=='All TRL 5 scenario targets met'
    for scenario in report['scenarios']:
        assert scenario['status']=='PASS'
        assert scenario['targets'] and all(t['passed'] for t in scenario['targets'])
        assert scenario['wall_time_s']>0
        metrics=scenario['metrics']
        assert metrics['oracle_residual_conflicts']==0
        assert metrics['validation_errors']=={}
        assert metrics['oracle_samples']>0
        assert metrics['max_relative_step_m']<=1.000000001
        assert metrics['tunnel_containment_percent']==100.
        assert metrics['minimum_site_clearance_m']>=500.
        assert metrics['db_reload_exact_match'] is True
        assert metrics['deconflicted_checker_conflicts']==[]
        database=tmp_path/scenario['sqlite_db']
        assert database.is_file() and database.stat().st_size>0
        with sqlite3.connect(database) as conn:
            assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert conn.execute('SELECT count(*) FROM tunnels_4d').fetchone()[0]==metrics['approved_count']
        assert len(scenario['screenshots'])>=2
        for name in scenario['screenshots']:
            data=(tmp_path/name).read_bytes()
            assert data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>1000
        events=[json.loads(line) for line in (tmp_path/scenario['event_log']).read_text().splitlines()]
        assert any(e['event']=='reloaded' and e['equal'] for e in events)
    s1,s3=report['scenarios']
    assert s1['metrics']['rf_resolution_action']=='RADIO_CHANNEL_SHIFT'
    assert s1['metrics']['approved_count']==4
    assert 0<s1['metrics']['planner_max_wall_s']<=5.
    live=s3['metrics']
    assert live['udp_senders']==12
    assert live['sent_positions']==live['received_positions']==72
    assert 0<live['receive_to_gui_max_s']<=1.
    assert 0<live['receive_to_gui_p95_s']<=.25
    assert live['receive_to_alert_s']==[]
    assert live['receive_to_alert_max_s'] is None
    assert len(live['receive_to_gui_s'])==72
    assert all(row['reports']==6 for row in live['confusion_table'])
    assert [row['fifth_status'] for row in live['confusion_table'][-4:]]==['MATCHED_TRAJECTORY','MATCHED_TRAJECTORY','AMBIGUOUS','AMBIGUOUS']
    html=(tmp_path/'report.html').read_text()
    assert 'data:image/png;base64,' in html
    assert 'Simulation only; never flown.' in html
    assert all(limit in (tmp_path/'report.md').read_text() for limit in report['limits'])


def test_missing_sitl_is_not_a_pass(tmp_path,monkeypatch):
    from minerva.trl5 import sitl_harness
    monkeypatch.setattr(sitl_harness.platform,'system',lambda:'Linux')
    code=run_campaign(tmp_path,['S6'],require_sitl=True,sitl_dir=tmp_path/'absent')
    report=json.loads((tmp_path/'report.json').read_text())
    assert code==2
    assert report['scenarios'][0]['status']=='NOT_RUN'
    assert report['overall_status']=='FAIL'
    assert report['summary_counts']['not_run']==1
    assert report['verdict_line'].startswith('TRL 5 validation FAILED: S6_')


def test_windows_sitl_is_not_applicable(tmp_path,monkeypatch):
    from minerva.trl5 import sitl_harness
    monkeypatch.setattr(sitl_harness.platform,'system',lambda:'Windows')
    code=run_campaign(tmp_path,['S6'])
    report=json.loads((tmp_path/'report.json').read_text())
    assert code==0
    assert report['scenarios'][0]['status']=='NOT_APPLICABLE'
    assert report['summary_counts']['not_applicable']==1
    assert report['summary_counts']['passed']==0
