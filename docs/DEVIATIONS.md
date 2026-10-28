# Decisions required by conflicting requirements

CYR229 uses the summer ceiling before 07:01:00Z on 1 December and the winter
ceiling from that instant. The Handbook leaves the minute after 0700Z undefined;
the summer ceiling is applied conservatively in that gap. Tests cover 06:59:59Z,
07:00:30Z and 07:01:01Z. This follows the clarified task requirement.

The installed PySide6-Essentials 6.12.0 and shiboken6 6.12.0 distributions
contain no dist-info/licenses folders or packaged licence text. An on-disk
inspection confirmed this. Without network access, the real LGPL v3 text and
its referenced GPL v3 text were copied from /usr/share/common-licenses instead.
Other requested licence texts, including GEOS, came from dist-info/licenses.

CI runs the implemented source tests and fixed slices 1–4 self-check for now.
The section 8 full T1–T7 rig/report step requires Slice 11 and is intentionally
not presented as completed evidence. Windows source/build/real-platform smoke
steps and artifact upload are provided; Windows execution remains unverified
until the owner runs CI.

The exact outer-radius formula radius/cos(pi/256) failed the circle containment
test at edge-midpoint tangencies because of floating-point cancellation at UTM
northings near 5.6 million metres. The implementation adds 0.00000001 m to the
computed outer radius. The unchanged test now requires containment at all
1024 sampled circle points, including those tangencies. This is a numerical
outward guard, not an increase of the stated airspace radius.

Local packaging verification is blocked by the host, before module analysis:
PyInstaller 6.22.3 reports that libpython3.13.so.1.0 is missing. The required
Python reports Py_ENABLE_SHARED=1 and LIBDIR=/usr/lib/x86_64-linux-gnu, but a
filesystem search found no libpython3.13 shared library. No alternate Python,
package installation, or network access was used. The spec remains a normal
onedir build for the pinned environment. The Linux build and frozen self-check
are not claimed as passing; they require the host's matching shared library.

The editable wheel built with the required Python and no build isolation, but
installation failed because the supplied venv is read-only. Source tests use
the explicitly permitted pytest pythonpath=["src"] fallback.
