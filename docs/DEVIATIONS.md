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

The initial CI placeholder has been replaced in Slice 11 with the full source
verification rig and report upload. Windows source/build/real-platform smoke
steps remain in place; Windows execution remains unverified until CI runs.

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

Slice 10 verification is blocked on this host: creating an AF_INET UDP socket
raises PermissionError (errno 1, Operation not permitted), before bind or send.
The five real loopback UDP tests remain enabled and fail visibly. They are not
skipped or replaced with fake sockets. Additional direct-datagram tests check
codec, matching, drift and separate SQLite re-route acceptance, but do not
establish the T7 UDP gate. No network permissions or alternate interpreter were
used. The implementation still requires real 127.0.0.1 UDP on a permitted host.

## TRL 5 campaign

The campaign plan preceded inspection of the real models and shipped geometry.
The following corrections follow the binding campaign instructions. PLAN.md is
unchanged. Every gate remains a measured gate; no existing test was weakened.

- Geometry comes from `data/zones/suffield.geojson`. CYR231 is the 5556 m circle
  centred at N50.26666667 W111.18333333; CYR230 reaches N50.21666667 and CYR229
  starts at N50.3375. The original operating sites were inside restricted zones.
  Ordinary missions now use N50.15 W111.42 as their UTM origin, with three GCS
  sites at (50.15, -111.42), (50.17, -111.43), (50.19, -111.44). SITL home is
  (50.15, -111.42, 750 m AMSL). The independent audit measures every active
  start, goal and GCS against all three real polygons and requires >=500 m.
- An operating rectangle wholly west of W111.27 cannot have straight chords
  through a circle whose west edge is approximately W111.261. Three crossing
  requests therefore use endpoints (50.2664969064, -111.2703257613) and
  (50.2160667919, -111.2198654385), each approximately 644 m outside CYR231.
  This deliberately extends the approximate west/south-west area eastward on
  its southern side. S1 and two S2 requests use that chord and must detour.
- The real types have transmitter power/gains, receiver threshold, guard band,
  fixed 2 m GCS height, flight limits and waypoint times. They have no EIRP,
  polarization, endurance, maximum-altitude or flexible-start field. These
  invented constraints are not claimed as verified. Crewed imports are actual
  `FlightPlan` records, not airspace-volume walls. S5's no-solution fixture
  occupies the live start with a long crewed reservation, preventing any safe
  outgoing edge. S1's operator escalation uses covering high-wind weather;
  an operator records +360 s delay and loads a covering calm file before
  approving. No false claim of a locked departure or battery model is made.
- The original GUI slot names, Database object and telemetry module names did
  not exist. The campaign drives the real `MainWindow`, its SQLite connection,
  editor, `LivePanel`, `UDPReceiver` and `LiveTracker`. Small operator methods,
  import buttons, a per-track table/selector and a hold/land decision button
  were added. Hold/land is a recorded simulation decision that closes the
  old reservation; it sends no aircraft command and approves no invalid path.
- SQLite revisions are global compare-and-swap revisions, not per-aircraft
  revision columns. A re-route has a distinct plan ID; the original record
  becomes SUPERSEDED in the same transaction. Events preserve old/new IDs and
  revisions. Equality after close/reopen covers every table, including history
  and decisions, plus reconstructed active plan fields. Known-ID mappings are
  session operator mappings, recorded in events rather than invented DB fields.
- S1 uses four accepted requests, plus high-wind and stale-weather rejections.
  Its real resolver chooses 5800 MHz, one of its existing alternate channels,
  rather than the plan's 5805 MHz. The fixture keeps the conflicting receiver
  active through every delay trial. Calm METAR wind is explicitly 00000KT;
  the gust fixture remains 28026G38KT. Stale input has its own expired window.
