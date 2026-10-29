# Verification of slices 1–4

Simulation only; never flown. These checks cover the first four slices, not
the later T1–T8 acceptance gates or a readiness-level assessment.

Host: Linux, Python 3.13.5, supplied pinned dependencies. All Python commands
used /workspace/trivision/minerva/build/venv/bin/python.

The following slice acceptance selections passed with QT_QPA_PLATFORM=offscreen:

- tests/test_unit_coords_models.py: 13 passed.
- tests/test_unit_db.py: 16 passed.
- tests/test_t3_zones.py -k ingest: 16 passed.
- tests/test_unit_coords_models.py -k tunnel: 6 passed, 7 deselected.

The coordinate tests require less than 0.01 m projection round-trip error.
Circle containment is checked at 1024 sampled points and at 5500/5600 m.
Tests assert every transcribed polygon vertex, seasonal UTC boundaries,
SQLite stale-revision rejection across two connections and transaction rollback,
finite/ordered plan invariants, crewed FL rejection, weather coverage and gusts,
and valid tunnel polygons with longitude first. GUI shell creation is tested
offscreen; this is not evidence of Windows platform-plugin operation.

The source --self-check passed. It uses a fixed, non-recursive pipeline with
real sample ingest, a temporary SQLite database, persistence round trip, and
JSON/GeoJSON export. It does not run or claim the later flight/conflict rig.

The editable wheel built offline, but installation into the supplied venv
was denied by its read-only filesystem. The pytest source-path fallback works.

The exact required PyInstaller command was attempted. It failed because the
host has no libpython3.13.so.1.0. No executable was produced, so neither a
Linux frozen self-check nor Windows frozen/GUI checks are reported as passed.
See DEVIATIONS.md. Windows CI includes the pinned build and clean-directory
frozen checks; that workflow has not been executed here.

## Slices 7 and 8

Simulation only; never flown. These checks ran on the supplied Linux host with
Python 3.13.5 and the pinned packages. They do not establish Windows execution
or real aircraft performance.

The planner uses north-referenced octants and keeps every searched edge in the
returned trajectory. Horizontal spacing is the larger of the requested spacing
and minimum turn radius. The bounded search extends six cells beyond the
endpoint displacement on each horizontal axis and four altitude layers beyond
the endpoint altitude range, with a ground floor. The exact goal is a boundary
node connected from nearby cells; its connecting edge receives the same turn,
length, timing and conflict checks. The expansion budget defaults to 40000; a
9.5 second search deadline also returns BUDGET_EXHAUSTED.

Soft objective penalties use the maximum proximity to zone polygons and fixed
GCS receivers: 1/(1 + distance/250 m) for zones and 1/(1 + distance/1000 m) for
radio receivers. These proximity preferences do not replace hard conflict
checks. The three weight pairs are those in section 6.2 of PLAN.md.

T4 runs 100 deterministic known-feasible requests with an independently checked
corridor witness for every request. Cases vary objective, wind, altitude,
heading, nearby zones and existing reservations. Each request has a separate
process-enforced 10 second deadline. All 100 returned FOUND and all 100 passed
the independent validator. The validator recomputes wind, edge duration,
airspeed, climb/descent, turn and fillet limits without planner helpers. It
checks zone intersections independently and uses the adaptive sampling and
radio reference oracles for existing reservations. Sampling is reference
evidence, not a proof for arbitrarily shallow separation penetrations.
Focused tests exercise blocked endpoints, missing/stale/excessive weather,
strong tailwinds, rejected headwinds, stretched-climb airspeed rejection,
optional hover edges, budget exhaustion and distinct objective costs.

T6 matches 60/60 explicit labels: 20 resolved with zero checked conflicts and
40 escalated. Inputs are compared with deep snapshots, including approved and
crewed reservations. Separate tests cover every mitigation step, the numerical
priority order, creation-time tie breaking, crewed precedence over Priority 1,
clean candidates and failed channel alternatives. Only draft candidates can
receive modifications; approved or crewed candidates require operator action.

Slice acceptance measurements: tests/test_t4_planner.py passed 14 tests in
22.80 seconds; the 100-request planning median was 0.030893 seconds and p95
was 0.504107 seconds. tests/test_t6_resolution.py passed 6 tests in 0.17 seconds.
The complete source regression suite passed 90 tests in 23.67 seconds with
QT_QPA_PLATFORM=offscreen. No Windows execution was performed in this slice.

## Slices 9 and 10

Simulation only; never flown. The desktop integrates the existing planner,
checker, resolver, SQLite approval, zone list and JSON/GeoJSON tunnel exports.
The plan form edits callsign and priority plus waypoint, airframe and radio/GCS
JSON values. Waypoint display times use UTC ISO text. Synthetic surface wind
requires an explicit operator action. The map paints offline UTM vectors,
tunnel widths and plans with detected conflicts. The live panel listens only
on loopback, maps source port and MAVLink IDs, and separates re-route computation
from operator acceptance. Telemetry and signatures are not authenticated.

