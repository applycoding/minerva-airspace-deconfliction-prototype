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
