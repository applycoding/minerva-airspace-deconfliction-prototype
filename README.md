# MINERVA

Copyright (c) 2026 Arpan Bom. All rights reserved.

Offline Windows desktop prototype. Slices 1–4 provide the desktop shell,
coordinate transforms, domain models, atomic SQLite storage, offline ingest,
and tunnel exports. Planning, conflict checking, live telemetry, full panels,
and the T1–T8 verification rig are scheduled for later slices.

The verification tests are engineering evidence offered towards the
readiness-level assessment against the challenge's criteria. The assessment
itself is the applicant's responsibility.

Simulation only; never flight-tested on real aircraft or connected to live air
traffic control. All altitudes are metres above a single flat ground reference
(0 m = Surface); terrain elevation is not modelled. METAR surface wind and
max(sustained, gust) apply uniformly at all altitudes. Missing or stale weather
requires an explicit covering operator synthetic observation or is rejected.

Static CYR229/230/231 rules use TP 1820E (3 Sep–29 Oct 2026); the 29 Oct issue
must be re-checked. CYR231's "3 miles" is modelled as 3 NM = 5556 m with a
conservative 256-gon. Dynamic NOTAMs require manual overrides. See
[the boundary decision](docs/DEVIATIONS.md). Crewed import supports feet or
metres above ground; Flight Levels are unsupported.

Future telemetry will be unauthenticated: sysid is not authentication; signed
MAVLink v2 frames will have their signatures ignored under the "not
authenticated" policy. The planned ITU-R P.525-5 radio model is free-space
screening between aircraft transmitters and fixed GCS receivers (2 m height,
10 m near-field clamp), with no terrain/clutter prediction. The planned path
maker is bounded by its grid, step size and 40000-expansion budget and does not
promise globally optimal continuous trajectories. These later functions are
not validated by the present self-check.

Use Python 3.12 or 3.13 with the pinned dependencies in pyproject.toml.
Install with `python -m pip install -e . --no-deps --no-build-isolation`.
Run `python -m pytest`, `python -m minerva --self-check`, or
`python -m minerva` for the desktop shell. Linux GUI tests require
`QT_QPA_PLATFORM=offscreen`. Build with
`pyinstaller --noconfirm --clean minerva.spec`. The onedir bundle keeps shared
libraries replaceable and includes data and licence texts. The SQLite path is
MINERVA_DB_PATH, otherwise LOCALAPPDATA/Minerva on Windows or
~/.local/share/minerva on Linux, never the install directory by default.

Offline weather files contain one explicit ISO UTC start/end window followed
by a METAR per line. This avoids guessing year/month from METAR day numbers.
Crewed JSON uses `plans` with `plan_id`, `callsign`, and `waypoints` containing
`lat_deg`, `lon_deg`, `altitude` (e.g. "3000 ft") and `time_utc`.
The text form is `PLAN id callsign`, then `WP lat lon altitude UTC` records,
then `END`. These are bounded ICAO-style local records, not a full ICAO message
grammar. Zone override JSON maps zone IDs to `active` and/or `ceiling_m`.

Tunnel segment time intervals include the configured time buffer, vertical
bounds are clipped at Surface, and horizontal width is twice the half-width.
JSON/GeoJSON epoch fields are formatted as ISO UTC at the export boundary.
GeoJSON corridors are built in UTM metres and transformed to [longitude,
latitude]. Each feature carries the segment's space/time bounds.
