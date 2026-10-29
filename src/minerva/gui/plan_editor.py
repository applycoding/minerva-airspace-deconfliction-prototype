"""Plan form with editable waypoint, airframe and radio values."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from uuid import uuid4
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QTextEdit, QPushButton, QComboBox, QFileDialog
from ..models import FlightPlan, Waypoint4D, DroneLimits, RadioSpec
from ..coords import lonlat_to_utm12n
from ..db import validate_plan_invariants
from ..tunnel import build_tunnel


def epoch(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp() if isinstance(value,str) else float(value)


class PlanEditor(QWidget):
    action = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.callsign = QLineEdit('SIM')
        self.priority = QSpinBox(); self.priority.setRange(1,4); self.priority.setValue(2)
        self.objective = QComboBox(); self.objective.addItems(['shortest_time','avoid_zones','avoid_radio'])
        self.values = QTextEdit()
        form.addRow('Callsign',self.callsign); form.addRow('Priority',self.priority); form.addRow('Objective',self.objective)
        layout.addLayout(form)
        layout.addWidget(self.values)
        self.plan_id = uuid4().hex
        for title, action in [('Import JSON','import'),('New plan','new'),('Run planner','plan'),('Check conflicts','check'),('Resolve candidate','resolve'),('Approve candidate','approve')]:
            button = QPushButton(title); layout.addWidget(button)
            button.clicked.connect(lambda checked=False,a=action: self.action.emit(a))
        self.new_plan()

    def new_plan(self):
        self.plan_id = uuid4().hex
        now = datetime.now(timezone.utc).timestamp()
        self.values.setPlainText(json.dumps(dict(limits=asdict(DroneLimits(40,5,4,100,15)),radio=asdict(RadioSpec(2400,10,20,2,2,-90,50.1,-111.4)),waypoints=[dict(lat_deg=50.1,lon_deg=-111.4,alt_m=150,epoch_s=datetime.fromtimestamp(now,timezone.utc).isoformat().replace('+00:00','Z')),dict(lat_deg=50.1,lon_deg=-111.38,alt_m=150,epoch_s=datetime.fromtimestamp(now+60,timezone.utc).isoformat().replace('+00:00','Z'))]),indent=2))

    def load_plan(self, plan):
        self.plan_id = plan.plan_id
        self.callsign.setText(plan.callsign); self.priority.setValue(plan.priority)
        data = dict(limits=asdict(plan.limits),radio=asdict(plan.radio),waypoints=[asdict(w) for w in plan.waypoints])
        for w in data['waypoints']:
            w['epoch_s'] = datetime.fromtimestamp(w['epoch_s'],timezone.utc).isoformat().replace('+00:00','Z')
        self.values.setPlainText(json.dumps(data,indent=2))

    def import_json(self, path):
        data = json.loads(path.read_text())
        self.plan_id = data.get('plan_id',uuid4().hex)
        self.callsign.setText(data.get('callsign','SIM')); self.priority.setValue(data.get('priority',2))
        self.values.setPlainText(json.dumps(data,indent=2))
        return self.read_plan()

    def read_plan(self):
        data = json.loads(self.values.toPlainText())
        points = []
        for item in data['waypoints']:
            x,y = lonlat_to_utm12n(item['lon_deg'],item['lat_deg'])
            points.append(Waypoint4D(item['lat_deg'],item['lon_deg'],item['alt_m'],epoch(item['epoch_s']),x,y))
        radio = RadioSpec(**data['radio']); radio.gcs_x_m,radio.gcs_y_m = lonlat_to_utm12n(radio.gcs_lon_deg,radio.gcs_lat_deg)
        plan = FlightPlan(self.plan_id,self.callsign.text(),self.priority.value(),'DRAFT',datetime.now(timezone.utc).timestamp(),DroneLimits(**data['limits']),radio,points,None)
        validate_plan_invariants(plan)
        plan.tunnel = build_tunnel(plan.plan_id,points)
        return plan
