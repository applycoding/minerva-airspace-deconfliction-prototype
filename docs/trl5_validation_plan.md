# MINERVA integrated scenario campaign

Author: Arpan Bom. Simulation only; never flown.

This document describes the implemented campaign. Its measured gates supply
engineering evidence towards the applicant's readiness assessment. They do not
by themselves establish a readiness level. `docs/DEVIATIONS.md` records the
corrections to the earlier proposed fixtures and interfaces.

## 1. Method and evidence

Each executed scenario opens the actual offscreen `MainWindow` against a fresh
SQLite file. The driver uses the editor, import methods, checker, planner,
resolver and live panel. Live scenarios use separate real UDP sender sockets
and the actual panel's 50 ms Qt polling timer. Qt events are pumped at intervals
of at most 5 ms. Telemetry time advances with wall time, mapped onto 29 October
2026 starting at 16:00 UTC; no accelerated telemetry clock is used.

`time.perf_counter()` measures planning, re-routing, receive-to-GUI processing
and whole-scenario duration. Seed 20261118 controls deliberate loss. Events
contain actual reports, IDs, positions, timestamps, dropped report indices,
conflict records, approvals, revisions, decisions and screenshots. Window grabs
must be non-null, at least 1000 by 700 pixels and over 1000 bytes as saved PNGs.

After each executed scenario, the independent path validator and adaptive-step
space/time and RF oracles recheck every APPROVED plan against all other active
plans, crewed plans and shipped zones. The relative sampling step is <=1 m.
The audit also verifies flight limits and edge timing, nominal segment
containment in tunnels, >=500 m site clearance, zero conflicts on the independently
clean set, and equality of all SQLite tables and reconstructed active plans after
closing and reopening the application. Superseded history is retained.

## 2. Real geometry, dates and files

The zone source is `data/zones/suffield.geojson`. CYR231 is the conservative
256-vertex representation of a 5556 m circle at N50.26666667 W111.18333333.
CYR230's southern edge is N50.21666667 and CYR229 begins at N50.3375. The
CYR229 summer/unlimited rule applies on the scenario date. The Handbook issue
ends on 29 October 2026; these simulations do not validate a newer issue.

Most missions use UTM Zone 12N offsets from N50.150000 W111.420000. The GCS
sites are (50.15, -111.42), (50.17, -111.43), and (50.19, -111.44), with fixed
2 m receiver heights. Ordinary starts/goals lie west/south-west of the range.
The three crossing requests use (50.2664969064, -111.2703257613) to
(50.2160667919, -111.2198654385), each about 644 m outside CYR231. Their
straight chords cross CYR231, so the planner must detour. The southern endpoint
extends east of the approximate W111.27 operating boundary: otherwise no such
chord is geometrically possible. Every actual active start, goal and GCS is
checked against all three polygons, not a hand-drawn bounding box.

Shipped scenario inputs under `data/trl5/` are:

| File | Contents |
| --- | --- |
| `calm.txt` | CYXH 291600Z 00000KT, valid 16:00 to 23:59 UTC |
| `highwind.txt` | CYXH 291600Z 28026G38KT, same validity; gust 19.548872 m/s |
| `stale.txt` | CYXH 291000Z 27010KT, expired at 11:00 UTC |
| `s1_crewed.json` | CREWED-101, 150 ft = 45.72 m, eastbound 1000 m at origin northing +2200 m, 16:02 to 16:03:40 UTC |
| `s2_crewed.json` | CREWED-201/202, eastbound northing +10000 m, 300 ft and 120 m, 16:00 to 16:10 UTC |
| `s5_popup.json` | CREWED-POPUP-501, eastbound at northing +600 m, easting +1500 to +2500 m, 70 m, 16:00:01 to 16:01:11 UTC |
| `s5_box.json` | CREWED-WALL-502, easting +4000 to +4001 m, origin northing, 70 m, 16:00 to 16:20 UTC |

All offsets refer to the origin above. Exact geographic coordinates are in the
JSON files and each report's `metrics.clearances` and approval events. Radio
models use real transmitter power and gains, receiver threshold, frequency,
bandwidth and guard band. There are no polarization, endurance, flexible-start,
EIRP or maximum-altitude model fields and no claims about those quantities.

## 3. Outcomes and targets

