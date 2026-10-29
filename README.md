# MINERVA

Copyright (c) 2026 Arpan Bom. All rights reserved.

MINERVA is an offline Windows desktop prototype for creating, checking and storing
simulated flight plans around CFB Suffield. It shows an offline map, flight plan
form, conflict table, restricted zones, tunnel exports and a live telemetry panel.
It checks aircraft separation, restricted areas, wind and possible radio clashes.
It is not an operational flight clearance system or a controller for aircraft or
physical radios.

## Install and run

For the Windows bundle, unzip the whole minerva folder and run minerva.exe.
Keep its supporting files together. No Python installation or internet connection
is needed for that bundle. Source use requires Python 3.12 or 3.13 and the pinned
packages in requirements-lock.txt. With a prepared wheel folder, install offline:

```text
python -m pip install --no-index --find-links wheelhouse -r requirements-lock.txt
python -m pip install --no-index --no-deps --no-build-isolation -e .
python -m minerva
```

The lock records the supplied Linux environment; prepare matching wheels for the
target Windows/Python version, including Windows-only packaging dependencies.
Build from source with `python -m PyInstaller --noconfirm --clean minerva.spec`.
SQLite data defaults to %LOCALAPPDATA%/Minerva/minerva.sqlite3 on Windows and
~/.local/share/minerva/minerva.sqlite3 on Linux. MINERVA_DB_PATH overrides it.
See [the operator guide](docs/user_guide.md) for input formats and live watch.

## Test

```text
python -m minerva --self-check
python -m minerva --run-test-rig --report-dir reports
python -m pytest
```

On Linux, set QT_QPA_PLATFORM=offscreen for GUI tests. The self-check is a short,
fixed storage/ingest/export check; it does not launch the verification rig. The
rig runs T1–T8 source tests and writes JSON, plain English, individual test logs
and XML results. It exits nonzero on failures or skipped checks. Frozen Windows
checks are checked by CI workflow; source results do not establish their outcome.
The tests need loopback UDP sockets; a restricted host can prevent those tests.
See [actual verification results](docs/VERIFICATION.md).

## Evidence and limits

The verification tests are engineering evidence offered towards the readiness-level
assessment against the challenge's criteria, including TRL 5. The assessment itself
is the applicant's responsibility. These results do not establish TRL 5.

Simulation only; never flown. The application has never been flight-tested on real
aircraft or connected to live air traffic control.

All altitudes are metres above a single flat ground reference (0 m = Surface).
Terrain elevation is not modelled. METAR surface wind applies uniformly at every
altitude during its validity window; limits use max(sustained, gust). Missing or
stale weather requires explicit operator synthetic wind or the request is rejected.

CYR229, CYR230 and CYR231 use static TP 1820E rules for 3 Sep–29 Oct 2026.
The 29 Oct 2026 issue must be re-checked. CYR231's “3 miles” is modelled as
3 NM = 5556 m inside a conservative 256-sided polygon. Dynamic NOTAMs are not
parsed; they require manual local override files. Crewed plan import accepts
feet or metres above ground and rejects Flight Levels (FL).

MAVLink v2 telemetry is not authenticated. sysid is an identifier, not proof of
identity. Unsigned frames are unauthenticated; signatures on signed frames are
ignored under the “not authenticated” policy.

Radio checks use ITU-R P.525-5 free-space loss between moving aircraft transmitters
and fixed ground receivers at 2 m height, with a 10 m near-field clamp. This is a
screening rule, not a terrain or clutter coverage prediction.

The planner searches a configured grid with a step size and a 40000-expansion
budget. It does not promise a globally optimal continuous trajectory.

## Licence

All rights reserved. The application is evaluation-only under [LICENSE](LICENSE).
Third-party components retain their own licences; see [NOTICE.md](NOTICE.md) and
THIRD_PARTY_LICENSES. The directory bundle keeps shared libraries separate.
