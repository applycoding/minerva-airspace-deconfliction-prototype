import json
import os
from pathlib import Path
import subprocess
import sys
from dataclasses import replace
from minerva.gui.main_window import MainWindow
from minerva.models import PlannerStatus
from minerva.test_rig.scenarios import make_plan, calm_weather
from minerva.db import list_active_plans


def test_parts_1_to_6(qapp, tmp_path):
    window = MainWindow(tmp_path/'gui.sqlite3')
    try:
        window.weather = [calm_weather()]
        assert len(window.zones)==3
        p = make_plan('first',[(500000,5500000,150,1000),(501000,5500000,150,1040)])
        p.status = 'DRAFT'
        window.editor.load_plan(p)
        result = window.run_planner()
        assert result.status == PlannerStatus.FOUND
        assert len(window.candidate.waypoints)>=2
        assert window.check_candidate()==[]
        window.approve_candidate()
        active = list_active_plans(window.conn)
        assert len(active)==1 and active[0].tunnel is not None
        second = replace(active[0],plan_id='second',status='DRAFT',callsign='SECOND')
        window.editor.load_plan(second)
        assert any(c.kind=='SPACE_TIME' for c in window.check_candidate())
        assert window.conflict_panel.table.rowCount()>0
        proposal = window.resolve_candidate()
        assert not proposal.requires_operator and proposal.conflicts_remaining==0
        assert window.check_candidate()==[]
        for geo,name in [(False,'tunnel.json'),(True,'tunnel.geojson')]:
            path = tmp_path/name
            window.conflict_panel.export(window.editor.read_plan(),path,geo)
            data = json.loads(path.read_text())
            if geo: assert data['type']=='FeatureCollection' and len(data['features'])>0
            else: assert data['width_m']==200 and data['segments']
        window.approve_candidate()
        assert len(window.active())==2
        window.show(); qapp.processEvents()
        assert not window.map_canvas.grab().isNull()
    finally:
        window.close()


def test_source_smoke_and_self_check(tmp_path):
    env = dict(os.environ,QT_QPA_PLATFORM='offscreen',MINERVA_DB_PATH=str(tmp_path/'smoke.sqlite3'),PYTHONPATH=str(Path('src').resolve()))
    marker = tmp_path/'marker.txt'
    for args in [ ['--self-check'], ['--gui-smoke','--marker-file',str(marker)]]:
        result = subprocess.run([sys.executable,'-m','minerva',*args],env=env,capture_output=True,text=True,timeout=60)
        assert result.returncode==0, result.stdout+result.stderr
    assert marker.read_text()=='MINERVA GUI smoke passed\n'


def test_packaging_module_manifest():
    spec = Path('minerva.spec').read_text()
    for module in ['map_canvas','plan_editor','conflict_panel','live_panel']:
        assert f'minerva.gui.{module}' in spec
    assert 'minerva.live' in spec
