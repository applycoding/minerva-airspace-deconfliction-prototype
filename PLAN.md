# PLAN.md — MINERVA Airspace Deconfliction Prototype

**Project:** MINERVA Airspace Deconfliction Prototype  
**Challenge Reference:** Canadian DND / ISC Challenge EN578-24ISC4/94  
**Author & Copyright Owner:** Arpan Bom  
**Repository:** `applycoding/minerva-airspace-deconfliction-prototype`  
**Target Environment:** Stand-alone offline Windows desktop application (Python 3.12, PySide6-Essentials, SQLite, PyInstaller `--onedir`), verified on a GitHub Actions Windows runner (`windows-2022`)  
**Evidence Posture:** Engineering verification evidence offered towards the applicant's readiness-level assessment against the challenge criteria (simulation-only; never flight-tested on real aircraft)

---

## 1. Scope and Out-of-Scope

### 1.1 Essential Outcomes (Parts 1 to 6)

1. **Windows-Based Stand-Alone Application (Outcome 1 / Part 1):** Offline desktop GUI built with `PySide6-Essentials` and packaged into a standalone `--onedir` executable bundle (`minerva.exe`) via PyInstaller. Makes zero outbound network connections and requires no external database or tile server.
2. **Flight Plan Creation and Storage with Radio Needs (Outcome 2 / Part 1 & Part 2):** Form editor and JSON importer allowing operators to define uncrewed flight plans with 4D waypoints, priorities (`1`–`4`), airframe limits, aircraft radio transmitter parameters, and fixed Ground Control Station (GCS) receiver coordinates.
3. **4D Path and Radio Database (Outcome 3 / Part 2):** Local SQLite database stored in the user's application data directory (never inside the install directory), persisting approved flight plans, 4D waypoints, 4D tunnels, radio/GCS allocations, restricted zones, weather observations, and a compare-and-swap state revision counter.
4. **External Data Ingestion (Outcome 4 / Part 3):** Offline parsers for NAV CANADA Designated Airspace Handbook (TP 1820E) restricted zones at CFB Suffield (`CYR229`, `CYR230`, `CYR231` plus optional local NOTAM/ceiling overrides), ICAO-style crewed flight plans (accepting altitudes in feet or metres; rejecting Flight Levels), and Environment Canada METAR surface wind text files.
5. **Bounded 4D Path Maker (Outcome 5 / Part 4):** 3D spatial grid A* planner (`(ix, iy, iz, heading_octant)`) in local UTM Zone 12N metres with deterministic arrival timing along each path, respecting airspeed, wind triangle, climb/descent rate, tangent-fillet turn radius, active zones, and existing plans across user objectives (`shortest_time`, `avoid_zones`, `avoid_radio`).
6. **Airspace, Zone, and Radio Conflict Checker & Resolver (Outcome 6 / Part 5):** Exact continuous-time linear-leg conflict checker (with start/end time-buffer holds and optional `STRtree` broad-phase indexing) and ITU-R P.525-5 aircraft-to-GCS radio interference checker, paired with a priority-respecting automated mitigation ladder and operator escalation.
7. **4D Cleared Airspace Tunnel Generation (Outcome 7 / Part 6):** Generates per-segment and overall 4D reservation corridors (`width_m`, `low_m`, `high_m`, `start_epoch_s`, `end_epoch_s`) around trajectories and exports clearances to JSON and GeoJSON.

### 1.2 Extra Outcomes (Parts 7 and 8 + NATO Parts Document)

8. **Live Drone Telemetry and Conflict Prevention (Extra 1 / Part 7):** Receives live or simulated MAVLink v2 UDP telemetry (`HEARTBEAT` and `GLOBAL_POSITION_INT`) using a minimal built-in parser, detects tunnel boundary breaches, and computes conflict-free re-routes as a separate operator-confirmed step.
9. **Live Conformance Monitoring with Known-ID and Unknown-ID Track Matching (Extra 2 / Part 7):** Matches telemetry streams by `(source_addr, sysid, compid)` when mapped, or by sliding-window ($K=5$) 4D RMS residual against active plans with a strict ambiguity margin (`best <= 150 m` and `second_best >= 2 * best`).
10. **NATO-Country-Made Parts Reference Template (Extra 3 / Documentation):** `docs/nato_parts.md`, written last and flagged *"to be completed from vendor datasheets by the applicant"*, listing verified facts only and leaving unverified hardware fields as `TBD`.
11. **Automated Verification Rig and Self-Check (Part 8):** Seeded scenario generator, adaptive-step dense-sampling reference oracle, independent RF link evaluator, simulated MAVLink UDP transmitter (`src/minerva/test_rig/sim.py`), CLI self-check (`--self-check`), GUI smoke mode (`--gui-smoke`), and report generator (`reports/test_report.json` and `reports/test_report.md`).

### 1.3 Out of Scope and Strictly Limited GUI Surface

- **Strictly Bounded GUI Surface:** The GUI contains only six elements: (1) 2D offline vector map canvas (`QPainter`), (2) plan editor form, (3) conflict/results table, (4) tunnel JSON/GeoJSON export buttons, (5) restricted zone list (with override loader), and (6) live telemetry panel.
- **No Real-Flight or Hardware RF Control:** Simulation-only; never keys physical transmitters or commands real aircraft.
- **No Terrain Elevation Model, 3D Wind Shear, or Ray-Tracing RF:** Uses a flat-ground altitude reference, uniform wind vector per observation window, and free-space path loss screening.
- **No Imported GPL Libraries or Online Feeds:** No OpenSky, OpenAIP, ArduPilot, or `pymavlink` code is imported or bundled.

---

## 2. Architecture and Module List

### 2.1 Coordinate Frames, Units, Altitude Reference, and Time

- **Geographic Frame (`EPSG:4326` / WGS84):** `lat_deg` ($[-90, 90]$), `lon_deg` ($[-180, 180]$). GeoJSON always stores `[lon_deg, lat_deg]`.
- **Local Metric Working Frame (`EPSG:32612` — WGS84 / UTM Zone 12N):** Easting `x_m` ($\text{m}$), Northing `y_m` ($\text{m}$). UTM Zone 12N ($114^\circ\text{W}$ to $108^\circ\text{W}$, central meridian $111^\circ\text{W}$) covers CFB Suffield ($\approx 50.27^\circ\text{N}, 111.18^\circ\text{W}$). All projections use `pyproj.Transformer.from_crs(4326, 32612, always_xy=True)` (longitude first) and its inverse.
- **Vertical Coordinate (`alt_m`):** All internal altitudes are **metres above a flat ground reference** (`0.0 m` = Surface). This flat-terrain assumption is documented in `README.md`. Inputs in feet are converted via `1 ft = 0.3048 m`. Unlimited ceiling is `100000.0 m`. ICAO Flight Levels (`FL`) are unsupported and rejected on ingest with an explicit error message.
- **Time Representation:** UTC Unix epoch seconds (`epoch_s: float`) internally and in SQLite, formatted as ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) at JSON/GeoJSON/UI boundaries.
- **Speeds and Wind:** Speeds in $\text{m/s}$. Meteorological wind direction `wind_from_deg` is degrees true from which the wind blows; wind vector in East/North axes is $\mathbf{w} = (-W \sin\theta, -W \cos\theta)$.
- **Radio Units:** Frequency `freq_mhz`, bandwidth `bw_mhz`, guard `guard_mhz` in $\text{MHz}$; power `tx_power_dbm`, threshold `rx_threshold_dbm` in $\text{dBm}$; gains `tx_gain_dbi`, `rx_gain_dbi` in $\text{dBi}$; fixed GCS receiver height `2.0 m` above flat ground at `(gcs_lat_deg, gcs_lon_deg)`.

### 2.2 System Architecture

