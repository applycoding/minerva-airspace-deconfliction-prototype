"""Offline vector display in local metric coordinates."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class MapCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.plans, self.zones, self.conflicts = [], [], []
        self.setMinimumSize(300,250)

    def set_scene(self, plans, zones, conflicts):
        self.plans,self.zones,self.conflicts = plans,zones,conflicts
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(),QColor('#f4f5f0'))
        coords = [(w.x_m,w.y_m) for p in self.plans for w in p.waypoints]+[xy for z in self.zones for xy in z.polygon_utm]
        if not coords:
            painter.drawText(20,30,'Offline UTM 12N map — simulation only'); return
        xs,ys = zip(*coords); xmin,ymin = min(xs),min(ys)
        scale = min((self.width()-40)/max(max(xs)-xmin,1),(self.height()-40)/max(max(ys)-ymin,1))
        def point(x,y):
            return QPointF(20+(x-xmin)*scale,self.height()-20-(y-ymin)*scale)
        painter.setPen(QPen(QColor('#996622'),1)); painter.setBrush(QColor(220,180,80,70))
        for zone in self.zones:
            painter.drawPolygon(QPolygonF([point(*xy) for xy in zone.polygon_utm]))
        bad = {c.plan_a_id for c in self.conflicts}
        for plan in self.plans:
            poly = QPolygonF([point(w.x_m,w.y_m) for w in plan.waypoints])
            if plan.tunnel:
                painter.setPen(QPen(QColor(60,140,200,50),max(1,plan.tunnel.width_m*scale)))
                painter.drawPolyline(poly)
            painter.setPen(QPen(QColor('#c03030' if plan.plan_id in bad else '#145c90'),2))
            painter.drawPolyline(poly)
            for p in poly:
                painter.drawEllipse(p,3,3)
            painter.drawText(poly[0],plan.callsign)
