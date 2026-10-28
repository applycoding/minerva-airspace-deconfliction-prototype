CREATE TABLE IF NOT EXISTS db_state_meta (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    revision            INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO db_state_meta (id, revision) VALUES (1, 0);

CREATE TABLE IF NOT EXISTS flight_plans (
    plan_id             TEXT PRIMARY KEY,
    callsign            TEXT NOT NULL,
    priority            INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 4),
    status              TEXT NOT NULL CHECK (status IN ('DRAFT','APPROVED','REJECTED','SUPERSEDED','CREWED_ACTIVE')),
    is_crewed           INTEGER NOT NULL DEFAULT 0 CHECK (is_crewed IN (0, 1)),
    created_epoch_s     REAL NOT NULL,
    max_airspeed_mps    REAL NOT NULL CHECK (max_airspeed_mps > 0),
    max_climb_mps       REAL NOT NULL CHECK (max_climb_mps > 0),
    max_descent_mps     REAL NOT NULL CHECK (max_descent_mps > 0),
    min_turn_radius_m   REAL NOT NULL CHECK (min_turn_radius_m >= 0),
    max_wind_mps        REAL NOT NULL CHECK (max_wind_mps >= 0),
    hover_allowed       INTEGER NOT NULL DEFAULT 0 CHECK (hover_allowed IN (0, 1))
);

CREATE TABLE IF NOT EXISTS waypoints_4d (
    plan_id             TEXT NOT NULL REFERENCES flight_plans(plan_id) ON DELETE CASCADE,
    seq_index           INTEGER NOT NULL,
    lat_deg             REAL NOT NULL CHECK (lat_deg BETWEEN -90.0 AND 90.0),
    lon_deg             REAL NOT NULL CHECK (lon_deg BETWEEN -180.0 AND 180.0),
    x_m                 REAL NOT NULL,
    y_m                 REAL NOT NULL,
    alt_m               REAL NOT NULL CHECK (alt_m >= 0.0),
    epoch_s             REAL NOT NULL,
    PRIMARY KEY (plan_id, seq_index)
);

CREATE TABLE IF NOT EXISTS radio_allocations (
    plan_id             TEXT PRIMARY KEY REFERENCES flight_plans(plan_id) ON DELETE CASCADE,
    radio_model         TEXT NOT NULL,
    freq_mhz            REAL NOT NULL CHECK (freq_mhz > 0),
    bw_mhz              REAL NOT NULL CHECK (bw_mhz > 0),
    guard_mhz           REAL NOT NULL DEFAULT 2.0 CHECK (guard_mhz >= 0),
    tx_power_dbm        REAL NOT NULL,
    tx_gain_dbi         REAL NOT NULL,
    rx_gain_dbi         REAL NOT NULL,
    rx_threshold_dbm    REAL NOT NULL,
    gcs_lat_deg         REAL NOT NULL CHECK (gcs_lat_deg BETWEEN -90.0 AND 90.0),
    gcs_lon_deg         REAL NOT NULL CHECK (gcs_lon_deg BETWEEN -180.0 AND 180.0),
    gcs_x_m             REAL NOT NULL,
    gcs_y_m             REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tunnels_4d (
    plan_id             TEXT PRIMARY KEY REFERENCES flight_plans(plan_id) ON DELETE CASCADE,
    width_m             REAL NOT NULL CHECK (width_m > 0),
    horiz_half_width_m  REAL NOT NULL CHECK (horiz_half_width_m > 0),
    vert_margin_m       REAL NOT NULL CHECK (vert_margin_m > 0),
    time_buf_s          REAL NOT NULL CHECK (time_buf_s >= 0),
    low_m               REAL NOT NULL,
    high_m              REAL NOT NULL CHECK (high_m >= low_m),
    start_epoch_s       REAL NOT NULL,
    end_epoch_s         REAL NOT NULL CHECK (end_epoch_s > start_epoch_s)
);

CREATE TABLE IF NOT EXISTS tunnel_segments_4d (
    plan_id             TEXT NOT NULL REFERENCES flight_plans(plan_id) ON DELETE CASCADE,
    seg_index           INTEGER NOT NULL,
    start_x_m           REAL NOT NULL,
    start_y_m           REAL NOT NULL,
    end_x_m             REAL NOT NULL,
    end_y_m             REAL NOT NULL,
    horiz_half_width_m  REAL NOT NULL,
    vert_margin_m       REAL NOT NULL,
    low_m               REAL NOT NULL,
    high_m              REAL NOT NULL,
    start_epoch_s       REAL NOT NULL,
    end_epoch_s         REAL NOT NULL,
    PRIMARY KEY (plan_id, seg_index)
);

CREATE TABLE IF NOT EXISTS restricted_zones (
    zone_id             TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    polygon_wgs84_json  TEXT NOT NULL,
    floor_m             REAL NOT NULL,
    ceiling_m           REAL NOT NULL,
    seasonal_rule       TEXT NOT NULL,
    handbook_issue      TEXT NOT NULL,
    source_note         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weather_observations (
    obs_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id          TEXT NOT NULL,
    valid_start_epoch_s REAL NOT NULL,
    valid_end_epoch_s   REAL NOT NULL,
    wind_from_deg       REAL NOT NULL,
    wind_speed_mps      REAL NOT NULL,
    gust_mps            REAL NOT NULL,
    is_synthetic        INTEGER NOT NULL DEFAULT 0,
    raw_text            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conflict_logs (
    conflict_id         TEXT PRIMARY KEY,
    detected_epoch_s    REAL NOT NULL,
    kind                TEXT NOT NULL CHECK (kind IN ('SPACE_TIME','RADIO','NO_FLY_ZONE','WEATHER_WIND','LIVE_DRIFT')),
    plan_a_id           TEXT NOT NULL,
    plan_b_or_zone_id   TEXT NOT NULL,
    start_epoch_s       REAL NOT NULL,
    end_epoch_s         REAL NOT NULL,
    min_horiz_m         REAL NOT NULL,
    min_vert_m          REAL NOT NULL,
    rx_power_dbm        REAL,
    severity            TEXT NOT NULL,
    description         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tunnels_time ON tunnels_4d(start_epoch_s, end_epoch_s);
