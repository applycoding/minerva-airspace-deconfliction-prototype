from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QListWidget, QPushButton
from ..tunnel import export_tunnel_json, export_tunnel_geojson


class ConflictPanel(QWidget):
    action = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0,4); self.table.setHorizontalHeaderLabels(['Kind','Plan','Other / zone','Description'])
        self.zone_list = QListWidget()
        layout.addWidget(self.table); layout.addWidget(self.zone_list)
        for title,action in [('Export tunnel JSON','json'),('Export tunnel GeoJSON','geojson'),('Load zone overrides','overrides')]:
            button = QPushButton(title); layout.addWidget(button)
            button.clicked.connect(lambda checked=False,a=action:self.action.emit(a))

    def refresh(self, conflicts, zones):
        self.table.setRowCount(len(conflicts))
        for row,c in enumerate(conflicts):
            for column,value in enumerate((c.kind,c.plan_a_id,c.plan_b_or_zone_id,c.description)):
                self.table.setItem(row,column,QTableWidgetItem(value))
        self.zone_list.clear()
        self.zone_list.addItems([f'{z.zone_id}: {z.name}; ceiling {z.override_ceiling_m if z.override_ceiling_m is not None else z.ceiling_m} m; active override {z.override_active}' for z in zones])

    def export(self, plan, path, geojson=False):
        if geojson:
            export_tunnel_geojson(plan,path)
        else:
            export_tunnel_json(plan.tunnel,path)
