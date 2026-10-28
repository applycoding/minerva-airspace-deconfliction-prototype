from dataclasses import dataclass
from enum import Enum

class PlannerStatus(str, Enum):
    FOUND = "FOUND"
    NO_PATH_WITHIN_GRID = "NO_PATH_WITHIN_GRID"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    REJECTED_WEATHER = "REJECTED_WEATHER"
    REJECTED_START_GOAL = "REJECTED_START_GOAL"

class TrackMatchStatus(str, Enum):
    MATCHED_KNOWN_ID = "MATCHED_KNOWN_ID"
    MATCHED_TRAJECTORY = "MATCHED_TRAJECTORY"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"

@dataclass
class Waypoint4D:
    lat_deg: float
    lon_deg: float
    alt_m: float
    epoch_s: float
    x_m: float = 0.0
    y_m: float = 0.0

@dataclass
class DroneLimits:
    max_airspeed_mps: float
    max_climb_mps: float
    max_descent_mps: float
    min_turn_radius_m: float
    max_wind_mps: float
    hover_allowed: bool = False

@dataclass
class RadioSpec:
    freq_mhz: float
    bw_mhz: float
    tx_power_dbm: float
    tx_gain_dbi: float
    rx_gain_dbi: float
    rx_threshold_dbm: float
    gcs_lat_deg: float
    gcs_lon_deg: float
    gcs_x_m: float = 0.0
    gcs_y_m: float = 0.0
    guard_mhz: float = 2.0
    radio_model: str = "Custom"

@dataclass
class TunnelSegment4D:
    seg_index: int
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float
    horiz_half_width_m: float
    vert_margin_m: float
    low_m: float
    high_m: float
    start_epoch_s: float
    end_epoch_s: float

@dataclass
class Tunnel4D:
    plan_id: str
    width_m: float
    horiz_half_width_m: float
    vert_margin_m: float
    time_buf_s: float
    low_m: float
    high_m: float
    start_epoch_s: float
    end_epoch_s: float
    segments: list[TunnelSegment4D]

@dataclass
class FlightPlan:
    plan_id: str
    callsign: str
    priority: int
    status: str
    created_epoch_s: float
    limits: DroneLimits
    radio: RadioSpec
    waypoints: list[Waypoint4D]
    tunnel: Tunnel4D | None
    is_crewed: bool = False

@dataclass
class RestrictedZone:
    zone_id: str
    name: str
    polygon_wgs84: list[tuple[float, float]]
    polygon_utm: list[tuple[float, float]]
    floor_m: float
    ceiling_m: float
    seasonal_rule: str
    handbook_issue: str
    source_note: str
    override_active: bool | None = None
    override_ceiling_m: float | None = None

@dataclass
class WeatherObservation:
    station_id: str
    valid_start_epoch_s: float
    valid_end_epoch_s: float
    wind_from_deg: float
    wind_speed_mps: float
    gust_mps: float
    is_synthetic: bool = False
    raw_text: str = ""

@dataclass
class ConflictRecord:
    conflict_id: str
    kind: str
    plan_a_id: str
    plan_b_or_zone_id: str
    start_epoch_s: float
    end_epoch_s: float
    min_horiz_m: float
    min_vert_m: float
    rx_power_dbm: float | None
    severity: str
    description: str

@dataclass
class PlannerResult:
    status: PlannerStatus
    plan: FlightPlan | None
    expansions: int
    elapsed_s: float
    message: str

@dataclass
class ResolutionProposal:
    original_plan_id: str
    action_type: str
    summary: str
    modified_plan: FlightPlan | None
    requires_operator: bool
    conflicts_remaining: int