```text
+-----------------------------------------------------------------------------------+
|                        PySide6 Desktop GUI (minerva.gui)                          |
|  [Map Canvas (QPainter)] [Plan Editor] [Conflict Table] [Zone List] [Live Panel]  |
+-----------------+-------------------------+-------------------------+-------------+
                  |                         |                         |
                  v                         v                         v
+------------------------+   +------------------------------+   +-------------------+
|   Data Ingest (Part 3) |   | Core Deconfliction (4, 5, 6) |   | Live Watch (Pt 7) |
| - Suffield GeoJSON     |   | - planner.py (3D Grid A*)    |   | - live.py         |
|   + Zone Overrides     |   | - conflict.py (Exact 4D/RF)  |   |   (MAVLink v2 UDP |
| - Crewed Plans (ft/m)  |   | - resolver.py (Priority)     |   |    & Track Match) |
| - METAR Surface Wind   |   | - tunnel.py (4D Export)      |   |                   |
+-----------+------------+   +--------------+---------------+   +---------+---------+
            |                               |                             |
            +---------------+---------------+-----------------------------+
                            |
                            v
+-----------------------------------------------------------------------------------+
|               Persistence & Spatial Index Layer (minerva.db / Part 2)             |
|     SQLite 3 (User Data Dir, CAS Revision Counter) + Shapely 2.2 STRtree          |
+-----------------------------------------------------------------------------------+
```

### 2.3 Module List and Function-Level Interfaces

#### `src/minerva/models.py` — Domain Data Structures
- `PlannerStatus(str, Enum)`: `FOUND`, `NO_PATH_WITHIN_GRID`, `BUDGET_EXHAUSTED`, `REJECTED_WEATHER`, `REJECTED_START_GOAL`.
- `TrackMatchStatus(str, Enum)`: `MATCHED_KNOWN_ID`, `MATCHED_TRAJECTORY`, `AMBIGUOUS`, `UNMATCHED`.
- `Waypoint4D(lat_deg: float, lon_deg: float, alt_m: float, epoch_s: float, x_m: float = 0.0, y_m: float = 0.0)`
- `DroneLimits(max_airspeed_mps: float, max_climb_mps: float, max_descent_mps: float, min_turn_radius_m: float, max_wind_mps: float, hover_allowed: bool = False)`
- `RadioSpec(freq_mhz: float, bw_mhz: float, tx_power_dbm: float, tx_gain_dbi: float, rx_gain_dbi: float, rx_threshold_dbm: float, gcs_lat_deg: float, gcs_lon_deg: float, gcs_x_m: float = 0.0, gcs_y_m: float = 0.0, guard_mhz: float = 2.0, radio_model: str = "Custom")`
- `TunnelSegment4D(seg_index: int, start_x_m: float, start_y_m: float, end_x_m: float, end_y_m: float, horiz_half_width_m: float, vert_margin_m: float, low_m: float, high_m: float, start_epoch_s: float, end_epoch_s: float)`
- `Tunnel4D(plan_id: str, width_m: float, horiz_half_width_m: float, vert_margin_m: float, time_buf_s: float, low_m: float, high_m: float, start_epoch_s: float, end_epoch_s: float, segments: list[TunnelSegment4D])`
- `FlightPlan(plan_id: str, callsign: str, priority: int, status: str, created_epoch_s: float, limits: DroneLimits, radio: RadioSpec, waypoints: list[Waypoint4D], tunnel: Tunnel4D | None, is_crewed: bool = False)`
- `RestrictedZone(zone_id: str, name: str, polygon_wgs84: list[tuple[float, float]], polygon_utm: list[tuple[float, float]], floor_m: float, ceiling_m: float, seasonal_rule: str, handbook_issue: str, source_note: str, override_active: bool | None = None, override_ceiling_m: float | None = None)`
- `WeatherObservation(station_id: str, valid_start_epoch_s: float, valid_end_epoch_s: float, wind_from_deg: float, wind_speed_mps: float, gust_mps: float, is_synthetic: bool = False, raw_text: str = "")`
- `ConflictRecord(conflict_id: str, kind: str, plan_a_id: str, plan_b_or_zone_id: str, start_epoch_s: float, end_epoch_s: float, min_horiz_m: float, min_vert_m: float, rx_power_dbm: float | None, severity: str, description: str)`
- `PlannerResult(status: PlannerStatus, plan: FlightPlan | None, expansions: int, elapsed_s: float, message: str)`
- `ResolutionProposal(original_plan_id: str, action_type: str, summary: str, modified_plan: FlightPlan | None, requires_operator: bool, conflicts_remaining: int)`

#### `src/minerva/coords.py` — Coordinate and Unit Transformations
- `lonlat_to_utm12n(lon_deg: float, lat_deg: float) -> tuple[float, float]`: Calls singleton `Transformer.from_crs(4326, 32612, always_xy=True).transform(lon_deg, lat_deg)`.
- `utm12n_to_lonlat(x_m: float, y_m: float) -> tuple[float, float]`: Calls singleton `Transformer.from_crs(32612, 4326, always_xy=True).transform(x_m, y_m)`.
- `feet_to_metres(feet: float) -> float`: `feet * 0.3048`.
- `knots_to_mps(knots: float) -> float`: `knots * 0.514444`.
- `nm_to_metres(nm: float) -> float`: `nm * 1852.0`.
- `dms_to_deg(deg: int, minutes: int, seconds: float, hemi: str) -> float`: Exact DMS conversion for TP 1820E coordinates.
- `build_conservative_circle_utm(center_lon: float, center_lat: float, radius_m: float, n_vertices: int = 256) -> list[tuple[float, float]]`: Builds a 256-vertex polygon in UTM 12N with outer radius `radius_m / math.cos(math.pi / n_vertices)` so the polygon strictly contains the circle.

#### `src/minerva/db.py` — SQLite Database Manager (Part 2)
- `resolve_db_path(explicit_path: Path | None = None) -> Path`: Uses `explicit_path`, else `os.environ.get("MINERVA_DB_PATH")`, else `%LOCALAPPDATA%/Minerva/minerva.sqlite3` (Windows) or `~/.local/share/minerva/minerva.sqlite3` (Linux). Never writes inside the executable directory.
- `init_db(db_path: Path) -> sqlite3.Connection`: Creates tables, indices, `db_state_meta(id=1, revision=0)`, enables `PRAGMA foreign_keys = ON` and `PRAGMA journal_mode = WAL`.
- `validate_plan_invariants(plan: FlightPlan) -> None`: Raises `ValueError` unless `len(plan.waypoints) >= 2`, all coordinates/timestamps/limits are finite (`math.isfinite`), and waypoint `epoch_s` values are strictly increasing (`wp[i+1].epoch_s > wp[i].epoch_s`).
- `get_db_revision(conn: sqlite3.Connection) -> int`: Returns current `revision` counter.
- `approve_and_persist_plan(conn: sqlite3.Connection, plan: FlightPlan, expected_revision: int, supersede_plan_id: str | None = None) -> int`: Validates invariants, executes `BEGIN IMMEDIATE`, verifies `revision == expected_revision` (raising `StaleStateError` on mismatch), optionally marks `supersede_plan_id` as `SUPERSEDED` (only used when operator accepts a live re-route for that specific plan; never modifies other approved plans), inserts the `APPROVED` plan/waypoints/radio/tunnel, increments `revision`, and commits in one transaction.
- `list_active_plans(conn: sqlite3.Connection, start_epoch_s: float | None = None, end_epoch_s: float | None = None) -> list[FlightPlan]`: Returns `APPROVED` and `CREWED_ACTIVE` plans.
- `save_zones`, `list_zones`, `save_weather`, `get_active_weather`, `log_conflicts`.

#### `src/minerva/ingest.py` — External Data Parsers (Part 3)
- `load_zones_geojson(path: Path, overrides_path: Path | None = None) -> list[RestrictedZone]`: Loads `data/zones/suffield.geojson`, converts circles (`CYR231`) via `build_conservative_circle_utm(n_vertices=256)`, and applies optional operator ceiling/activity overrides from `overrides_path`.
- `is_zone_active(zone: RestrictedZone, epoch_s: float) -> tuple[bool, float, float]`: Evaluates zone activity and ceiling at `epoch_s` (honouring any operator override first, then TP 1820E seasonal rules).
- `load_crewed_plans(path: Path) -> list[FlightPlan]`: Parses ICAO-style JSON/text crewed plans into `FlightPlan(is_crewed=True, status="CREWED_ACTIVE")`. Accepts altitudes in feet (`ft`) or metres (`m`) above ground reference; **rejects Flight Levels (`FL`/`F`) with `ValueError("Flight levels (FL) are not supported; specify altitude in feet or metres above ground reference")`**.
- `parse_weather_text(path: Path) -> list[WeatherObservation]`: Parses offline METAR wind lines (`wind_from_deg`, `wind_speed_mps`, `gust_mps`, validity window).
- `resolve_weather_for_window(conn_or_list, start_epoch_s: float, end_epoch_s: float, synthetic_wind: WeatherObservation | None = None) -> WeatherObservation | None`: Returns the covering observation or `synthetic_wind` if configured; otherwise `None` (causing planner/checker to reject with `REJECTED_WEATHER`).