- S2 retains 16 simultaneous approved drones plus two simultaneous crewed
  plans, >=14 planted conflicts and the original latency gates. Fourteen
  missions have parallel 400 m lanes and two detour around CYR231 at 200/400 m.
  Raw requests deliberately propose unsafe intermediate transits and shared
  RF channels. The operator assigns distinct 40 MHz-spaced channels and uses
  A* between the submitted endpoints, removing unsafe intermediate transits.
  This does not claim sixteen simultaneous aircraft at a single crossing hub.
  Audit checks all drone pairs, crewed reservations, zones and RF independently.
- The first original-geometry crossing exhausted the production 9.5 s budget;
  an early S2 run also missed the unchanged 3 s p95 target. Geometry is now
  cached by immutable coordinates, disjoint bounds are rejected conservatively,
  and the planner filters spatially impossible non-overlapping RF reservations.
  Its admissible speed bound uses its actual 0.85 airspeed factor, with goal
  altitude used only to break equal-cost queue ties. Hard edge checks and final
  full-set validation remain. The unchanged T1-T8 tests pass after these changes.
- The real campaign exposed a resolver exception when a negative altitude trial
  reached tunnel construction. Such trials now return invalid before building
  a tunnel. Weather and stored zones load from the database on restart instead
  of silently resetting operator state or incrementing revision just by opening.
- Conformance now distinguishes cross-track LATERAL, altitude VERTICAL and
  along-path/window TEMPORAL violations. The alert description includes the
  type. Receive and GUI update times use perf_counter; all packet latencies
  are retained. S4 uses 90 real 0.5 s reports, with exactly nine seeded dropped
  outgoing position datagrams on its loss track, including the first exit.
- SITL uses the supplied 4.7.x stable binary, serial0 TCP 5760, a real ephemeral
  UDP receiver, MAV1/2/3_POSITION=5 and other MAVn stream groups disabled.
  Arming retries GUIDED and arm every 2 s for up to 90 s. The hard flight cap
  is 300 s, as required by the correction, rather than the obsolete 240 s.
  Its 650 m northbound mission begins after takeoff; 1.5 s lead interpolated
  position targets honour plan timing. The commanded deviation is 120 m east.
  Actual binary SHA-256, AUTOPILOT_VERSION and commit prefix are recorded;
  git-version.txt is included when available. Other MAVLink message IDs are
  reported as ignored, never interpreted as packet loss. Remaining unparsed
  frames are counted separately without claiming a cause or a loss rate.
- `pymavlink==2.4.50` is imported lazily inside the Linux harness only and is
  explicitly excluded from the executable. SITL is an external child process,
  never bundled or linked. The fetch script uses the requested official stable
  URL and the matching full commit from git-version.txt for copter.parm, with
  three retries and printed hashes. It was not downloaded locally;
  network access was neither needed nor attempted here.
- Existing CI job names, steps and @v7 action versions remain. New source and
  frozen Windows runs use the requested separate report directories; the frozen
  run starts outside the checkout. Linux fetches SITL and requires S6. No new
  cache or matrix job replaces the existing jobs. Reports remain under the
  existing ignored `reports/` directory; local evidence is kept as local
  evidence, not labelled Windows or Ubuntu CI evidence that has not run.
- The earlier UDP restriction recorded above no longer applies in this session:
  real loopback UDP and TCP both work. The first whole-suite attempt used an
  unwritable default home directory; subsequent whole-suite runs set the
  supported MINERVA_DB_PATH override to a writable /tmp file. Source CLI runs
  use PYTHONPATH=src because the supplied environment has no editable install.
  The specified interpreter is used throughout; no installation was attempted.
- The supplied simulated sender pairs HEARTBEAT and GLOBAL_POSITION_INT in
  each 2 Hz datagram. The original separate 1 Hz heartbeat schedule was not
  added; position report counts, socket concurrency and all conformance targets
  remain unchanged. The fast pytest live subset has six reports per sender,
  whereas the CLI always uses the full sixty-report S3 window.
- Final reports distinguish the full receive-to-GUI latency series from new
  alert transitions. Alert-only max and p95 are measured separately, with null
  values when no alert exists; zero is never substituted for absent evidence.
  Candidate resolution and rejected-weather calls are timed at the GUI boundary
  as well as planner and live re-route calls.