| Outcome | Scenarios | Gate |
| --- | --- | --- |
| EO1 desktop operation | S1-S5 | All applicable targets pass; Windows source and standalone runs are separate evidence |
| EO2 plan and RF storage | S1, S2, S6 | Every accepted plan has waypoints, radio and tunnel; reload equality |
| EO3 approved reservations | S1, S2, S5, S6 | Atomic global revisions; superseded records retained; exact reload |
| EO4 file ingestion | S1, S2, S5 | Real shipped zones, crewed JSON and METARs; gust and stale rejection |
| EO5 bounded planning | S1, S2, S5, S6 | All generated paths pass independent validation; every compute <=5 s; S2 per-plan p95 <=3 s |
| EO6 detection and decision | S1, S2, S5 | 100% planted detection; >=14 in S2; zero false or residual conflicts; crewed unchanged; no-solution operator decision |
| EO7 cleared tunnels | S1-S6 | 100% nominal containment and zero independently found zone, space/time or RF conflicts |
| X1 live recovery | S4-S6 | Typed alerts; compute <=5 s; safe acceptance; recovery and arrival; operator escalation when no route exists |
| X2 and track association | S3-S6 | Known-ID 100%; unknown by K=5; ambiguous abstention; exits <=2 intervals, <=3 at 10% loss; latency max <=1 s and p95 <=0.25 s |

The requested selection is explicit in the report. A subset can pass its own
targets but outcomes depending on unselected scenarios remain NOT_FULLY_EVALUATED.
A full platform campaign requires every applicable scenario.

## 4. Executed scenarios

### S1_INGEST_PLAN_RF_DB

Import the zones, calm METAR and CREWED-101. Detect CYR231 on UAS-S1-01's raw
chord and plan around it with `shortest_time`. Submit UAS-S1-02 along the crewed
corridor at 45.72 m; detect the space/time clash and resolve the candidate by a
departure shift without changing crewed traffic. Its airspeed limit is 1.2 m/s,
so the link remains active through the later RF mitigation trials.

UAS-S1-03 uses northing +3500 m, departure 16:03:20, and 2425 MHz, overlapping
UAS-S1-02's 2422 MHz assignment. Detect RF interference and use the production
resolver's 5800 MHz alternate channel. UAS-S1-04 at northing +5000 m receives
no solution under the high-wind file; record an operator +360 s delay, load the
covering calm file and approve only after rechecking. UAS-S1-05/06 explicitly
exercise high-wind and stale-weather rejection by both checker and planner.
Restore calm weather for the final audit. Four plans must be approved; all
seven planted detection/rejection checks must succeed.

Screenshots: `after_ingest`, `rf_conflict`, `approved_tunnels`, `reloaded`.

### S2_SWARM_16_DECONFLICTION

Import CREWED-201/202. Fourteen 1000 m eastbound missions have starts at the
origin plus northing offsets 0, 400, ..., 5200 m, 60 m altitude and the same
16:02 departure. The other two use the CYR231-crossing chord at 200 and 400 m.
All eighteen reservations must share a positive time interval.

Raw requests share RF channels and deliberately propose unsafe intermediate
transits through the first mission's departure pad. Independently enumerate
space/time and RF clashes and the two known CYR231 intrusions, then require
100% detection and at least fourteen planted conflicts. The operator records
channel allocations 2400 + 40*i MHz; the real planner removes unsafe intermediate
transits between each submitted pair of endpoints. It uses `avoid_radio` on
one request and `shortest_time` on the others. Require 16 approved drones,
unchanged crewed plans, per-request total planning/allocation max <=5 s and
p95 <=3 s, zero independent residual conflicts and complete tunnel containment.
This validates simultaneous parallel lanes and two zone detours, not sixteen
vehicles at a single simultaneous intersection.

Screenshots: `swarm_16_map`, `reloaded`. Timings are saved per request.

### S3_LIVE_TRACK_MATCHING

Twelve approved eastbound 1000 m plans use northing offsets 0..3600 m at 400 m
spacing, plus 4500 and 4700 m. All have 60 m altitude, 50 m half-width, 15 m
vertical margin, 15 s time buffer and distinct channels. Twelve independent UDP
sockets send at 2 Hz for 30 wall seconds: 720 positions.

IDs 1..8 are mapped by source address, system and component through the panel.
IDs 109/110 are unmapped and fly plans 9/10; they must match on their fifth
report. IDs 111/112 fly the midpoint between the last two plans, 100 m from
either; both must abstain as AMBIGUOUS after K=5. Known-ID matching must be
correct on every report beginning with the first. All sent positions must be
received; the ten nominal tracks must have no drift alerts. The pytest subset
uses six reports per drone over three wall seconds and records that shorter
duration; it does not substitute for the full CLI run.

Screenshots: `live_panel_matching`, `reloaded`.