#### `src/minerva/tunnel.py` — 4D Tunnel Maker and Exporter (Part 6)
- `build_tunnel(plan_id: str, waypoints: list[Waypoint4D], horiz_half_width_m: float = 100.0, vert_margin_m: float = 30.0, time_buf_s: float = 15.0) -> Tunnel4D`
- `export_tunnel_json(tunnel: Tunnel4D, out_path: Path) -> None`
- `export_tunnel_geojson(plan: FlightPlan, out_path: Path) -> None`: Writes GeoJSON `FeatureCollection` with `[lon, lat]` coordinates and 4D tunnel properties.

#### `src/minerva/conflict.py` — Exact 4D Space, Zone, Weather, and Radio Conflict Checker (Part 5)
- `extend_waypoints_with_time_buffer(waypoints: list[Waypoint4D], t_buf_s: float) -> list[ tuple[Waypoint4D, Waypoint4D] ]`: Prepends a stationary hold leg `[t_0 - t_buf_s, t_0]` at `waypoints[0]` and appends a stationary hold leg `[t_end, t_end + t_buf_s]` at `waypoints[-1]`.
- `check_leg_pair_exact(leg_a: tuple[Waypoint4D, Waypoint4D], leg_b: tuple[Waypoint4D, Waypoint4D], h_sep_m: float, v_sep_m: float, tol: float = 1e-9) -> tuple[bool, float, float, float, float]`: Exact linear-relative-motion interval intersection check (Section 6.3).
- `SpatialIndex`: Immutable wrapper around `shapely.STRtree` built from 2D bounding boxes of active plan legs, mapping integer query indices back to `(plan_id, leg_index, leg_tuple)`. Rebuilt after each plan approval.
- `check_radio_conflict(plan_a: FlightPlan, plan_b: FlightPlan) -> list[ConflictRecord]`: ITU-R P.525-5 aircraft-TX to fixed-GCS-RX check in both directions (Section 6.3).
- `check_zone_conflicts(plan: FlightPlan, zones: list[RestrictedZone]) -> list[ConflictRecord]`: Checks tunnel-expanded legs (`horiz_half_width_m`, `vert_margin_m`) and `T_buf`-extended time intervals against active zone polygons and ceilings.
- `check_all_conflicts(candidate: FlightPlan, active_plans: list[FlightPlan], zones: list[RestrictedZone], weather: WeatherObservation | None, default_h_sep_m: float = 100.0, default_v_sep_m: float = 30.0, default_t_buf_s: float = 15.0, index: SpatialIndex | None = None) -> list[ConflictRecord]`: Runs weather wind-limit check (`max(sustained, gust) <= max_wind_mps`), zone check, RF check, and 4D leg check (exhaustive if `index is None`, or `STRtree` broad-phase if `index` is provided; both must return identical results).

#### `src/minerva/planner.py` — Bounded 3D Grid A* Path Maker (Part 4)
- `solve_wind_triangle(airspeed_mps: float, azimuth_rad: float, wind_from_deg: float, wind_speed_mps: float) -> float | None`: Computes along-track groundspeed (Section 6.2).
- `plan_4d_path(start_wp: Waypoint4D, goal_lat: float, goal_lon: float, goal_alt_m: float, limits: DroneLimits, radio: RadioSpec, objective: str, zones: list[RestrictedZone], existing_plans: list[FlightPlan], weather: WeatherObservation | None, grid_step_m: float = 250.0, alt_step_m: float = 30.0, max_expansions: int = 40000) -> PlannerResult`

#### `src/minerva/resolver.py` — Priority Resolver (Part 5)
- `resolve_conflicts(candidate: FlightPlan, active_plans: list[FlightPlan], zones: list[RestrictedZone], weather: WeatherObservation | None, alternate_freqs_mhz: list[float]) -> ResolutionProposal`: Applies priority and crewed-precedence rules without ever mutating already-approved or crewed plans (Section 6.4).

#### `src/minerva/live.py` — MAVLink v2 Codec, Conformance, and Track Matcher (Part 7)
- `crc16_mcrf4xx(data: bytes, crc_extra: int) -> int`: Pure-Python CRC-16/MCRF4XX.
- `encode_mavlink_v2_frame(msgid: int, payload: bytes, sysid: int = 1, compid: int = 1, seq: int = 0) -> bytes`: Zero-trims trailing payload zeros (keeping $\ge 1$ byte) and frames with `0xFD` and CRC.
- `parse_mavlink_v2_datagram(datagram: bytes) -> tuple[list[dict], int]`: Parses one or more MAVLink v2 frames in a UDP datagram, returning `(decoded_messages, dropped_frame_count)` (Section 6.5).
- `LiveTracker`: Keys telemetry streams by `(source_addr, sysid, compid)`, learns boot-to-plan clock offset on first packet via an injected/virtual clock, runs known-ID or sliding-window ($K=5$) unknown-ID matching, and flags off-tunnel drift after 2 consecutive out-of-tunnel reports.

#### `src/minerva/test_rig/` — Verification Rig, Oracle, and Simulated Drone (Part 8)
- `src/minerva/test_rig/oracle.py`: Adaptive-step (`max_rel_speed * dt <= 1.0 m`) dense-sampling space/time oracle and independent ITU-R P.525-5 RF link evaluator.
- `src/minerva/test_rig/scenarios.py`: Deterministic fixtures and seeded (`numpy.random.PCG64`) scenario builders for T1–T6.
- `src/minerva/test_rig/sim.py`: Simulated drone sending real MAVLink v2 UDP datagrams over `127.0.0.1` driven by a virtual clock.
- `src/minerva/test_rig/runner.py`: Executes T1–T7, writes `reports/test_report.json` and `reports/test_report.md`, and provides the fast non-recursive `--self-check` pipeline.

---

## 3. Pinned Versions and Third-Party Dependencies

All versions were verified against PyPI and GitHub Releases on **28 October 2026**. `scipy`, `pytest-qt`, and `hypothesis` are intentionally excluded. After the first green CI run, `pip freeze` output is committed as `requirements-lock.txt`.

| Package / Tool | Pinned Version | Licence | Purpose |
| :--- | :--- | :--- | :--- |
| **Python** | `3.12.x` (CI runner) | PSF-2.0 | Runtime and stdlib (`sqlite3`, `struct`, `json`, `math`, `socket`) |
| **PySide6-Essentials** | `6.12.0` (pulls `shiboken6==6.12.0`) | LGPL-3.0-only | Desktop GUI (`QtWidgets`, `QtCore`, `QtGui`, `QPainter`) |
| **shapely** | `2.2.0` (bundles GEOS) | BSD-3-Clause (GEOS: LGPL-2.1-or-later) | 2D polygon geometry and `STRtree` spatial index |
| **pyproj** | `3.8.0` (bundles PROJ) | MIT | CRS transforms (`EPSG:4326` $\leftrightarrow$ `EPSG:32612`) |
| **numpy** | `2.5.4` | BSD-3-Clause | Vector math and seeded `PCG64` random generation |
| **pytest** | `9.2.0` | MIT | Test runner (GUI tested via `QT_QPA_PLATFORM=offscreen` + plain `QApplication`) |
| **pyinstaller** | `6.22.3` | GPL-2.0-or-later WITH Bootloader-Exception | `--onedir` executable bundler |
| **GitHub Actions** | `actions/checkout@v7` (`v7.0.1`), `actions/setup-python@v7` (`v7.1.0`), `actions/upload-artifact@v7` (`v7.0.2`) | MIT | CI workflow actions on `windows-2022` and `ubuntu-24.04` |

### Licence and Attribution Policy (`LICENSE` and `NOTICE.md`)

