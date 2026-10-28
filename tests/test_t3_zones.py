import json
import math
from pathlib import Path
import pytest
from shapely.geometry import Polygon, Point
from minerva.ingest import *
from minerva.coords import lonlat_to_utm12n
from minerva.models import WeatherObservation

DATA=Path('data')


def test_ingest_exact_vertices():
    zones=load_zones_geojson(DATA/'zones/suffield.geojson')
    assert [z.zone_id for z in zones]==['CYR229','CYR230','CYR231']
    expected229=[(-111.16666667,50.3375),(-111.16666667,50.58333333),(-111.08333333,50.71666667),(-110.28333333,50.71666667),(-110.28333333,50.61666667),(-110.41666667,50.41666667),(-110.46666667,50.38333333),(-110.58888889,50.38333333),(-110.59654722,50.3375)]
    expected230=[(-111.16666667,50.25),(-111.16666667,50.3375),(-110.59654722,50.3375),(-110.61666667,50.21666667),(-111.12222222,50.21666667)]
    assert zones[0].polygon_wgs84==expected229
    assert zones[1].polygon_wgs84==expected230
    raw=json.loads((DATA/'zones/suffield.geojson').read_text())
    assert len(raw['features'][0]['geometry']['coordinates'][0])==10
    assert len(raw['features'][1]['geometry']['coordinates'][0])==6
    for z in zones:
        assert z.handbook_issue=='TP 1820E (2026-09-03 to 2026-10-29)'
        assert Polygon(z.polygon_utm).is_valid
    assert len(zones[2].polygon_utm)==256
    x,y=lonlat_to_utm12n(-111.18333333,50.26666667)
    assert Polygon(zones[2].polygon_utm).contains(Point(x+5500,y))
    assert not Polygon(zones[2].polygon_utm).contains(Point(x+5600,y))


@pytest.mark.parametrize('instant,ceiling', [('2026-03-31T23:59:59Z',4572.),('2026-04-01T00:00:00Z',100000.),('2026-12-01T06:59:59Z',100000.),('2026-12-01T07:00:30Z',100000.),('2026-12-01T07:01:00Z',4572.),('2026-12-01T07:01:01Z',4572.),('2027-04-01T00:00:00Z',100000.)])
def test_ingest_seasonal(instant,ceiling):
    zones=load_zones_geojson(DATA/'zones/suffield.geojson')
    assert is_zone_active(zones[0],parse_utc(instant))==(True,0.,ceiling)
    assert is_zone_active(zones[1],parse_utc(instant))==(True,0.,100000.)
    assert is_zone_active(zones[2],parse_utc(instant))==(True,0.,1828.8)


def test_ingest_overrides(tmp_path):
    path=tmp_path/'override.json';path.write_text(json.dumps({'CYR229':{'active':False,'ceiling_m':999.}}))
    zone=load_zones_geojson(DATA/'zones/suffield.geojson',path)[0]
    assert is_zone_active(zone,parse_utc('2026-04-01T00:00:00Z'))==(False,0.,999.)
    path.write_text(json.dumps({'CYR229':{'active':'false'}}))
    with pytest.raises(ValueError): load_zones_geojson(DATA/'zones/suffield.geojson',path)


def test_ingest_crewed_metres_and_feet(tmp_path):
    source=DATA/'crewed/sample_crewed_plans.json'
    plan=load_crewed_plans(source)[0]
    assert plan.is_crewed and plan.status=='CREWED_ACTIVE'
    assert plan.waypoints[0].alt_m==914.4
    data=json.loads(source.read_text());data['plans'][0]['waypoints'][0]['altitude']='123 m'
    path=tmp_path/'m.json';path.write_text(json.dumps(data))
    assert load_crewed_plans(path)[0].waypoints[0].alt_m==123.
    text=tmp_path/'plan.txt'
    text.write_text('PLAN c1 CTEST\nWP 50.1 -111.4 3000 ft 2026-10-28T12:00:00Z\nWP 50.15 -111.3 1000 m 2026-10-28T12:05:00Z\nEND\n')
    imported=load_crewed_plans(text)[0]
    assert [w.alt_m for w in imported.waypoints]==[914.4,1000.]
    assert imported.waypoints[0].x_m==pytest.approx(plan.waypoints[0].x_m)


@pytest.mark.parametrize('altitude', ['FL100','F100','fl 100'])
def test_ingest_rejects_fl(tmp_path,altitude):
    data=json.loads((DATA/'crewed/sample_crewed_plans.json').read_text())
    data['plans'][0]['waypoints'][0]['altitude']=altitude
    path=tmp_path/'fl.json';path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match=r'Flight levels \(FL\) are not supported; specify altitude in feet or metres above ground reference'): load_crewed_plans(path)


