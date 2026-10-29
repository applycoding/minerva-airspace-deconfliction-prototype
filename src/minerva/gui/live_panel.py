from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit
from ..live import LiveTracker, UDPReceiver
from ..db import get_db_revision


class LivePanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window; self.receiver = None; self.report = None; self.proposal = None
        self.tracker = LiveTracker(window.active())
        layout = QVBoxLayout(self)
        self.label = QLabel('Simulation only; telemetry is not authenticated. Receiver stopped.')
        layout.addWidget(self.label)
        self.mapping = QLineEdit(); self.mapping.setPlaceholderText('Known ID: source port, sysid, compid, approved plan ID')
        layout.addWidget(self.mapping)
        for text,callback in [('Start loopback receiver',self.start),('Stop receiver',self.stop),('Map known ID',self.map_id),('Compute re-route',self.compute),('Accept re-route (operator confirmation)',self.accept)]:
            button = QPushButton(text); layout.addWidget(button)
            button.clicked.connect(lambda checked=False,fn=callback:self.invoke(fn))
        self.timer = QTimer(self); self.timer.setInterval(50); self.timer.timeout.connect(self.poll)

    def invoke(self, fn):
        try: fn()
        except (ValueError, OSError, KeyError, StopIteration) as error: self.label.setText(str(error))

    def start(self):
        self.stop(); self.receiver = UDPReceiver(); self.timer.start()
        self.label.setText(f'Listening on {self.receiver.address}; not authenticated')

    def stop(self):
        self.timer.stop()
        if self.receiver: self.receiver.close(); self.receiver = None

    def map_id(self):
        port,sysid,compid,plan_id = [s.strip() for s in self.mapping.text().split(',')]
        if plan_id not in {p.plan_id for p in self.window.active()}: raise ValueError('Unknown approved plan')
        self.tracker.known_ids[(('127.0.0.1',int(port)),int(sysid),int(compid))] = plan_id

    def poll(self):
        self.tracker.plans = self.window.active()
        for report in self.receiver.poll(self.tracker):
            self.report = report
            self.label.setText(f'{report.status.value}: {report.plan_id}; drift={report.drift}; not authenticated')

    def compute(self):
        if not self.report or not self.report.plan_id: raise ValueError('Select a matched report first')
        original = next(p for p in self.window.active() if p.plan_id==self.report.plan_id)
        self.revision = get_db_revision(self.window.conn)
        self.original_id = original.plan_id
        self.proposal = self.tracker.compute_reroute(self.report,self.window.active(),self.window.zones,self.window.current_weather(original))
        self.label.setText(f'{self.proposal.status.value}; {self.proposal.elapsed_s:.3f} s; awaiting operator acceptance')

    def accept(self):
        if self.proposal is None: raise ValueError('Compute a re-route first')
        self.tracker.accept_reroute(self.window.conn,self.proposal,self.original_id,self.revision)
        self.proposal = None; self.window.refresh(); self.label.setText('Re-route accepted into SQLite')
