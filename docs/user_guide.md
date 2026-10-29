# Operator guide

Simulation only; never flown. Use this application for evaluation with simulated
plans. Read the evidence limits in README.md before interpreting a result.

## Offline installation

Obtain the complete Windows zip from a completed build. Extract every file to a
writable folder and open minerva.exe. Keep the executable, data, libraries and
licence folder together. The bundle does not need Python or network access.
For source installation, use Python 3.12 or 3.13 and the offline commands in
README.md, with wheels prepared for that computer. No package download is needed
at runtime. A source checkout including tests is required for --run-test-rig.

The database is stored at %LOCALAPPDATA%/Minerva/minerva.sqlite3 on Windows.
Set MINERVA_DB_PATH before launch to select another writable database file.
Close the application before copying the database and any adjacent -wal/-shm
files for backup. Do not place it inside a read-only installation directory.

## Create and approve a plan

1. Select New plan. Set the callsign, priority (1 highest through 4 lowest), and
   objective: shortest_time, avoid_zones or avoid_radio.
2. Edit the JSON form. waypoints must include latitude, longitude, alt_m and
   epoch_s, shown as UTC text such as 2026-10-28T12:00:00Z. Use at least two
   points with increasing times. limits contains airspeed, climb/descent, turn
   radius and wind limits. radio contains frequency/bandwidth in MHz, power in
   dBm, gains in dBi, receiver threshold, guard gap and fixed ground receiver
   latitude/longitude. Import JSON loads this same form format.
3. Supply weather that covers the whole flight window. The explicit synthetic
   wind line takes wind-from degrees, speed and gust in metres per second,
   followed by UTC start/end. Select Use synthetic wind to apply it. The bundled
   weather is sample data; it may not cover your chosen time.
   Load METAR file selects an offline file with explicit UTC validity windows.
   Import crewed plans loads the supported crewed JSON/text format into the
   database. Both inputs persist across closing and reopening the application.
4. Select Run planner. Inspect its status at the bottom of the window and the
   resulting map. Select Check conflicts and inspect the table.
5. Resolve candidate tries departure time, altitude, route, then frequency
   changes. Review the new values and check again. Crewed and approved plans
   are protected; unresolved cases need operator action.
6. Approve candidate saves only a conflict-free candidate. If the database has
   changed since a check, review and check again. Export JSON or GeoJSON writes
   the current form's tunnel; check and approve the intended plan first.

The map has no online tiles. It paints local vectors and reserved corridors.
The restricted zone list shows bundled zones. Load overrides accepts a JSON
object mapping zone IDs to active and/or ceiling_m, for example
{"CYR229": {"active": true, "ceiling_m": 4572}}. Re-check plans after changing
rules. The handbook cycle must be re-checked for 29 Oct 2026; NOTAM updates are
manual. Altitude is above a flat ground reference, not terrain or sea level.

## Live watch

Select Start loopback receiver. Its address and assigned port appear in the
panel. A local simulator must send MAVLink v2 datagrams to that address; the
receiver supports HEARTBEAT and GLOBAL_POSITION_INT. It uses relative altitude.
The GUI has no built-in simulator start button. The source simulator is in
src/minerva/test_rig/sim.py and the T7 tests show repeatable examples.

For a known stream, enter source port, sysid, compid, approved plan ID separated
by commas and select Map known ID. The source port is the sender's port, not
the displayed receiver port. Without a mapping, five reports are needed for
trajectory matching. Ambiguous tracks remain unassigned. Identifiers and signed
frames are not authenticated.

Drift is flagged after two consecutive reports outside the reserved corridor.
Select a track in the live table or selector. The table shows each stream's
plan association, conformance and LATERAL, VERTICAL or TEMPORAL violation.
Compute re-route prepares a proposal for the selected matched report. Inspect the
status, then select Accept re-route (operator confirmation) only after reviewing
it. Acceptance separately replaces that plan in the database. A stale database
revision requires computing and reviewing a new proposal. Stop receiver ends
watching; closing the window also stops it. This does not command an aircraft.

If computation has no solution, Record hold / land in place records the operator's
simulated decision and closes the old reservation without approving an unsafe
replacement. It sends no command to any aircraft.

## Checks and reports

--self-check runs a short fixed check. --gui-smoke shows the window for two
seconds and can write a --marker-file. --run-test-rig --report-dir reports runs
source verification and records failures as well as measured values. Read
reports/test_report.md and docs/VERIFICATION.md together. A source GUI check
using offscreen rendering does not establish that a frozen Windows window works.

`--run-trl5 --report-dir DIR` runs the integrated simulation campaign. Use
`--scenarios S1,S3` for an explicitly labelled subset. The report directory
contains report.json, report.md, a self-contained report.html, screenshots,
event logs and scenario databases. On Linux, the separate external flight
simulator is required for a complete pass; `--require-sitl --sitl-dir DIR`
returns exit 2 if it cannot run. On Windows that scenario is not applicable.
See trl5_validation_plan.md and trl5_evidence.md for scope and measured evidence.
