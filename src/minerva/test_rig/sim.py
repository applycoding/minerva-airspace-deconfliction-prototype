"""Loopback-only simulated telemetry; never commands aircraft."""
import socket
import struct
from ..live import encode_mavlink_v2_frame


class VirtualClock:
    def __init__(self, epoch_s=1000.):
        self.epoch_s = epoch_s

    def __call__(self):
        return self.epoch_s

    def advance(self, seconds):
        self.epoch_s += seconds


class SimulatedDrone:
    def __init__(self, destination, clock, sysid=1, compid=1):
        if destination[0] != '127.0.0.1':
            raise ValueError('Simulation uses 127.0.0.1 only')
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket.bind(('127.0.0.1',0))
        self.address = self.socket.getsockname()
        self.destination, self.clock = destination, clock
        self.start = clock()
        self.sysid, self.compid, self.seq = sysid, compid, 0

    def send(self, waypoint):
        payload = struct.pack('<IiiiihhhH',round((self.clock()-self.start)*1000),round(waypoint.lat_deg*1e7),round(waypoint.lon_deg*1e7),round((waypoint.alt_m+700)*1000),round(waypoint.alt_m*1000),0,0,0,0)
        heartbeat = encode_mavlink_v2_frame(0,struct.pack('<IBBBBB',0,2,0,0,4,3),self.sysid,self.compid,self.seq)
        frame = encode_mavlink_v2_frame(33,payload,self.sysid,self.compid,self.seq)
        self.socket.sendto(heartbeat+frame,self.destination)
        self.seq = (self.seq+1)%256

    def close(self):
        self.socket.close()