### S4_CONFORMANCE_AND_PACKET_LOSS

Five approved 1000 m eastbound plans start at northing offsets 0, 600, 1200,
1800 and 2400 m, altitude 60 m. Each has a distinct channel and the S3 tunnel
margins. Over 45 wall seconds each sender has 90 nominal 0.5 s report slots.
A remains nominal. B steps 85 m north on slot index 40, C steps 30 m upward on
index 42, D follows the point twenty seconds behind from index 48, and E has
the same lateral exit as B with exactly nine seeded outgoing datagrams dropped,
including index 40. Indices are zero-based and all drops are logged.

Require zero nominal false alerts. B/C/D must alert as LATERAL/VERTICAL/TEMPORAL
within two nominal report intervals; E within three including the lost interval.
All receive-to-GUI samples are retained; require max <=1 s and p95 <=0.25 s.
Other ignored MAVLink message IDs are not packet loss.

Screenshots: `conformance_alerts`, `reloaded`.

### S5_DYNAMIC_REROUTE

Three approved drones use real UDP. A starts at northing +3000 m and flies
800 m east at 60 m; an 85 m northward deviation must alert within two reports.
Compute through the selected track in the panel and separately accept the
replacement. B starts at easting +2000 m and flies 1000 m north at 70 m.
Import the shipped crewed popup crossing its original trajectory, show the
conflict, then compute and accept a safe 3D re-route from the live state.

Both replacements must return to conformance within two updates and be flown
with wall-clock positions to within 15 m of their goals. Each computation must
finish within five seconds. Old reservations remain SUPERSEDED and replacement
approvals advance the actual global DB revision without changing the popup.

C starts at easting +4000 m, 70 m altitude. Import the long crewed reservation
at its live departure location. No safe outgoing edge exists; require no plan
within five seconds, then use the operator hold/land decision button. That
records a simulated directive and closes the old reservation without committing
an unsafe replacement. There is no battery or endurance model.

Screenshots: `popup_conflict`, `reroute_accepted`, `operator_escalation`, `reloaded`.

### S6_ARDUPILOT_SITL

Linux only: execute the official external Copter binary with `--model +`,
`--speedup 1`, home `50.15,-111.42,750,0`, defaults `copter.parm,<extra.parm>`,
`-w` and `--serial1 udpclient:127.0.0.1:<ephemeral receiver port>`. Connect the
TCP client on 5760 to allow startup. The extra file sets MAV1/2/3_POSITION=5,
other MAVn stream groups to zero, serial1 MAVLink2, terrain off and sufficient
navigation speeds. Retry GUIDED and arm every two seconds up to 90 s, allowing
real EKF settling. Require takeoff to at least 38 m AGL within forty seconds.

Approve a 650 m northbound 4D mission starting after takeoff, 40 m AGL,
10 m/s, 50 m half-width, 15 m vertical margin and 30 s time buffer. Stream
SET_POSITION_TARGET_GLOBAL_INT relative-altitude targets at interpolated
`now + 1.5 s`. Require 100% Known-ID match and nominal conformance over twenty
wall seconds. Hold a guide target 120 m east to cause a real simulated lateral
exit; require detection within two position reports. Compute and accept through
the GUI, fly the replacement using interpolated targets, require recovery within
two reports and arrival within 15 m. The total flight harness cap is 300 s.

Record SHA-256, AUTOPILOT_VERSION, observed commit prefix and git-version.txt
when present. Count ignored other message IDs separately from unparsed/invalid
frames; neither count establishes a telemetry loss rate. The supplied local
binary identifies the fb773567 prefix of the specified full commit
fb773567896014da007bca58358704d4a0d8516f.

Screenshots: `sitl_conforming`, `sitl_drift_alert`, `sitl_rerouted`, `reloaded`.
Stdout is `events/S6_ARDUPILOT_SITL_sitl_stdout.log`.

## 5. Runner, CLI and reports

The implementation lives in `src/minerva/trl5/`: `runner.py`, `gui_driver.py`,
`scenarios.py`, `oracle_audit.py`, `sitl_harness.py`, and `report_writer.py`.

```text
python -m minerva --run-trl5 --report-dir DIR
python -m minerva --run-trl5 --report-dir DIR --scenarios S1,S3
python -m minerva --run-trl5 --report-dir DIR --require-sitl --sitl-dir DIR
minerva.exe --run-trl5 --report-dir DIR
```

