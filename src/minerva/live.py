"""Simulation telemetry. All identifiers and signatures are not authenticated."""
from collections import deque
from dataclasses import dataclass, replace
import math
import socket
import struct
import time
from uuid import uuid4
from .coords import lonlat_to_utm12n, utm12n_to_lonlat
from .models import TrackMatchStatus, Waypoint4D, ConflictRecord
from .tunnel import build_tunnel

_MESSAGES = {0: (50, 9), 33: (104, 28)}


def crc16_mcrf4xx(data: bytes, crc_extra: int) -> int:
    crc = 0xffff
    for byte in data + bytes([crc_extra]):
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8408 if crc & 1 else 0)
    return crc


def encode_mavlink_v2_frame(msgid, payload, sysid=1, compid=1, seq=0):
    extra, full_len = _MESSAGES[msgid]
    if len(payload) != full_len:
        raise ValueError('Incorrect payload length')
    payload = payload.rstrip(b'\0') or b'\0'
    header = bytes([len(payload), 0, 0, seq % 256, sysid, compid]) + msgid.to_bytes(3, 'little')
    return b'\xfd' + header + payload + struct.pack('<H', crc16_mcrf4xx(header + payload, extra))


def parse_mavlink_v2_datagram(datagram):
    messages, dropped, pos = [], 0, 0
    while pos < len(datagram):
        if datagram[pos] != 0xfd or len(datagram)-pos < 12:
            dropped += 1
            break
        length, flags = datagram[pos+1:pos+3]
        size = 12 + length + (13 if flags & 1 else 0)
        frame = datagram[pos:pos+size]
        pos += size
        msgid = int.from_bytes(frame[7:10], 'little')
        if len(frame) != size or flags & ~1 or msgid not in _MESSAGES:
            dropped += 1
            continue
        extra, full_len = _MESSAGES[msgid]
        if not 1 <= length <= full_len or crc16_mcrf4xx(frame[1:10+length], extra) != int.from_bytes(frame[10+length:12+length], 'little'):
            dropped += 1
            continue
        payload = frame[10:10+length].ljust(full_len, b'\0')
        message = dict(msgid=msgid, seq=frame[4], sysid=frame[5], compid=frame[6], trust='not authenticated')
        if msgid == 33:
            values = struct.unpack('<IiiiihhhH', payload)
            message.update(zip(('time_boot_ms','lat','lon','alt','relative_alt','vx','vy','vz','hdg'), values))
            message.update(lat_deg=values[1]/1e7, lon_deg=values[2]/1e7, alt_m=values[4]/1000.)
        else:
            message.update(zip(('custom_mode','type','autopilot','base_mode','system_status','mavlink_version'), struct.unpack('<IBBBBB', payload)))
        messages.append(message)
    return messages, dropped


def interpolate(plan, epoch):
    points = plan.waypoints
    if epoch <= points[0].epoch_s:
        return points[0]
    for a, b in zip(points, points[1:]):
        if epoch <= b.epoch_s:
            f = (epoch-a.epoch_s)/(b.epoch_s-a.epoch_s)
            x, y = a.x_m+f*(b.x_m-a.x_m), a.y_m+f*(b.y_m-a.y_m)
            lon, lat = utm12n_to_lonlat(x, y)
            return replace(a, lat_deg=lat, lon_deg=lon, x_m=x, y_m=y, alt_m=a.alt_m+f*(b.alt_m-a.alt_m), epoch_s=epoch)
    return points[-1]


@dataclass
class TrackReport:
    key: tuple
    waypoint: Waypoint4D
    status: TrackMatchStatus
    plan_id: str | None
    outside: bool = False
    drift: bool = False