- `LICENSE` contains the evaluation-only licence text under `Copyright (c) 2026 Arpan Bom`.
- No GPL library is imported by the application; the `PyInstaller` packaging tool is used under its GPL bootloader exception.
- No AI or coding-tool attribution appears in source files, commits, or workflows; third-party software and data notices are maintained in `NOTICE.md`.
- `NOTICE.md` lists every bundled/installed package and licence above and explicitly states:
  1. The evaluation-only licence does not restrict third-party components, which remain under their own licences.
  2. Dynamic LGPL libraries (`Qt6`/`PySide6`/`shiboken6` under LGPL-3.0 and `GEOS` inside `shapely` wheels under LGPL-2.1) are distributed as separate shared library files in the `--onedir` bundle so the user can inspect or replace them.
  3. Upstream source code locations (`https://code.qt.io/`, `https://libgeos.org/`, `https://proj.org/`, `https://numpy.org/`, `https://www.python.org/`, `https://pyinstaller.org/`).
  4. Full licence texts are shipped in `THIRD_PARTY_LICENSES/` inside the repository and copied into the `--onedir` bundle.
  5. Airspace data attribution: the NAV CANADA *Designated Airspace Handbook* (TP 1820E) is `© His Majesty the King in Right of Canada`, *"Source of Canadian Airspace Data © 2026 Transport Canada"*, and only the coordinates and altitude rules for `CYR229`, `CYR230`, and `CYR231` required for the demonstration are transcribed.

---

## 4. Repository Layout

```text
minerva-airspace-deconfliction-prototype/
├── .github/workflows/ci.yml             # Neutral workflow "ci" (windows-2022 + ubuntu-24.04)
├── THIRD_PARTY_LICENSES/                # Full license texts bundled into dist/minerva/
├── data/
│   ├── zones/
│   │   ├── suffield.geojson             # Exact TP 1820E (3 Sep-29 Oct 2026) CYR229/230/231
│   │   └── zone_overrides.json          # Optional operator ceiling/activity overrides
│   ├── crewed/sample_crewed_plans.json  # Crewed plans with altitudes in feet (no FL)
│   ├── weather/
│   │   ├── cyxh_metar_calm.txt          # Nominal surface wind METAR
│   │   └── cyxh_metar_highwind.txt      # High wind / gust METAR
│   └── presets/drones_and_radios.json   # Airframe limits + radio & GCS presets
├── docs/
│   ├── nato_parts.md                    # Written last; vendor datasheet fields marked TBD
│   └── user_guide.md                    # Offline installation and operator guide
├── reports/.gitkeep                     # Output folder for test_report.json and .md
├── src/minerva/
│   ├── __init__.py
│   ├── __main__.py                      # CLI: GUI launch, --self-check, --gui-smoke, --run-test-rig
│   ├── models.py
│   ├── coords.py
│   ├── db.py
│   ├── ingest.py
│   ├── planner.py
│   ├── conflict.py
│   ├── resolver.py
│   ├── tunnel.py
│   ├── live.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py               # MainWindow hosting the 6 bounded GUI panels
│   │   ├── map_canvas.py                # QPainter offline UTM 12N vector map
│   │   ├── plan_editor.py               # Plan, limits, radio/GCS editor + planner trigger
│   │   └── conflict_panel.py            # Conflicts table, zone list, tunnel exports, live panel
│   └── test_rig/
│       ├── __init__.py
│       ├── oracle.py                    # Adaptive-dt dense sampling & independent RF oracle
│       ├── scenarios.py                 # Deterministic + PCG64 seeded scenarios
│       ├── sim.py                       # Simulated MAVLink v2 UDP drone with virtual clock
│       └── runner.py                    # Full rig runner and fast <60s --self-check
├── tests/
│   ├── conftest.py                      # Offscreen QApplication, temp DB, no-network monkeypatch
│   ├── test_unit_coords_models.py
│   ├── test_unit_db.py
│   ├── test_unit_mavlink.py
│   ├── test_t1_space_time.py
│   ├── test_t2_radio.py
│   ├── test_t3_zones.py
│   ├── test_t4_planner.py
│   ├── test_t5_scale.py
│   ├── test_t6_resolution.py
│   ├── test_t7_live_mavlink.py
│   └── test_t8_packaging_and_smoke.py
├── LICENSE
├── NOTICE.md
├── PLAN.md
├── README.md
├── minerva.spec
├── pyproject.toml
└── requirements-lock.txt
```

---

## 5. Data Model and SQLite Schema

The database file resides in the user data directory (`MINERVA_DB_PATH` override supported). Every connection sets `PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;`. All altitudes are metres above flat ground reference (`0.0` = Surface).

```sql
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
```

---

## 6. Algorithm Choices and Policies

### 6.1 Suffield Restricted Airspace (`data/zones/suffield.geojson`)

Transcribed from the NAV CANADA *Designated Airspace Handbook* **TP 1820E (effective 3 Sep to 29 Oct 2026; the next issue takes effect 29 Oct 2026 and must be re-checked)**. Every feature stores `"handbook_issue": "TP 1820E (2026-09-03 to 2026-10-29)"`. GeoJSON coordinates are `[lon_deg, lat_deg]`:

1. **CYR229:** Polygon vertices `(lat, lon)` in order:
   - `N50 20 15, W111 10 00` (`50.33750000, -111.16666667`)
   - `N50 35 00, W111 10 00` (`50.58333333, -111.16666667`)
   - `N50 43 00, W111 05 00` (`50.71666667, -111.08333333`)
   - `N50 43 00, W110 17 00` (`50.71666667, -110.28333333`)
   - `N50 37 00, W110 17 00` (`50.61666667, -110.28333333`)
   - `N50 25 00, W110 25 00` (`50.41666667, -110.41666667`)
   - `N50 23 00, W110 28 00` (`50.38333333, -110.46666667`)
   - `N50 23 00, W110 35 20` (`50.38333333, -110.58888889`)
   - `N50 20 15, W110 35 47.57` (`50.33750000, -110.59654722`)
   - Closing back to `N50 20 15, W111 10 00`.
   - **Altitude & Seasonal Rule:** Surface (`0.0 m`) to Unlimited (`100000.0 m`) from `0000Z 1 Apr` to `0700Z 1 Dec`; Surface (`0.0 m`) to `15,000 ft` (`4572.0 m`, or as specified by NOTAM) from `0701Z 1 Dec` to `2359Z 31 Mar`. (For timestamps in `(07:00:00Z, 07:01:00Z)` on 1 Dec, the transition occurs at `07:00:00Z` / `07:01:00Z` so `epoch < Dec 1 07:01:00Z` uses `100000.0 m` and `epoch >= Dec 1 07:01:00Z` uses `4572.0 m`).
2. **CYR230:** Polygon vertices `(lat, lon)` in order:
   - `N50 15 00, W111 10 00` (`50.25000000, -111.16666667`)
   - `N50 20 15, W111 10 00` (`50.33750000, -111.16666667`)
   - `N50 20 15, W110 35 47.57` (`50.33750000, -110.59654722`)
   - `N50 13 00, W110 37 00` (`50.21666667, -110.61666667`)
   - `N50 13 00, W111 07 20` (`50.21666667, -111.12222222`)
   - Closing back to `N50 15 00, W111 10 00`.
   - **Altitude & Time:** Surface (`0.0 m`) to Unlimited (`100000.0 m`), continuous (or as specified by NOTAM).
3. **CYR231:** Circle centred on `N50 16 00, W111 11 00` (`50.26666667, -111.18333333`), radius stated in TP 1820E as `"3 miles"` — modelled as `3 NM = 5556.0 m` (both the exact Handbook wording `"3 miles"` and the `3 NM = 5556 m` assumption are recorded in `suffield.geojson`). Approximated in UTM 12N by a **256-vertex polygon with outer radius $5556.0 / \cos(\pi / 256)\text{ m}$** so it strictly encloses the true circle. Surface (`0.0 m`) to `6,000 ft` (`1828.8 m`), continuous.
4. **NOTAM Override Policy:** Dynamic NOTAMs are not parsed automatically; operators can override any zone's `active` boolean or `ceiling_m` in `data/zones/zone_overrides.json`.

### 6.2 Bounded 4D Path Maker (`src/minerva/planner.py`)

The path maker finds the **lowest-cost path within the configured 3D grid and step discretisation** (never claimed to be globally optimal):