An uninstalled checkout needs `PYTHONPATH=src`. Headless runs use
`QT_QPA_PLATFORM=offscreen`. S1-S5 work in the frozen bundle with shipped data;
pymavlink is excluded and SITL is never bundled. Linux lacking either the
binary/default parameters or pymavlink records S6 as NOT_RUN. Windows records
NOT_APPLICABLE. NOT_RUN never becomes PASS; `--require-sitl` returns 2 for
NOT_RUN. Target failures return 1. Only all applicable selected targets passing
returns 0. Requiring SITL also includes S6 in a subset selection.

DIR contains `report.json` (schema_version `1.0.0`), `report.md`, a self-contained
`report.html` with base64 PNGs, `events/<full_scenario_id>.jsonl`,
`screenshots/<full_scenario_id>_<milestone>.png` and
`db/<full_scenario_id>.sqlite3`. Unexecuted S6 has a reason event and no database.

Reports include author, seed, UTC timestamp, OS/CPU/Python/package versions,
frozen status, Git SHA from environment or read-only git query, and CI run URL
when available. They list selected scenarios, per-scenario status, wall duration,
target objects (`target_id`, `description`, `expected`, `measured`, `passed`),
measured metrics, screenshots, event log and database. Summary counts distinguish
PASS, FAIL, NOT_RUN and NOT_APPLICABLE. Traceability does not promote missing
scenario coverage to a completed outcome.

The exact verdict is `All TRL 5 scenario targets met` only when all applicable
selected scenarios pass; otherwise it is `TRL 5 validation FAILED: <ids>`.
No target result is supplied from a canned value or a production check alone.

## 6. External harness licensing and download

`pymavlink==2.4.50` (LGPL-3.0) is test-only and imported inside the harness
function. ArduPilot (GPL-3.0) is an external process, never linked or distributed
with MINERVA. Notices describe both. The fetch script retrieves the official
`Copter/stable/SITL_x86_64_linux_gnu/arducopter` and `git-version.txt`, extracts
the full commit and fetches that commit's default `copter.parm` from the source
repository. Curl makes up to three retries after the initial attempt and the script prints all SHA-256s.

## 7. CI and regression tests

The existing `ci` workflow retains both jobs, previous tests, builds, smoke
checks and @v7 action versions. Windows runs source scenarios into
`reports/trl5/windows-2022-source` and the frozen executable from outside the
checkout into `reports/trl5/windows-2022`. Linux downloads SITL into runner temp,
installs test-only pymavlink 2.4.50 and requires all scenarios into
`reports/trl5/ubuntu-24.04`. Existing artifact uploads include reports/trl5.

`tests/test_trl5_campaign.py` executes real S1 and shortened S3, validates
schema, actual timings, socket counts, received reports, independent audit,
PNG content, SQLite integrity and reload equality. It also verifies missing
SITL and Windows applicability status handling without launching SITL in pytest.
The unchanged T1-T8 tests remain enabled.

## 8. Readiness and evidence status

A local pass establishes only the recorded local simulation results. A Windows
source/frozen pass and Linux CI pass on the same reviewed change remain necessary
before asserting all platform requirements are met. No unexecuted Windows or CI
results are represented as measurements. `docs/trl5_evidence.md` summarizes the
actual available report, personnel placeholders and outstanding verification.
The owner reviews and commits changes and evidence; the runner makes no Git writes.

## 9. Honest limits

Simulation only; never flown. No aircraft, hardware autopilot or radio has been
flight-tested. Outdoor range testing and Range Control integration remain later
readiness work. Altitudes use flat ground, with 750 m AMSL for SITL home, and
uniform surface wind. There is no terrain model, wind shear, multipath, terrain
masking or antenna radiation pattern. RF is free-space screening, not coverage.
Zones, crewed flights and weather are local files rather than live NOTAM,
ADS-B/Mode-S or AWOS inputs. Telemetry is unauthenticated, unencrypted local UDP;
message signatures are not verified and physical datalink contention is untested.
The bounded 3D grid uses 250 m horizontal and 30 m vertical defaults, up to
40000 expansions and a 9.5 s search deadline; it does not promise a globally
optimal continuous route. Dense intersecting strategic traffic can require an
operator. These limits appear in every report. The readiness assessment remains
the applicant's responsibility.

## 10. Practical risks

Shared-runner jitter can fail latency gates and is reported as failure, not
excluded. PNGs must contain real window pixels. Receiver and sender UDP ports
are OS-assigned; external SITL still needs TCP 5760 free. EKF settling can take
about fifty seconds and is included in wall time. Downloads can fail; S6 is
then unrun and cannot silently pass. Cached zone geometry and conservative
bounds accelerate the real planner without bypassing any final conflict check.