class LiveTracker:
    def __init__(self, plans=(), known_ids=None, clock=time.time):
        self.plans = list(plans)
        self.known_ids = dict(known_ids or {})
        self.clock = clock
        self.streams = {}
        self.alerts = []
        self.dropped_frames = 0

    def process_datagram(self, datagram, source_addr):
        messages, dropped = parse_mavlink_v2_datagram(datagram)
        self.dropped_frames += dropped
        reports = []
        for msg in messages:
            if msg['msgid'] != 33:
                continue
            key = (source_addr, msg['sysid'], msg['compid'])
            state = self.streams.setdefault(key, dict(offset=self.clock()-msg['time_boot_ms']/1000., history=deque(maxlen=5), outside=0))
            epoch = state['offset']+msg['time_boot_ms']/1000.
            x, y = lonlat_to_utm12n(msg['lon_deg'], msg['lat_deg'])
            wp = Waypoint4D(msg['lat_deg'],msg['lon_deg'],msg['alt_m'],epoch,x,y)
            state['history'].append(wp)
            plan = next((p for p in self.plans if p.plan_id == self.known_ids.get(key)), None)
            status = TrackMatchStatus.MATCHED_KNOWN_ID if plan else TrackMatchStatus.UNMATCHED
            if plan is None and len(state['history']) == 5:
                scores = []
                for p in self.plans:
                    tunnel = p.tunnel or build_tunnel(p.plan_id,p.waypoints)
                    if any(w.epoch_s < p.waypoints[0].epoch_s-tunnel.time_buf_s or w.epoch_s > p.waypoints[-1].epoch_s+tunnel.time_buf_s for w in state['history']):
                        continue
                    error = sum((w.x_m-interpolate(p,w.epoch_s).x_m)**2+(w.y_m-interpolate(p,w.epoch_s).y_m)**2+(w.alt_m-interpolate(p,w.epoch_s).alt_m)**2 for w in state['history'])
                    scores.append((math.sqrt(error/5),p.plan_id,p))
                scores.sort(key=lambda item: (item[0],item[1]))
                if scores and scores[0][0] <= 150:
                    if len(scores)==1 or (scores[1][0] >= 2*scores[0][0] and scores[1][0] > scores[0][0]):
                        plan, status = scores[0][2], TrackMatchStatus.MATCHED_TRAJECTORY
                    else:
                        status = TrackMatchStatus.AMBIGUOUS
            outside = False
            if plan:
                expected = interpolate(plan,epoch)
                tunnel = plan.tunnel or build_tunnel(plan.plan_id,plan.waypoints)
                outside = (math.hypot(x-expected.x_m,y-expected.y_m)>tunnel.horiz_half_width_m or abs(wp.alt_m-expected.alt_m)>tunnel.vert_margin_m or epoch<plan.waypoints[0].epoch_s-tunnel.time_buf_s or epoch>plan.waypoints[-1].epoch_s+tunnel.time_buf_s)
            state['outside'] = state['outside']+1 if outside else 0
            report = TrackReport(key,wp,status,plan.plan_id if plan else None,outside,state['outside']>=2)
            if state['outside']==2:
                self.alerts.append(ConflictRecord(uuid4().hex,'LIVE_DRIFT',plan.plan_id,'',epoch,epoch,math.hypot(x-expected.x_m,y-expected.y_m),abs(wp.alt_m-expected.alt_m),None,'ALERT','Two consecutive reports outside tunnel; not authenticated'))
            reports.append(report)
        return reports

    def compute_reroute(self, report, active_plans, zones, weather):
        from .planner import plan_4d_path
        original = next(p for p in self.plans if p.plan_id==report.plan_id)
        goal = original.waypoints[-1]
        result = plan_4d_path(report.waypoint,goal.lat_deg,goal.lon_deg,goal.alt_m,original.limits,original.radio,'shortest_time',zones,[p for p in active_plans if p.plan_id!=original.plan_id],weather)
        if result.plan:
            result.plan = replace(result.plan,plan_id=uuid4().hex,callsign=original.callsign,priority=original.priority,status='DRAFT')
            result.plan.tunnel = build_tunnel(result.plan.plan_id,result.plan.waypoints)
        return result

    def accept_reroute(self, conn, result, original_plan_id, expected_revision):
        from .db import approve_and_persist_plan
        if result.plan is None:
            raise ValueError('No re-route to accept')
        revision = approve_and_persist_plan(conn,result.plan,expected_revision,supersede_plan_id=original_plan_id)
        self.plans = [p for p in self.plans if p.plan_id!=original_plan_id]+[result.plan]
        self.known_ids = {k: result.plan.plan_id if v==original_plan_id else v for k,v in self.known_ids.items()}
        return revision


class UDPReceiver:
    def __init__(self, port=0):
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1',port))
        self.socket.setblocking(False)
        self.address = self.socket.getsockname()

    def poll(self, tracker):
        reports = []
        while True:
            try:
                data, address = self.socket.recvfrom(65535)
            except BlockingIOError:
                return reports
            reports.extend(tracker.process_datagram(data,address))

    def close(self):
        self.socket.close()