1. **Grid & State:**
   - Local UTM 12N grid with horizontal step $\Delta xy \ge \max(\text{grid\_step\_m}, \text{min\_turn\_radius\_m})$ and vertical layer step $\Delta z = 30.0\text{ m}$.
   - State is `(ix, iy, iz, heading_octant)` where `heading_octant` $\in \{0..7\}$ represents $0^\circ, 45^\circ, \dots, 315^\circ$ clockwise from North (or `None` at the start node).
   - Because along-track airspeed is fixed at $v_a = 0.85 \times v_{\text{max\_airspeed}}$, the arrival timestamp `epoch_s` at any state is deterministic from the path (`g_time`), eliminating any time dimension from the state for fixed-wing aircraft.
   - If `limits.hover_allowed` is `True` (multirotor option), a wait transition holds position for a fixed `10.0 s` (`wait_count` $0..6$ included in state). Fixed-wing plans (`hover_allowed=False`) cannot hold in place; temporal deconfliction is handled via departure-time shifts in the resolver.
2. **Transitions & Turn Fillet Rule:**
   - 8 horizontal directions $\times$ $\Delta z \in \{-\Delta z, 0, +\Delta z\}$.
   - Heading change per step is restricted to $|\Delta \psi| \le 45^\circ$ ($\Delta \text{octant} \in \{-1, 0, +1\} \pmod 8$; no $\ge 90^\circ$ turns or reversals).
   - **Tangent-Fillet Rule:** Every horizontal step length $L$ satisfies $L \ge 1.0 \times \text{min\_turn\_radius\_m}$, which guarantees two adjacent $45^\circ$ turn fillets ($2 \times R \tan 22.5^\circ \approx 0.828 R$) fit within the step without overlapping. **No post-processing or waypoint merging is performed**, so the output plan consists of the exact edges verified during search.
3. **Weather & Wind Triangle Check:**
   - Missing/stale weather with no synthetic wind configured $\rightarrow$ immediate `PlannerResult(REJECTED_WEATHER)`.
   - Effective wind $\max(\text{wind\_speed\_mps}, \text{gust\_mps}) > \text{limits.max\_wind\_mps}$ $\rightarrow$ `PlannerResult(REJECTED_WEATHER)`.
   - Wind vector $\mathbf{w} = (-W \sin\theta, -W \cos\theta)$ with $\theta = \text{wind\_from\_deg}$; track unit vector $\hat{\mathbf{u}} = (\sin\psi, \cos\psi)$. Along-track wind $w_\parallel = \mathbf{w}\cdot\hat{\mathbf{u}}$, crosswind squared $w_\perp^2 = \|\mathbf{w}\|^2 - w_\parallel^2$, radicand $D = v_a^2 - w_\perp^2$.
   - Reject edge if $D < 0$ or groundspeed $v_g = w_\parallel + \sqrt{D} \le 0$ (tailwinds stronger than airspeed are valid since $D \ge 0$ and $v_g > 0$).
   - Edge duration is $\Delta t = \max(L / v_g,\; |\Delta z| / v_{z,\max})$. When stretched by climb/descent limits, verify required airspeed magnitude $\| (L/\Delta t)\hat{\mathbf{u}} - \mathbf{w} \| \le v_{\text{max\_airspeed}} + 10^{-9}$.
4. **Edge Conflict Pruning, Cost, and Heuristic:**
   - Every candidate edge `[t_parent, t_parent + dt]` is checked against active `RestrictedZone` polygons/ceilings (expanded by tunnel margins) and existing plans using the exact checker (Section 6.3). Conflicting edges are pruned.
   - Edge cost $c(e) = \Delta t \cdot (1 + w_{\text{zone}} \phi_{\text{zone}}(e) + w_{\text{rf}} \phi_{\text{rf}}(e))$ with presets `shortest_time` $(0, 0)$, `avoid_zones` $(5.0, 0.5)$, and `avoid_radio` $(0.5, 8.0)$.
   - Admissible heuristic: $h(n) = d_{xy}(n, \text{goal}) / (v_{\text{max\_airspeed}} + W)$.
   - Returns `FOUND`, `NO_PATH_WITHIN_GRID` (open set empty), `BUDGET_EXHAUSTED` (`expansions > 40000`), `REJECTED_WEATHER`, or `REJECTED_START_GOAL`.

### 6.3 Exact Space/Time, Zone, and Radio Conflict Checker (`src/minerva/conflict.py`)

1. **Time Buffer via Start/End Holds:**
   - For time buffer $T_{\text{buf}} = \max(\text{default } 15\text{ s}, \text{time\_buf}_A, \text{time\_buf}_B)$, each plan's waypoint sequence is extended by prepending a stationary hold leg $[t_{\text{first}} - T_{\text{buf}}, t_{\text{first}}]$ at its first waypoint and appending a stationary hold leg $[t_{\text{last}}, t_{\text{last}} + T_{\text{buf}}]$ at its last waypoint. No $\tau$-shift is used.
2. **Exact Continuous-Time Linear Leg Pair Check:**
   - Separation thresholds: $H_{\text{sep}} = \max(100\text{ m}, \text{half\_width}_A + \text{half\_width}_B)$, $V_{\text{sep}} = \max(30\text{ m}, \text{vert\_margin}_A + \text{vert\_margin}_B)$, tolerance $\epsilon = 10^{-9}$.
   - Given extended legs $A$ on $[t_{A0}, t_{A1}]$ and $B$ on $[t_{B0}, t_{B1}]$, take common time interval $I_t = [t_0, t_1] = [t_{A0}, t_{A1}] \cap [t_{B0}, t_{B1}]$. If $t_0 > t_1$, no conflict.
   - On $I_t$, relative position $\Delta\mathbf{p}(t) = \mathbf{p}_A(t) - \mathbf{p}_B(t) = \mathbf{p}_0 + \mathbf{v}(t - t_0)$ is linear in $t$:
     - **(a) Vertical interval $I_v$:** Solve $|\Delta z_0 + v_z \tau| < V_{\text{sep}} - \epsilon$ for $\tau = t - t_0 \in [0, t_1 - t_0]$. (If $|v_z| \le 10^{-12}$, $I_v = I_t$ when $|\Delta z_0| < V_{\text{sep}} - \epsilon$, else $\emptyset$). This yields a closed sub-interval $[t_{v0}, t_{v1}]$.
     - **(b) Horizontal interval $I_h$:** Solve $(\Delta x_0 + v_x \tau)^2 + (\Delta y_0 + v_y \tau)^2 < (H_{\text{sep}} - \epsilon)^2$, a quadratic $a\tau^2 + b\tau + c < 0$ on $[0, t_1 - t_0]$. (If $a = v_x^2 + v_y^2 \le 10^{-18}$, $I_h = I_t$ when $c < 0$, else $\emptyset$; otherwise if discriminant $b^2 - 4ac > 0$, take root interval $[\tau_-, \tau_+]$ intersected with $[0, t_1 - t_0]$).
     - **(c) Intersection:** Conflict iff $I_{\text{conf}} = I_t \cap I_v \cap I_h$ is non-empty (and has positive overlap or valid instant when $t_0 = t_1$). Report entry time $\min(I_{\text{conf}})$, exit time $\max(I_{\text{conf}})$, and exact minimum horizontal and vertical separations on $I_{\text{conf}}$.
3. **`STRtree` Broad-Phase Index:**
   - Built with `shapely.STRtree` over 2D leg bounding boxes buffered by $H_{\text{sep}}$. `STRtree.query(box)` returns integer indices mapped to leg metadata. Time and altitude are filtered after the 2D query. The index is immutable and rebuilt after each plan approval. Exhaustive pair checking and `STRtree`-indexed checking are verified to produce identical results.
