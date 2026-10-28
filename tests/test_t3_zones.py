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


@pytest.mark.parametrize('instant,ceiling', [('2026-03-31T23:59:59Z',4572.),('2026-04-01T00:00:00Z',100000.),('2026-12-01T06:59:59Z',100000.),('2026-12-01T07:00:01Z',4572.),('2026-12-01T07:00:00Z',4572.),('2027-04-01T00:00:00Z',100000.)])
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
