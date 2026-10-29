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