4. **Radio Interference Rule (ITU-R P.525-5 Screening Model):**
   - Each plan has a moving aircraft transmitter (`waypoints`) and a fixed GCS receiver at $\mathbf{g} = (\text{gcs\_x\_m}, \text{gcs\_y\_m}, 2.0\text{ m})$.
   - Interference is tested in both directions: $(A\text{ aircraft TX} \to B\text{ GCS RX})$ at frequency $f_A$, and $(B\text{ aircraft TX} \to A\text{ GCS RX})$ at frequency $f_B$.
   - Guard band $g = \max(g_A, g_B)$ is added as an extra gap between band edges: band overlap holds iff $|f_A - f_B| < (B_A / 2 + B_B / 2 + g)$.
   - Over the time overlap $[t_{\text{start},A}, t_{\text{end},A}] \cap [t_{\text{start},B}, t_{\text{end},B}]$, compute the exact minimum 3D distance $d_{\min}$ between the interferer's linear aircraft legs and the victim's fixed GCS point $\mathbf{g}$, **clamped to $d_{\min} \ge 10.0\text{ m}$** (near-field limit).
   - With $d_{\text{km}} = d_{\min} / 1000.0$ and interferer centre frequency $f_{\text{tx,MHz}}$:
     $$\text{FSPL}_{\text{dB}} = 32.44 + 20\log_{10}(d_{\text{km}}) + 20\log_{10}(f_{\text{tx,MHz}})$$
     $$P_{\text{rx}} = P_{\text{tx}} + G_{\text{tx}} + G_{\text{rx,victim}} - \text{FSPL}_{\text{dB}}$$
   - Conflict iff time overlap AND band overlap AND $P_{\text{rx}} > \text{rx\_threshold\_dbm}_{\text{victim}} + 10^{-9}$ (strict `>`). Documented as a screening model, not a coverage prediction.

### 6.4 Conflict Resolution and Precedence Policy (`src/minerva/resolver.py`)

- **Precedence Rules:**
  1. **Crewed aircraft (`is_crewed=True`) have absolute precedence over all drone priorities, including Priority 1.** The resolver never modifies a crewed plan.
  2. **Approving or resolving a candidate plan never modifies already-approved plans.** The resolver only searches modifications to the candidate plan (or returns `requires_operator=True` if an operator must decide whether to supersede an existing plan).
- **Mitigation Ladder on Candidate Plan:**
  1. **Departure Time Shift:** Shift all candidate waypoints by $\Delta t \in \{+60, +120, +180, +300, +600\}\text{ s}$.
  2. **Altitude Layer Shift:** Shift candidate cruise altitudes by $\Delta z \in \{+60, -60, +120, -120\}\text{ m}$ (staying $\ge 0\text{ m}$ and within climb/descent limits).
  3. **3D Grid A* Re-Route:** Call `plan_4d_path()` around active zones and approved plans.
  4. **RF Channel Shift:** If only `RADIO` conflicts remain, test `alternate_freqs_mhz`.
  5. **Operator Escalation:** If steps 1–4 fail, return `ResolutionProposal(requires_operator=True)`.

### 6.5 MAVLink v2 Codec and Live Watch (`src/minerva/live.py`)

1. **Minimal MAVLink v2 Codec (~150 lines, stdlib only):**
   - Frame layout: `0xFD` (1B), `len` (1B), `incompat_flags` (1B), `compat_flags` (1B), `seq` (1B), `sysid` (1B), `compid` (1B), `msgid` (3B little-endian), `payload` (`len` bytes), `crc` (2B little-endian), plus `13B` signature if `incompat_flags == 0x01`.
   - CRC-16/MCRF4XX (`init=0xFFFF`, reflected poly `0x8408`, no final XOR) over bytes `1 .. 9+len` followed by `CRC_EXTRA` (`HEARTBEAT` `msgid=0, extra=50, full_len=9`; `GLOBAL_POSITION_INT` `msgid=33, extra=104, full_len=28`).
   - Sender trims trailing zero bytes from payload (retaining $\ge 1$ byte). Receiver checks CRC on the transmitted payload, then zero-pads to `full_len` before unpacking.
   - Multiple frames per UDP datagram are parsed sequentially. Truncated frames, bad CRC, or unknown `incompat_flags` (`incompat_flags & ~0x01 != 0`) are dropped and counted. Signed frames (`incompat_flags == 0x01`) consume the extra 13 signature bytes and ignore the signature under the documented `"not authenticated"` trust policy.
   - `GLOBAL_POSITION_INT` (`<IiiiihhhH`): `time_boot_ms`, `lat` ($\text{deg}\times 10^7$), `lon` ($\text{deg}\times 10^7$), `alt` (mm MSL), `relative_alt` (mm above ground), `vx, vy, vz` (cm/s), `hdg` (cdeg). **Uses `relative_alt / 1000.0` as `alt_m`** (matching the flat-ground reference).
   - Stream key: `(source_addr, sysid, compid)`. `sysid` is an unauthenticated identifier. On the first packet of a stream, `epoch_offset_s = clock_now_s - time_boot_ms / 1000.0` is recorded using the injected/virtual clock.
2. **Conformance & Unknown-ID Matching:**
   - **Unknown-ID Matching:** Over a sliding window of the last $K = 5$ reports, compute 4D spatial RMS distance $E_{\text{RMS}}(P)$ between reports and each active plan $P$ interpolated at the report timestamps $t_k$. Match to $P_{\text{best}}$ **only if** $E_{\text{RMS}}(P_{\text{best}}) \le 150.0\text{ m}$ **and** (no second active plan exists or $E_{\text{RMS}}(P_{\text{second}}) \ge 2.0 \times E_{\text{RMS}}(P_{\text{best}})$); otherwise return `'AMBIGUOUS'` (or `'UNMATCHED'`) and abstain.
   - **Conformance & Drift Alert:** Compares each report against the matched plan's time-local interpolated leg position: cross-track error vs `horiz_half_width_m`, altitude vs `[low_m, high_m]`, and time vs `[start_epoch_s - T_buf, end_epoch_s + T_buf]`. Flags `LIVE_DRIFT` after **2 consecutive out-of-tunnel reports** (measured on the virtual clock: within 2 report intervals of boundary crossing). Re-route computation ($\le 5.0\text{ s}$ on runner) and atomic SQLite acceptance (`approve_and_persist_plan` with `supersede_plan_id`) execute as separate steps.

---

## 7. The 8 Verification Tests and Reference Oracle Design

### 7.1 Independent Reference Oracles (`src/minerva/test_rig/oracle.py`)

1. **Space/Time Adaptive-Step Dense-Sampling Oracle:**
   - Operates on the same `T_buf`-extended legs. For each pair of legs with overlapping time interval $[t_0, t_1]$ and relative velocity $\mathbf{v}_{\text{rel}}$, computes step size $\Delta t = \min(0.1\text{ s},\; 1.0\text{ m} / \max(\|\mathbf{v}_{\text{rel}}\|_3, 1.0\text{ m/s}))$ so that **`max_rel_speed * dt <= 1.0 m` always holds** (never a fixed `0.5 s` step). Evaluates endpoints $t_0, t_1$ plus uniform samples across $[t_0, t_1]$.
   - T1 scenarios are generated so planted clashes penetrate **$\ge 10\%$ inside** both separation minima ($\le 0.90 H_{\text{sep}}$ and $\le 0.90 V_{\text{sep}}$) and clean scenarios remain **$\ge 10\%$ outside** ($\ge 1.10$). Any random draw landing inside the $\pm 10\%$ band is excluded from pass/fail gating and tallied in `excluded_band_count`. Disagreements inside the $\pm 10\%$ band are reported separately and never counted as false alarms against the exact analytical detector.
2. **Independent RF Link-Budget Evaluator:**
   - Written separately in `oracle.py` from basic math primitives to cross-check aircraft-TX to GCS-RX ITU-R P.525-5 interference.

### 7.2 Verification Matrix and Gates (T1–T8)

