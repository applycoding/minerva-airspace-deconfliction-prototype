import json
import math
from dataclasses import asdict
import pytest
from shapely.geometry import Point, Polygon, shape
from minerva.coords import *
from minerva.models import PlannerStatus, TrackMatchStatus
from minerva.tunnel import build_tunnel, export_tunnel_json, export_tunnel_geojson


@pytest.mark.parametrize('lon,lat', [(-111.18,50.27),(-114.,50.),(-108.,51.),(-110.59654722,50.3375)])
def test_projection_round_trip(lon, lat):
    x,y=lonlat_to_utm12n(lon,lat)
    assert 200000 < x < 800000 and 5500000 < y < 5800000
    out=utm12n_to_lonlat(x,y)
    x2,y2=lonlat_to_utm12n(*out)
    assert math.hypot(x-x2,y-y2) < .01
    assert out == pytest.approx((lon,lat),abs=1e-10)


def test_units_and_models(plan):
    assert feet_to_metres(15000)==4572.
    assert knots_to_mps(10)==pytest.approx(5.14444)
    assert nm_to_metres(3)==5556.
    assert dms_to_deg(110,35,47.57,'W')==pytest.approx(-110.59654722222222)
    assert len(PlannerStatus)==5 and len(TrackMatchStatus)==4
    assert asdict(plan)['radio']['guard_mhz']==2.
    assert plan.waypoints[0].lat_deg==50.1


def test_circle_conservative():
    polygon=Polygon(build_conservative_circle_utm(-111.18333333,50.26666667,5556))
    x,y=lonlat_to_utm12n(-111.18333333,50.26666667)
    assert len(polygon.exterior.coords)==257 and polygon.is_valid
    for i in range(1024):
        angle=i*2*math.pi/1024
        assert polygon.covers(Point(x+5556*math.cos(angle),y+5556*math.sin(angle)))
    assert polygon.contains(Point(x+5500,y))
    assert not polygon.contains(Point(x+5600,y))


def test_tunnel_bounds_exports(plan,tmp_path):
    plan.tunnel=build_tunnel(plan.plan_id,plan.waypoints)
    t=plan.tunnel
    assert len(t.segments)==2
    assert (t.width_m,t.low_m,t.high_m,t.start_epoch_s,t.end_epoch_s)==(200.,70.,190.,985.,1135.)
    assert (t.segments[0].low_m,t.segments[0].high_m,t.segments[0].start_epoch_s,t.segments[0].end_epoch_s)==(70.,190.,985.,1075.)
    jp,gp=tmp_path/'t.json',tmp_path/'t.geojson'
    export_tunnel_json(t,jp); export_tunnel_geojson(plan,gp)
    out=json.loads(jp.read_text())
    assert out['start_epoch_s']=='1970-01-01T00:16:25Z'
    assert out['width_m']==200.
    geo=json.loads(gp.read_text())
    assert geo['type']=='FeatureCollection' and len(geo['features'])==2
    for feature, segment in zip(geo['features'],t.segments):
        geometry=shape(feature['geometry'])
        assert geometry.is_valid and geometry.geom_type=='Polygon' and geometry.area>0
        assert geometry.contains(Point(plan.waypoints[segment.seg_index].lon_deg,plan.waypoints[segment.seg_index].lat_deg))
        assert feature['properties']['high_m']==segment.high_m
        for lon,lat in geometry.exterior.coords:
            assert -112<lon<-111 and 50<lat<51


@pytest.mark.parametrize('half,vertical,buffer', [(0,30,15),(100,-1,15),(100,30,-1),(float('nan'),30,15)])
def test_tunnel_rejects_margins(plan,half,vertical,buffer):
    with pytest.raises(ValueError): build_tunnel(plan.plan_id,plan.waypoints,half,vertical,buffer)


def test_tunnel_stationary_and_surface(plan):
    plan.waypoints[1].x_m=plan.waypoints[0].x_m
    plan.waypoints[1].y_m=plan.waypoints[0].y_m
    plan.waypoints[0].alt_m=0
    tunnel=build_tunnel(plan.plan_id,plan.waypoints)
    assert tunnel.low_m==0
    plan.waypoints[1].epoch_s=plan.waypoints[0].epoch_s
    with pytest.raises(ValueError): build_tunnel(plan.plan_id,plan.waypoints)


def test_gui_shell(qapp):
    from minerva.gui.main_window import MainWindow
    window=MainWindow(); window.show(); qapp.processEvents()
    assert window.isVisible() and 'MINERVA' in window.windowTitle()
    window.close()
