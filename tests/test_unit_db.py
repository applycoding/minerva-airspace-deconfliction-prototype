from copy import deepcopy
from pathlib import Path
import sqlite3
import pytest
from minerva.db import *
from minerva.models import ConflictRecord
from minerva.tunnel import build_tunnel
from minerva.ingest import load_zones_geojson, parse_weather_text


def test_path(monkeypatch,tmp_path):
    monkeypatch.setenv('MINERVA_DB_PATH',str(tmp_path/'env.sqlite3'))
    assert resolve_db_path()==tmp_path/'env.sqlite3'
    assert resolve_db_path(tmp_path/'explicit')==tmp_path/'explicit'
    monkeypatch.delenv('MINERVA_DB_PATH')
    if __import__('os').name != 'nt':
        assert resolve_db_path()==Path.home()/'.local/share/minerva/minerva.sqlite3'
    else:
        assert resolve_db_path()==Path(__import__('os').environ['LOCALAPPDATA'])/'Minerva/minerva.sqlite3'


def test_schema_roundtrip(conn,plan):
    assert conn.execute('PRAGMA foreign_keys').fetchone()[0]==1
    assert conn.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
    assert get_db_revision(conn)==0
    plan.tunnel=build_tunnel(plan.plan_id,plan.waypoints)
    assert approve_and_persist_plan(conn,plan,0)==1
    loaded=list_active_plans(conn)
    expected=deepcopy(plan); expected.status='APPROVED'
    assert loaded==[expected]
    assert plan.status=='DRAFT'
    assert list_active_plans(conn,2000,3000)==[]
    assert list_active_plans(conn,1060,1061)==loaded
    assert conn.execute('SELECT count(*) FROM tunnel_segments_4d').fetchone()[0]==2


def test_stale_and_atomic_supersede(conn,plan):
    approve_and_persist_plan(conn,plan,0)
    other=deepcopy(plan); other.plan_id='p2'
    with pytest.raises(StaleStateError): approve_and_persist_plan(conn,other,0,plan.plan_id)
    assert [p.plan_id for p in list_active_plans(conn)]==['p1']
    assert get_db_revision(conn)==1
    with pytest.raises(sqlite3.IntegrityError): approve_and_persist_plan(conn,plan,1)
    assert get_db_revision(conn)==1
    with pytest.raises(ValueError): approve_and_persist_plan(conn,other,1,'missing')
    assert approve_and_persist_plan(conn,other,1,plan.plan_id)==2
    assert [p.plan_id for p in list_active_plans(conn)]==['p2']
    assert conn.execute('SELECT status FROM flight_plans WHERE plan_id=?',('p1',)).fetchone()[0]=='SUPERSEDED'


def test_two_connection_cas(tmp_path,plan):
    a=init_db(tmp_path/'cas.sqlite3'); b=init_db(tmp_path/'cas.sqlite3')
    try:
        revision=get_db_revision(b)
        approve_and_persist_plan(a,plan,revision)
        plan.plan_id='p2'
        with pytest.raises(StaleStateError): approve_and_persist_plan(b,plan,revision)
        assert get_db_revision(b)==1
        assert len(list_active_plans(b))==1
    finally:
        a.close(); b.close()


@pytest.mark.parametrize('bad', ['few','equal','reverse','nan','infinite','limit','radio','coordinate','priority','altitude'])
def test_invariant_rejections(conn,plan,bad):
    if bad=='few': plan.waypoints=plan.waypoints[:1]
    if bad=='equal': plan.waypoints[1].epoch_s=plan.waypoints[0].epoch_s
    if bad=='reverse': plan.waypoints.reverse()
    if bad=='nan': plan.waypoints[1].x_m=float('nan')
    if bad=='infinite': plan.radio.tx_gain_dbi=float('inf')
    if bad=='limit': plan.limits.max_airspeed_mps=0
    if bad=='radio': plan.radio.freq_mhz=-1
    if bad=='coordinate': plan.waypoints[0].lat_deg=91
    if bad=='priority': plan.priority=5
    if bad=='altitude': plan.waypoints[0].alt_m=-1
    with pytest.raises(ValueError): approve_and_persist_plan(conn,plan,0)
    assert get_db_revision(conn)==0 and list_active_plans(conn)==[]


def test_crewed_precedence(conn,plan):
    plan.is_crewed=True
    approve_and_persist_plan(conn,plan,0)
    assert list_active_plans(conn)[0].status=='CREWED_ACTIVE'
    other=deepcopy(plan); other.is_crewed=False; other.plan_id='replacement'
    with pytest.raises(ValueError): approve_and_persist_plan(conn,other,1,plan.plan_id)
    assert len(list_active_plans(conn))==1


def test_zones_weather_logs(conn):
    zones=load_zones_geojson(Path('data/zones/suffield.geojson'))
    zones[0].override_active=False; zones[0].override_ceiling_m=500
    save_zones(conn,zones)
    loaded=list_zones(conn)
    assert loaded[0].polygon_wgs84==zones[0].polygon_wgs84
    assert loaded[0].override_active is False and loaded[0].override_ceiling_m==500
    assert loaded[2].polygon_utm[0]==pytest.approx(zones[2].polygon_utm[0],abs=.001)
    weather=parse_weather_text(Path('data/weather/cyxh_metar_calm.txt'))
    save_weather(conn,weather)
    o=weather[0]
    assert get_active_weather(conn,o.valid_start_epoch_s,o.valid_end_epoch_s)==o
    assert get_active_weather(conn,o.valid_start_epoch_s,o.valid_end_epoch_s+1) is None
    record=ConflictRecord('c1','WEATHER_WIND','p','weather',1,2,0,0,None,'ERROR','test wind')
    log_conflicts(conn,[record])
    assert conn.execute('SELECT description FROM conflict_logs').fetchone()[0]=='test wind'
    assert get_db_revision(conn)==2
