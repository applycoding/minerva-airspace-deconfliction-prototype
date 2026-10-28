import math
from pyproj import Transformer

_FORWARD = Transformer.from_crs(4326, 32612, always_xy=True)
_INVERSE = Transformer.from_crs(32612, 4326, always_xy=True)

def lonlat_to_utm12n(lon_deg, lat_deg):
    return _FORWARD.transform(lon_deg, lat_deg, errcheck=True)

def utm12n_to_lonlat(x_m, y_m):
    return _INVERSE.transform(x_m, y_m, errcheck=True)

def feet_to_metres(feet):
    return feet * 0.3048

def knots_to_mps(knots):
    return knots * 0.514444

def nm_to_metres(nm):
    return nm * 1852.0

def dms_to_deg(deg, minutes, seconds, hemi):
    if hemi not in ('N', 'S', 'E', 'W') or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        raise ValueError('Invalid DMS coordinate')
    return (abs(deg) + minutes / 60 + seconds / 3600) * (-1 if hemi in ('S', 'W') else 1)

def build_conservative_circle_utm(center_lon, center_lat, radius_m, n_vertices=256):
    if n_vertices < 3 or not math.isfinite(radius_m) or radius_m <= 0:
        raise ValueError('Invalid circle dimensions')
    x, y = lonlat_to_utm12n(center_lon, center_lat)
    radius = radius_m / math.cos(math.pi / n_vertices) + 1e-8
    return [(x + radius * math.cos(i * 2 * math.pi / n_vertices),
             y + radius * math.sin(i * 2 * math.pi / n_vertices)) for i in range(n_vertices)]
