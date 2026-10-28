import ipaddress
import socket
import pytest
from minerva.coords import lonlat_to_utm12n
from minerva.models import Waypoint4D, DroneLimits, RadioSpec, FlightPlan


@pytest.fixture(autouse=True)
def no_external_connections(monkeypatch):
    connect, connect_ex, sendto, getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto, socket.getaddrinfo
    def check(host):
        if host == 'localhost':
            return
        try:
            if ipaddress.ip_address(host).is_loopback:
                return
        except ValueError:
            pass
        raise AssertionError('External network access is forbidden')
    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            check(address[0])
        return connect(sock, address)
    def guarded_connect_ex(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            check(address[0])
        return connect_ex(sock, address)
    def guarded_sendto(sock, data, *args):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            check(args[-1][0])
        return sendto(sock, data, *args)
    def guarded_resolve(host, *args, **kwargs):
        check(host)
        return getaddrinfo(host, *args, **kwargs)
    monkeypatch.setattr(socket.socket, 'connect', guarded_connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', guarded_connect_ex)
    monkeypatch.setattr(socket.socket, 'sendto', guarded_sendto)
    monkeypatch.setattr(socket, 'getaddrinfo', guarded_resolve)


@pytest.fixture
def plan():
    wps = []
    for lon, lat, alt, epoch in [(-111.4, 50.1, 100., 1000.), (-111.39, 50.11, 160., 1060.), (-111.38, 50.12, 120., 1120.)]:
        x, y = lonlat_to_utm12n(lon, lat)
        wps.append(Waypoint4D(lat, lon, alt, epoch, x, y))
    return FlightPlan('p1', 'TEST1', 2, 'DRAFT', 900., DroneLimits(35., 5., 4., 100., 15.), RadioSpec(2400., 10., 20., 2., 2., -90., 50.1, -111.4, wps[0].x_m, wps[0].y_m), wps, None)


@pytest.fixture
def conn(tmp_path):
    from minerva.db import init_db
    connection = init_db(tmp_path / 'state.sqlite3')
    yield connection
    connection.close()


@pytest.fixture(scope='session')
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