| Test ID | Specification & Fixtures | Strict Correctness & Honest Timing Gates |
| :--- | :--- | :--- |
| **T1: Space/Time Clash** | 200 seeded scenarios (100 planted $\ge 10\%$ penetration, 100 clean $\ge 10\%$ outside; $\pm 10\%$ band excluded & counted) + 6 hand-derived fixtures (grazing, endpoint, stationary hold, equal-velocity, sub-sample high-speed, parallel). | **100% recall on planted clashes; 0% false alarms on clean scenarios outside the $\pm 10\%$ band; 100% pass on hand-derived fixtures.** |
| **T2: Radio Clash** | 50 seeded scenarios + boundary fixtures (10 m near-field clamp, guard band $g=\max(g_A,g_B)$, bidirectional aircraft-TX to fixed-GCS-RX). | **100% (50/50 + fixtures) exact agreement** with independent RF evaluator. |
| **T3: Suffield Zones** | Deterministic fixtures isolating one zone at a time (`CYR229`, `CYR230`, `CYR231`), testing lateral tunnel margins, ceilings, 256-gon circle containment, and instants just before/after `0000Z 1 Apr` and `0700Z`/`0701Z 1 Dec`. | **100% of intruding paths flagged; 0% false alarms.** |
| **T4: 4D Path Maker** | 100 requests built from known-feasible fixtures across `shortest_time`, `avoid_zones`, `avoid_radio`. Hard timeout `10.0 s` per request. | **$\ge 95/100$ return `FOUND`** (remainder return a valid `PlannerStatus` enum); **100% of `FOUND` paths pass independent validator** (airspeed, wind triangle, climb/descent, turn-fillet $L \ge R$, zones, plans). **Median time $\le 2.0\text{ s}$** (p50 & p95 reported). |
| **T5: Scale Benchmark** | Measure `check_all_conflicts` latency at **10, 50, 200, and 500** active plans; compare exhaustive vs `STRtree` outputs; record runner CPU/RAM. | **100% identical conflict sets** between exhaustive and `STRtree`; **median $\le 1.0\text{ s}$ at 200 plans and $\le 3.0\text{ s}$ at 500 plans** on CI runner (p50 & p95 reported). |
| **T6: Conflict Resolver** | 60 deterministic cases explicitly labelled `'resolvable'` or `'unresolvable'`, including crewed precedence over Priority 1 and non-mutation of approved plans. | **100% (60/60) match their label** (`'resolvable'` $\rightarrow$ verified zero-conflict plan within limits; `'unresolvable'` $\rightarrow$ `requires_operator=True`). |
| **T7: Live MAVLink UDP** | Simulated drone (`test_rig/sim.py`) streaming MAVLink v2 UDP frames over `127.0.0.1` with virtual clock: known-ID, unknown-ID ($K=5$, $2\times$ margin, `'AMBIGUOUS'` abstention), and tunnel exit. | **100% track match accuracy; drift flagged within $\le 2$ report intervals on virtual clock; separate re-route computed in $\le 5.0\text{ s}$ and accepted into SQLite.** |
| **T8: Exe & GUI Smoke** | Run frozen `dist/minerva/minerva.exe` from a clean temp folder outside checkout: `--self-check` and `--gui-smoke` (real `windows` platform plugin, 2 s `QTimer` exit, marker file). | **Exit code `0` for both; `--self-check` finishes in $< 60\text{ s}$; `--gui-smoke` writes verified marker file; zero outbound network calls.** |

---

## 8. Continuous Integration (CI) Design

`.github/workflows/ci.yml` uses workflow name `ci`, `actions/checkout@v7`, `actions/setup-python@v7`, and `actions/upload-artifact@v7`.

### 8.1 Main Job: `windows-build-and-test` (`runs-on: windows-2022`)

1. **Checkout & Python 3.12 Setup:** Install pinned dependencies (`PySide6-Essentials==6.12.0`, `shapely==2.2.0`, `pyproj==3.8.0`, `numpy==2.5.4`, `pytest==9.2.0`, `pyinstaller==6.22.3`) and `pip install -e . --no-deps`.
2. **Step 1 — Source Tests (`pytest`):**
   - Run `pytest -v` with `QT_QPA_PLATFORM=offscreen` and the `conftest.py` fixture that blocks non-localhost socket connections.
3. **Step 2 — PyInstaller `--onedir` Build:**
   - Run `pyinstaller --noconfirm --clean minerva.spec` producing `dist/minerva/minerva.exe` alongside separate LGPL DLLs, bundled `data/`, and `THIRD_PARTY_LICENSES/`.
4. **Step 3 — Frozen Executable Checks from Clean Temp Directory:**
   - Copy `dist/minerva` (or invoke it) with working directory set to `$env:RUNNER_TEMP\minerva_smoke`, `MINERVA_DATA_DIR=$env:RUNNER_TEMP\minerva_appdata`, and repo removed from `PATH`/`PYTHONPATH`:
     - Run `minerva.exe --self-check` (non-recursive fixed pipeline, gated at $< 60\text{ s}$, exit code `0`).
     - Run `minerva.exe --gui-smoke --marker-file $env:RUNNER_TEMP\gui_smoke_ok.txt` without `QT_QPA_PLATFORM=offscreen` (uses real Qt `windows` platform plugin, shows `MainWindow`, quits after `2 s` via `QTimer`, verifies exit code `0` and marker file existence).
5. **Step 4 — Full Verification Test Rig & Artifact Upload:**
   - Run `python -m minerva --run-test-rig --report-dir reports` from source.
   - Upload `reports/` (`test_report.json`, `test_report.md`) and zipped `dist/minerva/` via `actions/upload-artifact@v7`.

### 8.2 Secondary Job: `linux-test` (`runs-on: ubuntu-24.04`)

- Runs `QT_QPA_PLATFORM=offscreen pytest -v` and `python -m minerva --self-check` on Linux for cross-platform verification.

---

## 9. Build Order in 11 Verified Slices

A minimal PyInstaller `--onedir` executable and Windows CI workflow are established in **Slice 1** and kept green across every slice. **End of Slice 9** is the milestone checkpoint where **Parts 1 to 6 work together end-to-end**.

| Slice | Scope & Deliverables | Acceptance Command |
| :--- | :--- | :--- |
| **Slice 1** | **Skeleton, Licensing, PyInstaller Exe & Green CI:** `pyproject.toml`, `LICENSE`, `NOTICE.md`, `THIRD_PARTY_LICENSES/`, `models.py`, `coords.py` (`always_xy=True`, 256-gon circle), minimal `MainWindow`, `__main__.py` (`--self-check`, `--gui-smoke`), `minerva.spec`, `.github/workflows/ci.yml`. | `pytest tests/test_unit_coords_models.py && pyinstaller --noconfirm --clean minerva.spec && ./dist/minerva/minerva --self-check` |
| **Slice 2** | **Part 2 — SQLite Layer with CAS Revision Counter:** `src/minerva/db.py` (user data dir resolution, schema DDL, invariant checks $\ge 2$ waypoints / strictly increasing time / finite floats, atomic `approve_and_persist_plan` with compare-and-swap revision). | `pytest tests/test_unit_db.py` |
| **Slice 3** | **Part 3 — Suffield Zones, Crewed Plans & METAR Ingest:** `data/zones/suffield.geojson` (exact TP 1820E `3 Sep–29 Oct 2026` vertices, `CYR229` `0000Z 1 Apr`/`0700Z 1 Dec` rules, `CYR231` 256-gon), `zone_overrides.json`, `ingest.py` (rejecting `FL` in crewed plans, METAR wind/gust parser, missing-weather policy). | `pytest tests/test_t3_zones.py -k "ingest"` |
| **Slice 4** | **Part 6 — 4D Tunnel Maker & JSON/GeoJSON Exporters:** `src/minerva/tunnel.py` (`build_tunnel`, `export_tunnel_json`, `export_tunnel_geojson`). | `pytest tests/test_unit_coords_models.py -k "tunnel"` |
| **Slice 5** | **Part 5a — Exact Space/Time, Zone & Weather Conflict Checker (Exhaustive) + T1/T3 Oracles:** `src/minerva/conflict.py` (`T_buf` start/end holds, linear relative motion interval intersection, zone check with tunnel margins, wind/gust check) + `test_rig/oracle.py` (adaptive `dt` dense sampler). | `pytest tests/test_t1_space_time.py tests/test_t3_zones.py` |
| **Slice 6** | **Part 5b — ITU-R P.525-5 Radio Checker & `STRtree` Index (T2 & T5):** Aircraft-TX to fixed-GCS-RX check (`10 m` clamp, guard gap) + immutable `STRtree` broad phase verified identical to exhaustive check. | `pytest tests/test_t2_radio.py tests/test_t5_scale.py` |
| **Slice 7** | **Part 4 — Bounded 3D Grid A* Path Maker (T4):** `src/minerva/planner.py` (`(ix, iy, iz, heading_octant)`, wind triangle + climb airspeed check, $\pm 45^\circ$ turn limit, $L \ge R$ fillet rule, optional multirotor hover edge, `PlannerStatus` enum) + independent path validator. | `pytest tests/test_t4_planner.py` |
| **Slice 8** | **Part 5c — Priority & Crewed-Precedence Conflict Resolver (T6):** `src/minerva/resolver.py` (crewed precedence over all priorities including Priority 1, non-mutation of approved plans, mitigation ladder, labelled resolvable/unresolvable fixtures). | `pytest tests/test_t6_resolution.py` |
| **Slice 9** | **Part 1 — Bounded Desktop GUI Integration (**CHECKPOINT: Parts 1 to 6 Working Together**):** `map_canvas.py` (`QPainter`), `plan_editor.py`, `conflict_panel.py` (conflicts table, tunnel exports, zone list). | `QT_QPA_PLATFORM=offscreen pytest tests/test_t8_packaging_and_smoke.py -k "parts_1_to_6"` |
| **Slice 10** | **Part 7 — Live Watch MAVLink v2 UDP, Conformance & Track Matching (T7):** `src/minerva/live.py` (~150-line MAVLink v2 codec, zero-trimming, signed-frame handling, `relative_alt`, virtual clock, $K=5$ RMS matcher with $2\times$ margin, 2-report drift alert, separate re-route) + `test_rig/sim.py` + GUI live panel. | `pytest tests/test_unit_mavlink.py tests/test_t7_live_mavlink.py` |
| **Slice 11** | **Part 8 — Full Verification Rig, Reports, NATO Template & Polish:** `test_rig/runner.py` (`reports/test_report.json` & `.md`), `docs/nato_parts.md` (flagged for applicant completion with `TBD` for unverified vendor fields), `docs/user_guide.md`, `README.md`, `requirements-lock.txt`. | `python -m minerva --run-test-rig --report-dir reports && pytest` |

