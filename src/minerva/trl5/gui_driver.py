"""Operator workflows against a real offscreen window and disk database."""
from dataclasses import asdict
import json
from pathlib import Path
import time
from PySide6.QtWidgets import QApplication
from ..gui.main_window import MainWindow
from ..resources import data_dir


class GuiDriver:
    def __init__(self, root, scenario_id, epoch):
        self.root, self.id = Path(root), scenario_id
        for folder in ('events','screenshots','db'):
            (self.root/folder).mkdir(parents=True,exist_ok=True)
        self.db_path = self.root/'db'/f'{scenario_id}.sqlite3'
        for suffix in ('','-wal','-shm'):
            self.db_path.with_name(self.db_path.name+suffix).unlink(missing_ok=True)
        self.events = (self.root/'events'/f'{scenario_id}.jsonl').open('w',encoding='utf-8')
        self.app = QApplication.instance() or QApplication([])
        self.start_perf = time.perf_counter(); self.epoch = epoch
        self.window = MainWindow(self.db_path)
        self.window.show(); self.pump(.02)
        self.window.live_panel.tracker.clock = self.clock
        self.screenshots = []; self.timings = []; self.latencies = []; self.alert_latencies = []
        self.last_drift = {}
        self.window.live_panel.report_callback = self.on_report
        self.window.ingest_metar_file(data_dir()/'trl5/calm.txt')
        self.event('opened',db=str(self.db_path),zones=[z.zone_id for z in self.window.zones])

    def clock(self):
        return self.epoch+time.perf_counter()-self.start_perf

    def pump(self, seconds=0):
        end = time.perf_counter()+seconds
        while True:
            self.app.processEvents()
            if time.perf_counter() >= end: break
            time.sleep(min(.005,max(0.,end-time.perf_counter())))

    def event(self, kind, **values):
        self.events.write(json.dumps(dict(event=kind,perf_s=time.perf_counter(),epoch_s=self.clock(),**values),allow_nan=False)+'\n')
        self.events.flush()

    def on_report(self, report):
        latency = report.gui_perf_s-report.received_perf_s
        self.latencies.append(latency)
        emitted = report.drift and not self.last_drift.get(report.key,False)
        if emitted:
            self.alert_latencies.append(latency)
        self.last_drift[report.key] = report.drift
        self.event('telemetry',key=report.key,plan_id=report.plan_id,status=report.status.value,
                   waypoint=asdict(report.waypoint),outside=report.outside,drift=report.drift,
                   violation_type=report.violation_type,received_perf_s=report.received_perf_s,
                   gui_perf_s=report.gui_perf_s,receive_to_gui_s=latency,alert_emitted=emitted)

    def screenshot(self, name):
        self.pump(.02)
        relative = f'screenshots/{self.id}_{name}.png'
        path = self.root/relative
        pixmap = self.window.grab()
        if pixmap.isNull() or pixmap.width()<1000 or pixmap.height()<700 or not pixmap.save(str(path),'PNG') or path.stat().st_size<=1000:
            raise AssertionError('Window screenshot is empty or too small')
        self.screenshots.append(relative)
        self.event('screenshot',path=relative,width=pixmap.width(),height=pixmap.height(),bytes=path.stat().st_size)
        return relative

    def load(self, plan):
        from shapely.geometry import Point, Polygon
        clearances = [min(Point(w.x_m,w.y_m).distance(Polygon(z.polygon_utm)) for z in self.window.zones)
                      for w in (plan.waypoints[0],plan.waypoints[-1])]
        self.event('request_site_clearance',plan_id=plan.plan_id,start_m=clearances[0],goal_m=clearances[1])
        if min(clearances)<500.:
            raise AssertionError(f'{plan.plan_id}: campaign endpoint less than 500 m outside a shipped zone')
        self.window.editor.load_plan(plan)
        return self.window.editor.read_plan()

    def check(self, plan):
        self.load(plan)
        records = self.window.check_candidate()
        self.event('check',plan_id=plan.plan_id,conflicts=[asdict(c) for c in records])
        return records

    def approve(self, plan):
        self.load(plan)
        revision = self.window.approve_candidate()
        stored = next(p for p in self.window.active() if p.plan_id==plan.plan_id)
        self.event('approved',revision=revision,plan=asdict(stored))
        return stored

    def plan(self, request, objective='shortest_time'):
        self.load(request); self.window.editor.objective.setCurrentText(objective)
        started = time.perf_counter(); result = self.window.run_planner(); elapsed = time.perf_counter()-started
        self.timings.append(elapsed)
        self.event('planner',plan_id=request.plan_id,status=result.status.value,expansions=result.expansions,wall_s=elapsed)
        if result.plan is None: raise AssertionError(f'{request.plan_id}: {result.status.value}')
        return self.window.editor.read_plan()

    def reroute(self, key):
        panel = self.window.live_panel; panel.select_track(key)
        started = time.perf_counter(); result = panel.compute(); elapsed = time.perf_counter()-started
        self.timings.append(elapsed)
        self.event('reroute_computed',status=result.status.value,wall_s=elapsed,original_id=panel.original_id)
        return result,elapsed

    def resolve(self):
        started = time.perf_counter()
        proposal = self.window.resolve_candidate()
        elapsed = time.perf_counter()-started
        self.timings.append(elapsed)
        self.event('resolution',wall_s=elapsed,proposal=asdict(proposal))
        return proposal

    def accept(self):
        panel = self.window.live_panel
        plan = panel.proposal.plan
        revision = panel.accept()
        stored = next(p for p in self.window.active() if p.plan_id==plan.plan_id)
        self.event('reroute_accepted',revision=revision,plan=asdict(stored))
        return stored

    def restart(self):
        before = [asdict(p) for p in self.window.active()]
        def snapshot(conn):
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name:sorted([tuple(row) for row in conn.execute('SELECT * FROM "'+name+'"')],key=repr) for name in tables}
        all_before = snapshot(self.window.conn)
        revision = self.window.conn.execute('SELECT revision FROM db_state_meta').fetchone()[0]
        self.window.close(); self.pump()
        self.window = MainWindow(self.db_path); self.window.show(); self.pump(.02)
        after = [asdict(p) for p in self.window.active()]
        equal = before==after and all_before==snapshot(self.window.conn) and revision==self.window.conn.execute('SELECT revision FROM db_state_meta').fetchone()[0]
        self.event('reloaded',equal=equal,plan_count=len(after),revision=revision)
        return equal

    def close(self):
        self.window.close(); self.pump(); self.events.close()