The Slice 9 acceptance selection passed: 1 passed, 2 deselected in 0.42 seconds.
All three T8 source/manifest tests passed in 3.25 seconds, including the source
self-check and two-second offscreen GUI smoke marker. This does not establish
Windows or frozen executable behavior. The spec explicitly lists the new GUI,
live and simulation modules as hidden imports.

The Slice 10 acceptance command produced 5 passed and 5 failed in 0.25 seconds.
All failures occurred at IPv4 socket creation, denied by the host. Direct
codec-to-tracker checks passed: CRC agrees with a separate byte recurrence,
zero trimming/padding and relative altitude decode correctly, signed frames
carry the not-authenticated policy, malformed frames are counted, unknown
tracks match after five reports, ambiguous tracks abstain, and drift appears
on the second consecutive outside report. A direct-datagram re-route took
0.054952 seconds, passed conflict checking and was separately accepted into
SQLite at revision 2. These measurements do not establish 100% UDP track match
accuracy or the complete T7 gate.

The full suite with QT_QPA_PLATFORM=offscreen and a temporary MINERVA_DB_PATH
produced 98 passed and 5 failed in 26.30 seconds. The five failures are the socket
restriction above. The default user directory is read-only here, so a temporary
database override is necessary for the existing GUI shell regression test.
No existing test assertions were changed. Windows/frozen verification and real
loopback T7 acceptance remain unfinished.

## Slice 11

Simulation only; never flown. The verification tests are engineering evidence
for the applicant's readiness-level assessment, including TRL 5; the assessment
itself is the applicant's responsibility. No readiness level is established here.

The source rig now runs the unchanged T1–T8 acceptance files in separate test
processes, keeps individual XML and text logs, and writes reports/test_report.json
and reports/test_report.md. Each entry records its target, outcome, counts,
measured test durations and acceptance output. Planner and scale measurements
come from the acceptance tests' own output. Environment versions are read from
installed package metadata. Failures and skips prevent a zero exit status.
The frozen portion of T8 is labelled “checked by CI workflow”; it is not reported
as a locally measured result. The short self-check remains separate and passed.

All commands used /workspace/trivision/minerva/build/venv/bin/python, Python
3.13.5 on Linux, with QT_QPA_PLATFORM=offscreen and a temporary MINERVA_DB_PATH.
The final source rig returned exit 1 with 66 passed test cases and 5 failed:

- T1: 100/100 planted clashes recalled, zero false alarms among 100 clean
  scenarios, 6/6 hand fixtures passed, 74 excluded-band draws counted.
- T2: 50/50 seeded agreements plus boundary fixtures; 3 test cases passed.
- T3: all 27 zone and ingest test cases passed.
- T4: 100/100 FOUND and independently validated. Median 0.031228 seconds,
  p95 0.518325 seconds. All 14 test cases passed.
- T5: identical conflict sets at 10, 50, 200 and 500 active plans, with five
  timing repetitions per mode. At 200 plans, exhaustive median/p95 were
  0.009695/0.009774 seconds and indexed median/p95 were 0.012237/0.015389 seconds.
  At 500 plans, exhaustive median/p95 were 0.024609/0.025685 seconds and indexed
  median/p95 were 0.033553/0.035102 seconds. Both test cases passed. The runner
  reported an Intel Xeon processor, 8 logical CPUs and 16779640832 bytes RAM.
- T6: 60/60 labels matched, 20 resolved and 40 escalated; all 6 tests passed.
- T7: 2 direct-datagram tests passed. Five UDP tests failed at socket creation
  with PermissionError, errno 1: known and unknown track matching, ambiguity
  and source identity, drift/re-route acceptance, and altitude/time/reset.
  No UDP accuracy or latency result is claimed.
- T8: all 3 source tests passed, including the offscreen smoke marker and source
  self-check. Windows platform rendering and frozen executable checks were not
  run here and remain for CI.

The full regression suite produced 99 passed and 5 failed in 40.15 seconds.
The new report-schema test runs the real rig into a temporary directory and
checks all eight entries, environment versions, individual measurements,
failure details, timing summaries, report files and honest frozen-check scope.
It passed. No existing test was edited or weakened.

The acceptance command's rig stage returns nonzero because of the five blocked
UDP tests, so its && would not start pytest. The full suite was therefore run
separately to collect all results. The owner still needs to run the complete
acceptance command on a host permitting loopback UDP and run Windows CI.
The dependency lock records the supplied environment's pip freeze, not evidence
of a Windows installation or a successful frozen build.

A final regression selection excluding only the five socket-blocked cases passed:
99 passed, 5 deselected in 38.59 seconds. This selection still ran the new report
test, whose child rig attempted all UDP cases and preserved their failures.
It does not turn the full T7 gate into a pass. git diff --check was clean.
