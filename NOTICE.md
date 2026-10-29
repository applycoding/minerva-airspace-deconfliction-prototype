# Third-party notices

Copyright (c) 2026 Arpan Bom. All rights reserved.

The evaluation-only licence does not restrict third-party components. They
remain under their own licences. Full licence texts copied from installed
packages are in THIRD_PARTY_LICENSES/ and are copied into the standalone bundle.

| Component | Version | Licence |
| --- | --- | --- |
| Python | 3.12.x (CI), 3.13 (local verification) | PSF-2.0 |
| PySide6-Essentials, Qt6, shiboken6 | 6.12.0 | LGPL-3.0-only |
| shapely | 2.2.0 | BSD-3-Clause |
| GEOS, bundled by shapely | wheel version | LGPL-2.1-or-later |
| pyproj | 3.8.0 | MIT |
| PROJ, bundled by pyproj | wheel version | MIT |
| numpy | 2.5.4 | BSD-3-Clause; bundled notices included |
| pytest (tests only) | 9.2.0 | MIT |
| PyInstaller (packaging only) | 6.22.3 | GPL-2.0-or-later WITH Bootloader-Exception |
| actions/checkout | v7 (v7.0.1) | MIT |
| actions/setup-python | v7 (v7.1.0) | MIT |
| actions/upload-artifact | v7 (v7.0.2) | MIT |
| pymavlink (Linux test harness only, not distributed) | 2.4.50 | LGPL-3.0 |
| ArduPilot Copter SITL (separate test program, never bundled or linked) | stable; run records version and SHA-256 | GPL-3.0 |

The application imports no GPL library. PyInstaller is a packaging tool used
under its bootloader exception. Dynamic Qt6/PySide6/shiboken6 LGPL-3.0 libraries
and GEOS LGPL-2.1 libraries remain separate shared library files in the onedir
bundle. Users may inspect and replace these libraries with compatible versions.
The evaluation-only permission does not restrict those rights. Keep the bundle
layout when replacing libraries; no static linking is used.

The Linux campaign imports pymavlink lazily inside its external test harness.
PyInstaller explicitly excludes it. ArduPilot SITL is downloaded at test time,
executes as a separate process and exchanges local telemetry and commands only.
Neither SITL nor pymavlink is part of the distributed desktop bundle.
Their source and licence notices are available at
https://github.com/ArduPilot/pymavlink and https://github.com/ArduPilot/ardupilot.

Upstream source: https://code.qt.io/, https://libgeos.org/,
https://github.com/shapely/shapely, https://github.com/pyproj4/pyproj,
https://proj.org/, https://numpy.org/, https://www.python.org/,
https://pyinstaller.org/, https://github.com/pytest-dev/pytest.
Action sources: https://github.com/actions/checkout,
https://github.com/actions/setup-python, https://github.com/actions/upload-artifact.

The NAV CANADA Designated Airspace Handbook (TP 1820E) is
© His Majesty the King in Right of Canada.
"Source of Canadian Airspace Data © 2026 Transport Canada".
Only the coordinates and altitude rules for CYR229, CYR230 and CYR231 required
for this demonstration are transcribed. The issue is effective 3 September to
29 October 2026; the next issue on 29 October 2026 must be re-checked.
CYR231's "3 miles" is modelled as 3 NM = 5556 m, enclosed by a conservative
256-vertex polygon. Dynamic NOTAMs require manual local overrides.
