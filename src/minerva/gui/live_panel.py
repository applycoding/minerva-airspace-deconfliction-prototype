import time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem
from ..live import LiveTracker, UDPReceiver
from ..db import get_db_revision


class LivePanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window; self.receiver = None; self.report = None; self.proposal = None
        self.tracker = LiveTracker(window.active())
        self.reports = {}; self.report_history = []; self.report_callback = None
        layout = QVBoxLayout(self)
        self.label = QLabel('Simulation only; telemetry is not authenticated. Receiver stopped.')
        layout.addWidget(self.label)
        self.tracks = QComboBox(); layout.addWidget(self.tracks)
        self.tracks.currentIndexChanged.connect(self.select_index)
        self.table = QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(['Source / ID','Plan','Match','Conformance','Violation'])
        layout.addWidget(self.table)
        self.table.cellClicked.connect(lambda row,column:self.tracks.setCurrentIndex(row))
        self.mapping = QLineEdit(); self.mapping.setPlaceholderText('Known ID: source port, sysid, compid, approved plan ID')
        layout.addWidget(self.mapping)
        for text,callback in [('Start loopback receiver',self.start),('Stop receiver',self.stop),('Map known ID',self.map_id),('Compute re-route',self.compute),('Accept re-route (operator confirmation)',self.accept),('Record hold / land in place',self.hold_land)]:
            button = QPushButton(text); layout.addWidget(button)
            button.clicked.connect(lambda checked=False,fn=callback:self.invoke(fn))
        self.timer = QTimer(self); self.timer.setInterval(50); self.timer.timeout.connect(self.poll)
        self.window.conn.execute('CREATE TABLE IF NOT EXISTS operator_decisions (decision_id INTEGER PRIMARY KEY, epoch_s REAL NOT NULL, plan_id TEXT NOT NULL, decision TEXT NOT NULL)')
        self.window.conn.commit()

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

    def select_index(self, index):
        key = self.tracks.itemData(index)
        if key in self.reports:
            self.report = self.reports[key]
            self.show_report(self.report)

    def select_track(self, key):
        for index in range(self.tracks.count()):
            if self.tracks.itemData(index) == key:
                self.tracks.setCurrentIndex(index)
                self.report = self.reports[key]
                return self.report
        raise ValueError('Track has not reported')

    def show_report(self, report):
        self.label.setText(f'{report.status.value}: {report.plan_id}; drift={report.drift}; {report.violation_type or "CONFORMING"}; not authenticated')

    def poll(self):
        if self.receiver is None: return
        self.tracker.plans = self.window.active()
        for report in self.receiver.poll(self.tracker):
            if report.key not in self.reports:
                self.tracks.addItem(f'{report.key[0][1]} / {report.key[1]} / {report.key[2]}',report.key)
                self.table.setRowCount(self.tracks.count())
            self.reports[report.key] = report
            self.report_history.append(report)
            row = next(i for i in range(self.tracks.count()) if self.tracks.itemData(i)==report.key)
            values=(self.tracks.itemText(row),report.plan_id or '',report.status.value,
                    'NON_CONFORMING' if report.drift else 'OUTSIDE (pending)' if report.outside else 'CONFORMING' if report.plan_id else 'UNASSOCIATED',
                    report.violation_type or '')
            for column,value in enumerate(values):
                self.table.setItem(row,column,QTableWidgetItem(value))
            if self.report is None or self.tracks.currentData() == report.key:
                self.report = report
                self.show_report(report)
            report.gui_perf_s = time.perf_counter()
            if self.report_callback: self.report_callback(report)

    def compute(self):
        if not self.report or not self.report.plan_id: raise ValueError('Select a matched report first')
        original = next(p for p in self.window.active() if p.plan_id==self.report.plan_id)
        self.revision = get_db_revision(self.window.conn)
        self.original_id = original.plan_id
        self.proposal = self.tracker.compute_reroute(self.report,self.window.active(),self.window.zones,self.window.current_weather(original))
        if self.proposal.plan is None:
            self.label.setText(f'{self.proposal.status.value}: requires operator; hold / land in place decision needed')
        else:
            self.label.setText(f'{self.proposal.status.value}; {self.proposal.elapsed_s:.3f} s; awaiting operator acceptance')
        return self.proposal

    def accept(self):
        if self.proposal is None: raise ValueError('Compute a re-route first')
        result = self.tracker.accept_reroute(self.window.conn,self.proposal,self.original_id,self.revision)
        self.proposal = None; self.window.refresh(); self.label.setText('Re-route accepted into SQLite')
        return result

    def hold_land(self):
        if not self.report or not self.report.plan_id: raise ValueError('Select a matched report first')
        if self.proposal is None or self.proposal.plan is not None:
            raise ValueError('Record a no-solution re-route before the operator decision')
        # This records a simulated decision and releases the reservation; no command is sent.
        conn = self.window.conn
        with conn:
            conn.execute('INSERT INTO operator_decisions(epoch_s,plan_id,decision) VALUES (?,?,?)',
                         (self.tracker.clock(),self.report.plan_id,'HOLD_LAND_IN_PLACE; simulation only'))
            conn.execute("UPDATE flight_plans SET status='SUPERSEDED' WHERE plan_id=? AND status='APPROVED' AND is_crewed=0",(self.report.plan_id,))
            conn.execute('UPDATE db_state_meta SET revision=revision+1 WHERE id=1')
        self.window.refresh()
        self.label.setText('Operator decision recorded: hold / land in place (simulation only)')