---

## 10. Numbered Success Criteria

1. **SC-1 (Standalone Offline Executable & CI):** `minerva.exe` builds in `--onedir` mode on the `windows-2022` runner, stores SQLite data in the user data directory, makes zero external network calls (verified by socket monkeypatch), and passes both `minerva.exe --self-check` ($< 60\text{ s}$) and `minerva.exe --gui-smoke` (real `windows` platform window + marker file) from a clean temp folder outside the repo checkout (T8).
2. **SC-2 (Atomic 4D Plan & Radio Persistence):** Plans with $\ge 2$ waypoints, strictly increasing timestamps, finite coordinates, drone limits, 4D tunnels, and radio/GCS parameters are checked, approved, and persisted in a single SQLite transaction guarded by a compare-and-swap revision counter.
3. **SC-3 (Accurate Airspace, Crewed & Weather Ingest):** Offline parsers load exact TP 1820E (`3 Sep–29 Oct 2026`) coordinates and rules for `CYR229`, `CYR230`, and `CYR231` (256-gon outer circle) plus local overrides, reject unsupported Flight Levels (`FL`) in crewed plans with a clear message, and enforce `max(sustained, gust)` wind limits (T3).
4. **SC-4 (Bounded 4D Path Maker):** Across 100 known-feasible requests, $\ge 95\%$ return `FOUND` (the rest a defined `PlannerStatus`), 100% of `FOUND` paths pass an independent validator checking wind triangle, post-climb airspeed, $\pm 45^\circ$ turns, $L \ge R$ tangent fillets, zones, and existing plans, with median time $\le 2.0\text{ s}$ (T4).
5. **SC-5 (Exact Space/Time & Radio Conflict Detection at Scale):** Checker achieves 100% recall and 0% false alarms outside the $\pm 10\%$ band against the adaptive-step (`max_rel_speed * dt <= 1 m`) oracle and deterministic edge fixtures (T1), 100% agreement with the independent ITU-R P.525-5 aircraft-to-GCS RF evaluator (T2), identical results between exhaustive and `STRtree` modes, and median latency $\le 1.0\text{ s}$ at 200 plans and $\le 3.0\text{ s}$ at 500 plans (T5).
6. **SC-6 (Priority & Crewed-Precedence Resolution):** Resolver matches 100% (60/60) of `'resolvable'` and `'unresolvable'` labels while never modifying crewed plans (which outrank Priority 1) or already-approved plans (T6).
7. **SC-7 (4D Tunnel Export):** Approved plans generate 4D tunnels (`width_m`, `low_m`, `high_m`, `start_epoch_s`, `end_epoch_s`) exported as valid JSON and GeoJSON.
8. **SC-8 (MAVLink v2 Live Monitoring & Track Matching):** Minimal MAVLink v2 codec handles zero-trimmed payloads, multiple frames per datagram, CRC-16/MCRF4XX, and signed frames; matches known-ID and unambiguous ($2\times$ margin) unknown-ID tracks; flags drift within 2 report intervals on the virtual clock; and computes/accepts re-routes as separate steps (T7).
9. **SC-9 (Honest NATO Parts Template & Licensing):** `docs/nato_parts.md` is clearly marked to be completed from vendor datasheets by the applicant with `TBD` for unverified specs; `LICENSE`, `NOTICE.md`, and `THIRD_PARTY_LICENSES/` comply with all third-party and Transport Canada attribution rules.

---

## 11. Risks and Honest-Evidence Rules

### 11.1 Technical Risks and Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **R1: Discrepancies near separation thresholds in T1** | Use exact linear relative-motion interval math (`tol=1e-9`) in production; in T1 oracle use adaptive `dt` (`max_rel_speed * dt <= 1.0 m`), plant clashes $\ge 10\%$ inside, keep clean cases $\ge 10\%$ outside, and exclude/report $\pm 10\%$ band cases separately. |
| **R2: Grid A* expansion budget exhaustion** | Enforce `max_expansions = 40000`, set $\Delta xy \ge \max(250\text{ m}, \text{min\_turn\_radius\_m})$, keep time deterministic from path length, and return explicit `PlannerStatus` values. |
| **R3: Frozen `.exe` missing `pyproj`/`shapely` DLLs or writing to install dir** | Bundle `pyproj` data and `THIRD_PARTY_LICENSES/` in `minerva.spec`, store SQLite in the user data directory, and test `minerva.exe` from `$RUNNER_TEMP` in Slice 1. |
| **R4: TP 1820E handbook cycle update on 29 Oct 2026** | Record `"handbook_issue": "TP 1820E (2026-09-03 to 2026-10-29)"` in `suffield.geojson`, provide `zone_overrides.json`, and note that the 29 Oct 2026 issue must be re-checked. |

### 11.2 Mandatory Honest-Evidence Statements (`README.md` and `reports/test_report.md`)

`README.md` and every generated `test_report.md` must state that **the verification tests are engineering evidence offered towards the readiness-level assessment against the challenge's criteria, and that the assessment itself is the applicant's responsibility** (never claiming the software "proves TRL 5"). They must list these explicit limitations:

1. **Simulation-Only Validation:** Never flight-tested on real aircraft or connected to live air traffic control.
2. **Flat-Terrain Assumption:** All altitudes are metres above a single flat ground reference (`0 m` = Surface); terrain elevation is not modelled.
3. **Uniform Surface Wind:** METAR surface wind (and gusts via `max(sustained, gust)`) is applied uniformly across all altitudes per validity window; missing/stale weather requires an explicit operator synthetic wind or is rejected.
4. **Static Airspace Rules & Manual NOTAM Overrides:** `CYR229`, `CYR230`, and `CYR231` use TP 1820E (`3 Sep–29 Oct 2026`; next issue `29 Oct 2026` must be re-checked) with `CYR231`'s `"3 miles"` radius modelled as `3 NM = 5556 m` on a conservative 256-gon; dynamic NOTAMs are not parsed and require local override files.
5. **Flight Levels Unsupported:** Crewed plan import accepts feet or metres only and rejects Flight Levels (`FL`).
6. **MAVLink v2 Unauthenticated Telemetry:** `sysid` is not authentication; unsigned frames are unauthenticated and signed frames (`incompat_flags=0x01`) have their signature ignored under the `"not authenticated"` policy.
7. **Screening-Level Radio Model:** ITU-R P.525-5 free-space path loss between moving aircraft transmitters and fixed GCS receivers (`2 m` height, `10 m` near-field clamp) is a screening rule, not a terrain/clutter coverage prediction.
8. **Grid-Bounded Path Planner:** Produces the lowest-cost path within the configured grid, step size, and `40000`-expansion budget, not a globally optimal continuous trajectory.
