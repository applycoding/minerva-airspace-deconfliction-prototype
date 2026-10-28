"""Repeatable simulation fixtures and measured scale evidence."""
from dataclasses import replace
import os
import platform
from pathlib import Path
import statistics
import time
import numpy as np
from shapely.geometry import Polygon
from ..models import Waypoint4D, DroneLimits, RadioSpec, FlightPlan, WeatherObservation
from ..coords import utm12n_to_lonlat


def waypoint(x, y, z=100., t=0.):
    lon,lat = utm12n_to_lonlat(x,y)
    return Waypoint4D(lat,lon,z,t,x,y)


def make_plan(plan_id, coordinates):
    wps = [waypoint(*p) for p in coordinates]
    return FlightPlan(plan_id,plan_id,2,'APPROVED',0.,DroneLimits(100.,10.,10.,0.,15.),RadioSpec(2400.,10.,20.,2.,2.,-90.,wps[0].lat_deg,wps[0].lon_deg,wps[0].x_m,wps[0].y_m),wps,None)


def calm_weather():
    return WeatherObservation('SYN',-1e12,1e12,0.,0.,0.,True)


def build_t1_scenarios(seed=1101):
    rng = np.random.Generator(np.random.PCG64(seed))
    scenarios = []
    excluded = 0
    for planted in (True,False):
        count = 0
        while count < 100:
            lateral = float(rng.uniform(0.,200.))
            vertical = float(rng.uniform(0.,60.))
            inside = lateral <= 90. and vertical <= 27.
            outside = lateral >= 110. or vertical >= 33.
            if not (inside or outside):
                excluded += 1
                continue
            if inside != planted:
                continue
            speed = float(rng.uniform(10.,200.))
            origin = rng.uniform(-10000,10000,size=2)
            a = make_plan('a',[(origin[0]-speed*5,origin[1],100.,0.),(origin[0]+speed*5,origin[1],100.,10.)])
            b = make_plan('b',[(origin[0]+speed*5,origin[1]+lateral,100.+vertical,0.),(origin[0]-speed*5,origin[1]+lateral,100.+vertical,10.)])
            scenarios.append((a,b,planted)); count += 1
    return dict(scenarios=scenarios,excluded_band_count=excluded,seed=seed)


def hand_space_time_fixtures():
    def leg(points):
        return tuple(waypoint(*p) for p in points)
    base = leg([(0,0,100,0),(1000,0,100,10)])
    return [
        ('grazing',base,leg([(0,100,100,0),(1000,100,100,10)]),False),
        ('endpoint',base,leg([(1000,0,100,10),(2000,0,100,20)]),True),
        ('stationary',leg([(0,0,100,-15),(0,0,100,0)]),leg([(-200,0,100,-10),(200,0,100,-2)]),True),
        ('equal_velocity',base,leg([(0,50,110,0),(1000,50,110,10)]),True),
        ('sub_sample',leg([(-1234,0,100,0),(8766,0,100,1)]),leg([(0,0,100,0),(0,0,100,1)]),True),
        ('parallel',base,leg([(0,110,100,0),(1000,110,100,10)]),False),
    ]


def build_t2_scenarios(seed=2202):
    rng = np.random.Generator(np.random.PCG64(seed))
    result = []
    for i in range(50):
        plans = []
        for name in ('a','b'):
            xyz = rng.uniform([-5000,-5000,2],[5000,5000,1000],size=(3,3))
            plan = make_plan(name,[(*p,float(j*10)) for j,p in enumerate(xyz)])
            plan.radio = replace(plan.radio,freq_mhz=float(rng.choice([900.,905.,920.])),tx_power_dbm=float(rng.uniform(-10,40)),rx_threshold_dbm=float(rng.uniform(-110,-40)),gcs_x_m=float(rng.uniform(-5000,5000)),gcs_y_m=float(rng.uniform(-5000,5000)),guard_mhz=float(rng.uniform(0,5)))
            plans.append(plan)
        result.append(tuple(plans))
    return result


def build_t3_scenarios(zones):
    """Isolate each polygon using its representative point and western edge."""
    result = []
    for zone in zones:
        polygon = Polygon(zone.polygon_utm)
        centre = polygon.representative_point()
        for altitude,expected in ((100.,True),(zone.ceiling_m+31.,False)):
            plan = make_plan('zone',[(centre.x,centre.y,altitude,1775001600.),(centre.x+1,centre.y,altitude,1775001610.)])
            result.append((plan,zone,expected))
    return result


def build_t5_scenario(count, seed=5505):
    rng = np.random.Generator(np.random.PCG64(seed))
    candidate = make_plan('candidate',[(0,0,100,0),(2000,0,100,100)])
    plans = []
    for i in range(count):
        x,y = rng.uniform(-20000,20000,size=2)
        if i % 10 == 0:
            x,y = 1000.,-1000.
        plan = make_plan(f'p{i}',[(x,y,100.,0.),(x,y+2000,100.,100.)])
        if i % 3:
            plan.radio.freq_mhz = 5800.
        plans.append(plan)
    return candidate,plans


def runner_info():
    ram = None
    if platform.system() == 'Windows':
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in ('total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','extended')]
        status = MemoryStatus(); status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            ram = status.total_phys
    elif hasattr(os,'sysconf'):
        ram = os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')
    cpu = platform.processor() or platform.machine()
    if Path('/proc/cpuinfo').is_file():
        cpu = next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),cpu)
    return dict(system=platform.platform(),python=platform.python_version(),cpu=cpu,logical_cpus=os.cpu_count(),ram_bytes=ram)


def benchmark_t5(repeats=5):
    from ..conflict import SpatialIndex, check_all_conflicts
    from dataclasses import asdict
    report = dict(runner=runner_info(),repeats=repeats,counts={})
    for count in (10,50,200,500):
        candidate,plans = build_t5_scenario(count)
        index = SpatialIndex(plans)
        durations = dict(exhaustive=[],indexed=[])
        for _ in range(repeats):
            outputs = []
            for mode,idx in (('exhaustive',None),('indexed',index)):
                start = time.perf_counter()
                output = check_all_conflicts(candidate,plans,[],calm_weather(),index=idx)
                durations[mode].append(time.perf_counter()-start)
                outputs.append([asdict(r) for r in output])
            if outputs[0] != outputs[1]:
                raise AssertionError('Indexed and exhaustive conflict sets differ')
        report['counts'][count] = {mode:dict(median_s=statistics.median(values),p95_s=float(np.percentile(values,95))) for mode,values in durations.items()}
        report['counts'][count]['identical'] = True
        report['counts'][count]['conflict_count'] = len(outputs[0])
    return report
