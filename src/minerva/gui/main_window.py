from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFileDialog, QPushButton, QLineEdit, QLabel
from .. import db
from ..resources import data_dir
from ..ingest import load_zones_geojson, parse_weather_text, resolve_weather_for_window
from ..conflict import check_all_conflicts, SpatialIndex
from ..planner import plan_4d_path
from ..resolver import resolve_conflicts
from .map_canvas import MapCanvas
from .plan_editor import PlanEditor, epoch
from .conflict_panel import ConflictPanel


class MainWindow(QMainWindow):
    def __init__(self, db_path=None):
        super().__init__()
        self.setWindowTitle('MINERVA — simulation only; never flown')
        self.resize(1200,850)
        self.conn = db.init_db(db.resolve_db_path(db_path))
        self.zones = load_zones_geojson(data_dir()/'zones/suffield.geojson')
        db.save_zones(self.conn,self.zones)
        self.weather = parse_weather_text(data_dir()/'weather/cyxh_metar_calm.txt')
        self.candidate = None; self.conflicts = []
        self.editor = PlanEditor(); self.map_canvas = MapCanvas(); self.conflict_panel = ConflictPanel()
        central = QWidget(); layout = QHBoxLayout(central); layout.addWidget(self.editor,1)
        right = QVBoxLayout(); layout.addLayout(right,2); right.addWidget(self.map_canvas); right.addWidget(self.conflict_panel)
        self.weather_input = QLineEdit('0, 0, 0, 2026-01-01T00:00:00Z, 2027-01-01T00:00:00Z')
        right.addWidget(QLabel('Explicit synthetic wind: from degrees, speed m/s, gust m/s, UTC start, UTC end'))
        right.addWidget(self.weather_input)
        wind_button = QPushButton('Use synthetic wind'); right.addWidget(wind_button)
        wind_button.clicked.connect(lambda:self.safe_action('wind'))
        self.setCentralWidget(central)
        self.editor.action.connect(self.safe_action); self.conflict_panel.action.connect(self.safe_action)
        self.refresh()
        from .live_panel import LivePanel
        self.live_panel = LivePanel(self); right.addWidget(self.live_panel)

    def active(self):
        return db.list_active_plans(self.conn)

    def current_weather(self, plan):
        return resolve_weather_for_window(self.weather,plan.waypoints[0].epoch_s,plan.waypoints[-1].epoch_s)

    def refresh(self):
        plans = self.active()
        self.index = SpatialIndex(plans)
        self.map_canvas.set_scene(plans+([self.candidate] if self.candidate else []),self.zones,self.conflicts)
        self.conflict_panel.refresh(self.conflicts,self.zones)

    def check_candidate(self):
        self.candidate = self.editor.read_plan()
        self.conflicts = check_all_conflicts(self.candidate,self.active(),self.zones,self.current_weather(self.candidate),index=self.index)
        db.log_conflicts(self.conn,self.conflicts)
        self.refresh()
        return self.conflicts

    def run_planner(self):
        p = self.editor.read_plan(); goal = p.waypoints[-1]
        result = plan_4d_path(p.waypoints[0],goal.lat_deg,goal.lon_deg,goal.alt_m,p.limits,p.radio,self.editor.objective.currentText(),self.zones,self.active(),self.current_weather(p))
        if result.plan:
            from dataclasses import replace
            self.candidate = replace(result.plan,plan_id=p.plan_id,callsign=p.callsign,priority=p.priority)
            from ..tunnel import build_tunnel
            self.candidate.tunnel = build_tunnel(p.plan_id,self.candidate.waypoints)
            self.editor.load_plan(self.candidate)
        self.refresh()
        return result

    def resolve_candidate(self):
        p = self.editor.read_plan()
        proposal = resolve_conflicts(p,self.active(),self.zones,self.current_weather(p),[5800.,900.])
        if proposal.modified_plan:
            self.editor.load_plan(proposal.modified_plan)
            self.check_candidate()
        return proposal

    def approve_candidate(self):
        revision = db.get_db_revision(self.conn)
        if self.check_candidate():
            raise ValueError('Resolve conflicts before approval')
        result = db.approve_and_persist_plan(self.conn,self.candidate,revision)
        self.candidate = None; self.editor.new_plan(); self.refresh()
        return result

    def safe_action(self, action):
        try:
            self.perform_action(action)
        except (ValueError, KeyError, OSError, TypeError, db.StaleStateError) as error:
            self.statusBar().showMessage(str(error))

    def perform_action(self, action):
        if action=='new': self.editor.new_plan()
        elif action=='plan': self.statusBar().showMessage(self.run_planner().message)
        elif action=='check': self.check_candidate()
        elif action=='resolve': self.statusBar().showMessage(self.resolve_candidate().summary)
        elif action=='approve': self.approve_candidate()
        elif action=='wind':
            from ..models import WeatherObservation
            fields = [s.strip() for s in self.weather_input.text().split(',')]
            self.weather = [WeatherObservation('OPERATOR',epoch(fields[3]),epoch(fields[4]),float(fields[0]),float(fields[1]),float(fields[2]),True)]
        elif action in ('json','geojson'):
            path,_ = QFileDialog.getSaveFileName(self,'Export tunnel','','JSON (*.json *.geojson)')
            if path: self.conflict_panel.export(self.editor.read_plan(),Path(path),action=='geojson')
        elif action in ('import','overrides'):
            path,_ = QFileDialog.getOpenFileName(self,'Load JSON','','JSON (*.json)')
            if path and action=='import': self.editor.import_json(Path(path))
            elif path:
                self.zones = load_zones_geojson(data_dir()/'zones/suffield.geojson',Path(path)); db.save_zones(self.conn,self.zones); self.refresh()

    def closeEvent(self, event):
        self.live_panel.stop()
        self.conn.close()
        super().closeEvent(event)