def test_ingest_metar_and_weather_policy(conn):
    calm=parse_weather_text(DATA/'weather/cyxh_metar_calm.txt')[0]
    high=parse_weather_text(DATA/'weather/cyxh_metar_highwind.txt')[0]
    assert calm.station_id=='CYXH' and calm.wind_speed_mps==0 and calm.gust_mps==0
    assert high.wind_from_deg==270 and high.wind_speed_mps==pytest.approx(25*.514444) and high.gust_mps==pytest.approx(40*.514444)
    assert max(high.wind_speed_mps,high.gust_mps)>15
    start,end=calm.valid_start_epoch_s,calm.valid_end_epoch_s
    assert resolve_weather_for_window([calm],start,end)==calm
    assert resolve_weather_for_window([calm],start,end+1) is None
    synthetic=WeatherObservation('SYN',start,end+3600,0,2,3,True)
    assert resolve_weather_for_window([],start,end+1,synthetic)==synthetic
    assert resolve_weather_for_window([],start,end+7200,synthetic) is None
    from minerva.db import save_weather
    save_weather(conn,[calm])
    assert resolve_weather_for_window(conn,start,end)==calm
    assert resolve_weather_for_window(conn,start,end+1) is None


@pytest.mark.parametrize('wind',['VRB05KT','40010KT','270XXKT'])
def test_ingest_bad_weather(tmp_path,wind):
    path=tmp_path/'bad.txt';path.write_text(f'2026-10-28T12:00:00Z/2026-10-28T13:00:00Z METAR CYXH 281200Z {wind} CAVOK\n')
    with pytest.raises(ValueError): parse_weather_text(path)


from dataclasses import replace
from minerva.conflict import check_zone_conflicts
from minerva.test_rig.scenarios import build_t3_scenarios, make_plan
from minerva.tunnel import build_tunnel


def test_t3_isolated_zones():
    zones = load_zones_geojson(DATA/'zones/suffield.geojson')
    scenarios = build_t3_scenarios(zones)
    assert len(scenarios) == 6
    for plan,zone,expected in scenarios:
        assert bool(check_zone_conflicts(plan,[zone])) == expected


@pytest.mark.parametrize('zone_index',[0,1,2])
def test_t3_tunnel_margins(zone_index):
    zone = load_zones_geojson(DATA/'zones/suffield.geojson')[zone_index]
    polygon = Polygon(zone.polygon_utm)
    centre = polygon.representative_point()
    # The nearest point on the western boundary gives a known outward direction.
    from shapely.ops import nearest_points
    west = Point(polygon.bounds[0]-1000,centre.y)
    edge = nearest_points(polygon,west)[0]
    dx,dy = west.x-edge.x,west.y-edge.y
    norm = math.hypot(dx,dy); dx/=norm; dy/=norm
    t = parse_utc('2026-06-01T12:00:00Z')
    for offset,expected in ((99.,True),(101.,False)):
        x,y = edge.x+dx*offset,edge.y+dy*offset
        plan = make_plan('lateral',[(x,y,100,t),(x,y,100,t+10)])
        assert bool(check_zone_conflicts(plan,[zone])) == expected
    for altitude,expected in ((zone.ceiling_m+29.,True),(zone.ceiling_m+31.,False)):
        plan = make_plan('vertical',[(centre.x,centre.y,altitude,t),(centre.x,centre.y,altitude,t+10)])
        assert bool(check_zone_conflicts(plan,[zone])) == expected
    plan.tunnel = build_tunnel(plan.plan_id,plan.waypoints,vert_margin_m=40.)
    assert check_zone_conflicts(plan,[zone])
    assert not check_zone_conflicts(plan,[replace(zone,override_active=False)])


@pytest.mark.parametrize('instant,expected',[
    ('2026-03-31T23:59:59Z',False),('2026-04-01T00:00:00Z',True),
    ('2026-12-01T06:59:59Z',True),('2026-12-01T07:00:30Z',True),
    ('2026-12-01T07:01:01Z',False)])
def test_t3_transition_instants(instant,expected):
    zone = load_zones_geojson(DATA/'zones/suffield.geojson')[0]
    c = Polygon(zone.polygon_utm).representative_point()
    t = parse_utc(instant)
    plan = make_plan('season',[(c.x,c.y,5000,t),(c.x,c.y,5000,t+.01)])
    plan.tunnel = build_tunnel(plan.plan_id,plan.waypoints,time_buf_s=0)
    assert bool(check_zone_conflicts(plan,[zone])) == expected


def test_t3_crossing_season_and_buffer_hold():
    zone = load_zones_geojson(DATA/'zones/suffield.geojson')[0]
    c = Polygon(zone.polygon_utm).representative_point()
    t = parse_utc('2026-04-01T00:00:00Z')
    plan = make_plan('crossing',[(c.x,c.y,5000,t-10),(c.x,c.y,5000,t+10)])
    records = check_zone_conflicts(plan,[zone])
    assert records and min(r.start_epoch_s for r in records) == t
    plan = make_plan('hold',[(c.x,c.y,5000,t-20),(c.x,c.y,5000,t-5)])
    assert check_zone_conflicts(plan,[zone])
    plan.tunnel = build_tunnel(plan.plan_id,plan.waypoints,time_buf_s=0)
    assert not check_zone_conflicts(plan,[zone])
