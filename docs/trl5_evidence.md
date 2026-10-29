# MINERVA Airspace Deconfliction Prototype: TRL 5 Evidence

**Challenge:** Innovative Solutions Canada — *MINERVA Initiative: Uncrewed Aircraft System Deconfliction*  
**Question Addressed:** Pass/Fail Question Q2 (Proof that the prototype works and its current Technology Readiness Level)  
**Author:** Arpan Bom  
**Git Commit:** `e8334478cc4afcb73539517215cff9c65c86cc4a` (`e833447`)  
**Public Continuous Integration (CI) Run:** <https://github.com/applycoding/minerva-airspace-deconfliction-prototype/actions/runs/40917797547>

---

## 1. Summary

The MINERVA airspace deconfliction prototype has been tested and verified at **Technology Readiness Level 5 (TRL 5)** in simulation only; it has never been flown on a real aircraft. On Git commit `e8334478cc4afcb73539517215cff9c65c86cc4a` (`e833447`), automated public Continuous Integration (CI, an automated build and test server) run [`40917797547`](https://github.com/applycoding/minerva-airspace-deconfliction-prototype/actions/runs/40917797547) executed 107 component tests (`T1`–`T8` and supporting unit checks) and a six-scenario end-to-end campaign (`S1`–`S6`) across Windows Server 2022 and Ubuntu 24.04 Linux. Every component test and every scenario target passed: **62 out of 62 targets passed** across `S1`–`S5` on Windows Server 2022 (both from Python source and from the packaged stand-alone `minerva.exe` program running outside the source folder), and **78 out of 78 targets passed** across `S1`–`S6` on Ubuntu 24.04 Linux, including closed-loop flight control and in-flight re-routing of the external ArduPilot Copter 4.7.2 flight simulator.

---

## 2. What TRL 5 Means Here and Why This Evidence Meets It

At Technology Readiness Level 5 (TRL 5), the parts of a software system are joined together into one working application and tested in a simulated environment that matches key rules and conditions of the real operating area. This report does not claim TRL 5 by repeating that definition. Instead, it provides measured outputs from running the complete application against real geographical data, real database files, real network sockets, and an external autopilot simulator:

1. **Integrated software application:** Every test scenario runs the full desktop program as one connected system. The program loads files from disk, checks weather and aircraft limits, plans four-dimensional (4D: latitude, longitude, altitude, and time) flight paths, checks radio frequency (RF) interference, writes to a real SQLite database file (`.sqlite3`), listens on real User Datagram Protocol (UDP, a standard network message format) ports for live aircraft position reports, draws tracks and alerts on the real graphical user interface (GUI) window, and saves screenshots of that window.
2. **Simulated relevant environment around CFB Suffield:** All scenarios take place in the coordinate space of Canadian Forces Base (CFB) Suffield, Alberta. The scenarios load the real restricted airspace boundaries `CYR229`, `CYR230`, and `CYR231` from the NAV CANADA *Designated Airspace Handbook* (issue effective through 29 October 2026), together with scheduled crewed aircraft flights, aviation routine weather reports (METARs), up to 16 simultaneous uncrewed aircraft systems (UAS, or drones), and 12 simultaneous live UDP telemetry feeds.
3. **Closed-loop external flight simulator:** In scenario `S6_ARDUPILOT_SITL`, MINERVA connects over UDP using MAVLink (Micro Air Vehicle Link, a standard drone communication format) to a separate operating system process running the official ArduPilot Copter Software-In-The-Loop (SITL) version 4.7.2 flight physics and autopilot program. MINERVA uploads an approved route, tracks the simulated aircraft in flight, detects an off-plan lateral deviation within 2 position reports, computes and uploads a new route in `0.0048 s`, and monitors the aircraft until it arrives `14.65 m` from its goal.

---

## 3. Test Method

The test campaign uses an automated scenario runner built into the application (`--run-trl5`). The runner does not mock or bypass the user interface, database, or network layers:

* **Real window, database, and UDP receiver:** For each scenario, the runner opens the actual MINERVA desktop window, creates a fresh `.sqlite3` database file on disk, and starts the background UDP telemetry receiver thread. Simulated aircraft (in `S3`–`S5`) and the external ArduPilot SITL process (in `S6`) send position packets through real local UDP sockets to the receiver.
* **Persistence check on close and reopen:** At the end of every scenario (`S1` through `S6`), the runner closes the application, re-opens it pointing at the saved `.sqlite3` file, and checks that all active flight plans, statuses, and the database revision number match what was saved before closing.
* **Independent audit with separate reference checkers:** After each scenario finishes, an independent audit module checks the final set of approved flight plans using separate validation code (independent of the path planner). It verifies aircraft speed and climb limits, restricted zone boundaries, a mandatory 500 m buffer outside every restricted zone for all active start points, goal points, and ground control stations (GCS), 4D space-and-time separation between all aircraft, 100% containment of nominal flight paths inside their reserved 4D safety tunnels, and radio frequency separation.
* **Seeded and repeatable:** All pseudo-random operations—such as conflict planting in `S2` and the exact 10% (`0.1`) outgoing UDP packet loss in `S4`—use fixed random seeds so that any reviewer running the commands below gets repeatable results.

### How to Re-Run the Campaign

To run the full TRL 5 campaign from Python source on Windows or Linux:

```bash
python -m minerva --run-trl5 --report-dir DIR
```

To download the external ArduPilot Copter SITL binary on Linux and run all six scenarios (`S1`–`S6`) requiring the external simulator:

```bash
scripts/fetch_ardupilot_sitl.sh
python -m minerva --run-trl5 --report-dir DIR --require-sitl --sitl-dir DIR
```

To run the campaign on Windows using the stand-alone packaged executable:

```powershell
minerva.exe --run-trl5 --report-dir DIR
```

---

## 4. Test Environment

All evidence in this document was generated on public GitHub Actions virtual machines during CI run [`40917797547`](https://github.com/applycoding/minerva-airspace-deconfliction-prototype/actions/runs/40917797547) on 29 October 2026 against commit `e8334478cc4afcb73539517215cff9c65c86cc4a`:

| Environment Item | Windows Stand-Alone Exe (`windows-2022`) | Windows Source (`windows-2022-source`) | Linux Source + SITL (`ubuntu-24.04`) |
| --- | --- | --- | --- |
| **CI Runner Image** | GitHub-hosted Windows Server 2022 (`windows-2022`) | GitHub-hosted Windows Server 2022 (`windows-2022`) | GitHub-hosted Ubuntu 24.04 (`ubuntu-24.04`) |
| **Execution Mode** | Stand-alone `minerva.exe` copied outside the repository checkout | `python -m minerva` from repository checkout | `python -m minerva` from repository checkout |
| **CPU & Python** | Standard GitHub-hosted `windows-2022` x86_64 runner; bundled Python runtime inside `minerva.exe` (exact host metadata recorded in `report.json`) | Standard GitHub-hosted `windows-2022` x86_64 runner; Python interpreter running `python -m minerva` (exact host metadata recorded in `report.json`) | Standard GitHub-hosted `ubuntu-24.04` x86_64 runner; Python interpreter running `python -m minerva` (exact host metadata recorded in `report.json`) |
| **External Autopilot Simulator** | Not applicable (`S6` runs on Linux only) | Not applicable (`S6` runs on Linux only) | Official ArduPilot Copter SITL `4.7.2 (type 255)` run as a separate OS process |
| **External Simulator Binary SHA-256** | N/A | N/A | `caed35e4cb796ec06cac40b09566a18251771486b1cbac5e2bf16b7a5ed5045d` |
| **UTC Completion Timestamp** | `2026-10-29T17:11:07.669520Z` | Recorded in `windows-2022-source/report.md` and `report.json` | `2026-10-29T17:06:23.158103Z` |

Running `minerva.exe` from a directory outside the source repository checkout on Windows Server 2022 verifies that the packaged Windows executable contains all required code, libraries, and data files without relying on the development folder.

---

## 5. Who Ran and Reviewed It

The test runs reported here were triggered automatically on public GitHub Actions CI under the `applycoding` GitHub account by pushing commit `e8334478cc4afcb73539517215cff9c65c86cc4a` (authored by Arpan Bom).

The applicant must fill in the placeholders in the table below truthfully with the actual human test lead and reviewer names and job titles before submitting this document as formal challenge evidence.

| Role | Name and Job Title | Responsibility |
| --- | --- | --- |
| **Software Author & CI Trigger** | Arpan Bom | Wrote the prototype and test suite; pushed commit `e833447` under account `applycoding` to run the automated CI campaign. |
| **Test Lead** | `[NAME], [JOB TITLE]` | Verified test configuration, scenario inputs, and execution logs. |
| **Independent Reviewer** | `[NAME], [JOB TITLE]` | Reviewed raw CI artifacts (`report.md`, `report.json`, `events/*.jsonl`, `screenshots/*.png`, `db/*.sqlite3`) against challenge requirements. |

---

## 6. Results

In addition to the integrated scenarios below, **107 automated component tests** (`T1`–`T8` and supporting unit tests) passed in the same CI run.

### 6.1 Ubuntu 24.04 Summary (`reports/trl5/ci-run-40917797547/ubuntu-24.04`)

All **6 scenarios** and **78 out of 78 targets** passed in `292.159 s` total scenario time.

| Scenario | What It Tests | Targets Passed | Wall Seconds | Key Measured Numbers |
| --- | --- | --- | --- | --- |
| `S1_INGEST_PLAN_RF_DB` | File loading, weather/gust/zone/crewed/RF validation, automatic RF channel shift, operator escalation, 4D planning, and DB close/reopen persistence. | 11 / 11 | 2.409 | `7/7` planted errors caught; `4` plans accepted; RF resolved by `RADIO_CHANNEL_SHIFT`; max planner call `0.857 s` (`<= 5.0 s`); min zone buffer `643.58 m` (`>= 500 m`); `0` residual audit conflicts. |
| `S2_SWARM_16_DECONFLICTION` | Simultaneous 4D deconfliction of 16 drones and 2 crewed aircraft with planted conflicts and independent audit. | 10 / 10 | 5.454 | `108/108` planted conflicts detected; `16` drones + `2` crewed overlap for `58.82 s`; plan time max `1.235 s` (`<= 5.0 s`), 95th percentile (p95, the value under which 95% of samples fall) `1.233 s` (`<= 3.0 s`); `0` residual conflicts. |
| `S3_LIVE_TRACK_MATCHING` | 12 simultaneous UDP telemetry streams, matching known and unknown tracks, and abstaining on ambiguous tracks. | 11 / 11 | 31.179 | `720/720` UDP reports received across `12` sockets; `8/8` known tracks matched on first report; `2/2` unknown matched by `K=5`; `2/2` ambiguous abstained after `K=5`; receive-to-GUI latency max `0.00441 s`, p95 `0.00426 s`. |
| `S4_CONFORMANCE_AND_PACKET_LOSS` | Detection of lateral, vertical, and time tunnel exits, including lateral exit under 10% UDP packet loss. | 13 / 13 | 45.668 | Nominal alerts `0`; lateral, vertical, and temporal alerts in `2` intervals each; lateral alert under `10%` (`0.1`) packet loss in `3` intervals; receive-to-GUI max `0.00089 s`; alert-to-GUI max `0.00067 s` (`4` alerts). |
| `S5_DYNAMIC_REROUTE` | In-flight re-routing for lateral drift and pop-up crewed traffic, plus operator hold/land when boxed in. | 17 / 17 | 60.720 | Drift detected in `2` reports; `2/2` re-routes conform within `2` updates and fly within `15 m` of goal; box-in returns `NO_PATH_WITHIN_GRID` in `0.00588 s`; max re-route `0.00750 s`; `2` superseded histories kept; GUI latency max `0.00062 s`. |
| `S6_ARDUPILOT_SITL` | Closed-loop flight with external ArduPilot Copter SITL 4.7.2, off-plan lateral deviation, dynamic re-route, recovery, and arrival. | 16 / 16 | 146.729 | `100/100` nominal reports matched and conforming; lateral exit flagged in `2` reports; re-route in `0.00482 s` at DB rev `4`; conformance back in `1` report; `421/421` total reports matched; arrival at `14.65 m` (`<= 15 m`) in `146.42 s`. |

### 6.2 Windows Server 2022 Summary (`windows-2022` Stand-Alone `.exe` and `windows-2022-source`)

All **5 Windows scenarios (`S1`–`S5`)** and **62 out of 62 targets** passed in `145.780 s` total scenario time on the stand-alone `.exe` (`S6_ARDUPILOT_SITL` is `NOT_APPLICABLE` on Windows because the external ArduPilot SITL binary runs on Linux only). Both the stand-alone executable run (`windows-2022`) and the Python source run (`windows-2022-source`) passed all 62 targets.

| Scenario | What It Tests | Targets Passed | Wall Seconds (`.exe`) | Key Measured Numbers (Stand-Alone `minerva.exe`) |
| --- | --- | --- | --- | --- |
| `S1_INGEST_PLAN_RF_DB` | File loading, weather/gust/zone/crewed/RF validation, automatic RF channel shift, operator escalation, 4D planning, and DB close/reopen persistence. | 11 / 11 | 2.506 | `7/7` planted errors caught; `4` plans accepted; RF resolved by `RADIO_CHANNEL_SHIFT`; max planner call `0.883 s` (`<= 5.0 s`); min zone buffer `643.58 m` (`>= 500 m`); `0` residual audit conflicts. |
| `S2_SWARM_16_DECONFLICTION` | Simultaneous 4D deconfliction of 16 drones and 2 crewed aircraft with planted conflicts and independent audit. | 10 / 10 | 5.523 | `108/108` planted conflicts detected; `16` drones + `2` crewed overlap for `58.82 s`; plan time max `1.237 s` (`<= 5.0 s`), p95 `1.228 s` (`<= 3.0 s`); max planner/re-route call `1.192 s`; `0` residual conflicts. |
| `S3_LIVE_TRACK_MATCHING` | 12 simultaneous UDP telemetry streams, matching known and unknown tracks, and abstaining on ambiguous tracks. | 11 / 11 | 31.210 | `720/720` UDP reports received across `12` sockets; `8/8` known tracks matched on first report; `2/2` unknown matched by `K=5`; `2/2` ambiguous abstained after `K=5`; receive-to-GUI latency max `0.00491 s`, p95 `0.00447 s`. |
| `S4_CONFORMANCE_AND_PACKET_LOSS` | Detection of lateral, vertical, and time tunnel exits, including lateral exit under 10% UDP packet loss. | 13 / 13 | 45.695 | Nominal alerts `0`; lateral, vertical, and temporal alerts in `2` intervals each; lateral alert under `10%` (`0.1`) packet loss in `3` intervals; receive-to-GUI max `0.00109 s`; alert-to-GUI max `0.00087 s` (`4` alerts). |
| `S5_DYNAMIC_REROUTE` | In-flight re-routing for lateral drift and pop-up crewed traffic, plus operator hold/land when boxed in. | 17 / 17 | 60.846 | Drift detected in `2` reports; `2/2` re-routes conform within `2` updates and fly within `15 m` of goal; box-in returns `NO_PATH_WITHIN_GRID` in `0.00598 s`; max re-route `0.00677 s`; `2` superseded histories kept; GUI latency max `0.00071 s`. |
| `S6_ARDUPILOT_SITL` | External ArduPilot Copter SITL campaign (Linux only). | N/A | 0.002 | Marked `NOT_APPLICABLE` on Windows; tested on Ubuntu 24.04 (`16/16` targets passed). |

### 6.3 Full Per-Target Measurements Across Both Platforms

The table below lists every individual target across `S1`–`S6` and its exact measured value on Ubuntu 24.04 and Windows Server 2022 (`minerva.exe`).

| Scenario | Target | Expected | Measured (Ubuntu 24.04) | Measured (Windows 2022 `.exe`) | Pass |
| --- | --- | --- | --- | --- | --- |
| `S1` | RF interference resolves by channel reassignment | `RADIO_CHANNEL_SHIFT` | `"RADIO_CHANNEL_SHIFT"` | `"RADIO_CHANNEL_SHIFT"` | True |
| `S1` | No solution escalates to an operator | `True` | `true` | `true` | True |
| `S1` | Zone, crewed, RF, gust and stale-weather checks and planner rejection | `100%` | `{"detected": 7, "planted": 7}` | `{"detected": 7, "planted": 7}` | True |
| `S1` | Crewed records unchanged | `True` | `true` | `true` | True |
| `S1` | Four accepted requests | `4` | `4` | `4` | True |
| `S1` | Every measured planner/re-route call <=5 s | `5.0` | `0.8570834069999904` | `0.8830891000000065` | True |
| `S1` | Independent flight-limit, zone, space/time and RF audit has no residual conflicts | `0` | `{"residual": 0, "errors": {}}` | `{"residual": 0, "errors": {}}` | True |
| `S1` | No conflicts reported on the independently clean approved set | `0` | `0` | `0` | True |
| `S1` | Nominal paths are contained in their tunnels | `100%` | `100.0` | `100.0` | True |
| `S1` | Every active start, goal and GCS is >=500 m outside every zone | `500.0` | `643.5816119050141` | `643.5816119050141` | True |
| `S1` | All active fields and DB revision survive application close/reopen | `True` | `true` | `true` | True |
| `S2` | All independently planted conflicts detected; at least 14 | `100%, >=14` | `{"planted": 108, "detected": 108}` | `{"planted": 108, "detected": 108}` | True |
| `S2` | 16 drones and two crewed plans have a common active interval | `16+2` | `{"drones": 16, "crewed": 2, "overlap_s": 58.82352900505066}` | `{"drones": 16, "crewed": 2, "overlap_s": 58.82352900505066}` | True |
| `S2` | Planning and allocation per plan, max <=5 s and p95 <=3 s | `max <=5, p95 <=3` | `{"max_s": 1.2352864510000074, "p95_s": 1.2331355267500115}` | `{"max_s": 1.2367047000000184, "p95_s": 1.2281753249999383}` | True |
| `S2` | Crewed records unchanged | `True` | `true` | `true` | True |
| `S2` | Every measured planner/re-route call <=5 s | `5.0` | `1.1941623289999939` | `1.1922749000000294` | True |
| `S2` | Independent flight-limit, zone, space/time and RF audit has no residual conflicts | `0` | `{"residual": 0, "errors": {}}` | `{"residual": 0, "errors": {}}` | True |
| `S2` | No conflicts reported on the independently clean approved set | `0` | `0` | `0` | True |
| `S2` | Nominal paths are contained in their tunnels | `100%` | `100.0` | `100.0` | True |
| `S2` | Every active start, goal and GCS is >=500 m outside every zone | `500.0` | `643.5816119050141` | `643.5816119050141` | True |
| `S2` | All active fields and DB revision survive application close/reopen | `True` | `true` | `true` | True |
| `S3` | All eight known tracks match on first and subsequent reports | `100%` | `{"correct": 8, "total": 8}` | `{"correct": 8, "total": 8}` | True |
| `S3` | Both unknown tracks match by K=5 without false association | `2/2` | `2` | `2` | True |
| `S3` | Both ambiguous tracks abstain after K=5 | `2/2` | `2` | `2` | True |
| `S3` | Twelve simultaneous independent UDP sockets; all sent positions received | `720` | `720` | `720` | True |
| `S3` | No drift alerts on ten nominal tracks | `0` | `0` | `0` | True |
| `S3` | Receive-to-GUI latency max <=1 s and p95 <=0.25 s | `max <=1, p95 <=0.25` | `{"max_s": 0.004406130999996094, "p95_s": 0.004261598149980728}` | `{"max_s": 0.004912200000035227, "p95_s": 0.004471694999915598}` | True |
| `S3` | Independent flight-limit, zone, space/time and RF audit has no residual conflicts | `0` | `{"residual": 0, "errors": {}}` | `{"residual": 0, "errors": {}}` | True |
| `S3` | No conflicts reported on the independently clean approved set | `0` | `0` | `0` | True |
| `S3` | Nominal paths are contained in their tunnels | `100%` | `100.0` | `100.0` | True |
| `S3` | Every active start, goal and GCS is >=500 m outside every zone | `500.0` | `12371.272454024585` | `12371.272454024585` | True |
| `S3` | All active fields and DB revision survive application close/reopen | `True` | `true` | `true` | True |
| `S4` | Nominal track remains conforming | `0` | `0` | `0` | True |
| `S4` | LATERAL alert within 2 report intervals | `2` | `2` | `2` | True |
| `S4` | VERTICAL alert within 2 report intervals | `2` | `2` | `2` | True |
| `S4` | TEMPORAL alert within 2 report intervals | `2` | `2` | `2` | True |
| `S4` | LATERAL alert within 3 report intervals | `3` | `3` | `3` | True |
| `S4` | Seeded outgoing packet loss is exactly 10% | `0.1` | `0.1` | `0.1` | True |
| `S4` | Receive-to-GUI latency max <=1 s and p95 <=0.25 s | `max <=1, p95 <=0.25` | `{"max_s": 0.0008935139999834973, "p95_s": 0.0007645329999945716}` | `{"max_s": 0.0010938999998870713, "p95_s": 0.0009168999999928928}` | True |
| `S4` | New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | `max <=1, p95 <=0.25` | `{"alerts": 4, "max_s": 0.000666910999996162, "p95_s": 0.000663912949995904}` | `{"alerts": 4, "max_s": 0.0008660999999392516, "p95_s": 0.0008558999999650041}` | True |
| `S4` | Independent flight-limit, zone, space/time and RF audit has no residual conflicts | `0` | `{"residual": 0, "errors": {}}` | `{"residual": 0, "errors": {}}` | True |
| `S4` | No conflicts reported on the independently clean approved set | `0` | `0` | `0` | True |
| `S4` | Nominal paths are contained in their tunnels | `100%` | `100.0` | `100.0` | True |
| `S4` | Every active start, goal and GCS is >=500 m outside every zone | `500.0` | `13533.461665375673` | `13533.461665375673` | True |
| `S4` | All active fields and DB revision survive application close/reopen | `True` | `true` | `true` | True |
| `S5` | Drift alert received before re-route | `True` | `true` | `true` | True |
| `S5` | Lateral drift detected within two reports | `2` | `2` | `2` | True |
| `S5` | Pop-up crewed conflict detected | `True` | `true` | `true` | True |
| `S5` | Both accepted re-routes conform within two updates | `2/2` | `2` | `2` | True |
| `S5` | Box-in returns no path within five seconds | `no plan, <=5 s` | `{"status": "NO_PATH_WITHIN_GRID", "wall_s": 0.005877553999994234}` | `{"status": "NO_PATH_WITHIN_GRID", "wall_s": 0.00597620000007737}` | True |
| `S5` | Operator hold/land decision recorded; no unsafe replacement | `1` | `1` | `1` | True |
| `S5` | Two accepted old reservations remain as superseded history | `2` | `2` | `2` | True |
| `S5` | Pop-up crewed plan unchanged | `True` | `true` | `true` | True |
| `S5` | Both simulated drones fly the accepted route to within 15 m | `2/2` | `2` | `2` | True |
| `S5` | Every measured planner/re-route call <=5 s | `5.0` | `0.007500797000005832` | `0.00676700000008168` | True |
| `S5` | Receive-to-GUI latency max <=1 s and p95 <=0.25 s | `max <=1, p95 <=0.25` | `{"max_s": 0.000621305999999322, "p95_s": 0.0004930856499996139}` | `{"max_s": 0.0007060000000365108, "p95_s": 0.0005652199999872209}` | True |
| `S5` | New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | `max <=1, p95 <=0.25` | `{"alerts": 1, "max_s": 0.0005356679999977132, "p95_s": 0.0005356679999977132}` | `{"alerts": 1, "max_s": 0.0006852999999864551, "p95_s": 0.0006852999999864551}` | True |
| `S5` | Independent flight-limit, zone, space/time and RF audit has no residual conflicts | `0` | `{"residual": 0, "errors": {}}` | `{"residual": 0, "errors": {}}` | True |
| `S5` | No conflicts reported on the independently clean approved set | `0` | `0` | `0` | True |
| `S5` | Nominal paths are contained in their tunnels | `100%` | `100.0` | `100.0` | True |
| `S5` | Every active start, goal and GCS is >=500 m outside every zone | `500.0` | `12717.275474241816` | `12717.275474241816` | True |
| `S5` | All active fields and DB revision survive application close/reopen | `True` | `true` | `true` | True |
| `S6` | Every monitored SITL report matches the mapped ID | `100%` | `{"matched": 100, "reports": 100}` | N/A (Linux only) | True |
| `S6` | Every monitored nominal report conforms | `100%` | `{"conforming": 100, "reports": 100}` | N/A (Linux only) | True |
| `S6` | Lateral exit flagged within two received position reports | `2` | `2` | N/A (Linux only) | True |
| `S6` | Re-route atomically supersedes original at next DB revision | `4` | `4` | N/A (Linux only) | True |
| `S6` | Conformance returns within two reports | `2` | `1` | N/A (Linux only) | True |
| `S6` | Known-ID match across nominal, deviation and recovery | `100%` | `{"matched": 421, "reports": 421}` | N/A (Linux only) | True |
| `S6` | Arrival within 15 m and campaign hard cap | `<=15 m, <=300 s` | `{"distance_m": 14.647048933483983, "wall_s": 146.415373235}` | N/A (Linux only) | True |
| `S6` | External version and binary SHA-256 are recorded | `version + SHA-256` | `{"version": "4.7.2 (type 255)", "sha256": "caed35e4cb796ec06cac40b09566a18251771486b1cbac5e2bf16b7a5ed5045d"}` | N/A (Linux only) | True |
| `S6` | Every measured planner/re-route call <=5 s | `5.0` | `0.004818489999991016` | N/A (Linux only) | True |
| `S6` | Receive-to-GUI latency max <=1 s and p95 <=0.25 s | `max <=1, p95 <=0.25` | `{"max_s": 0.0006465149999712594, "p95_s": 0.00035499414997843806}` | N/A (Linux only) | True |
| `S6` | New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | `max <=1, p95 <=0.25` | `{"alerts": 1, "max_s": 0.00030903599997600395, "p95_s": 0.00030903599997600395}` | N/A (Linux only) | True |
| `S6` | Independent flight-limit, zone, space/time and RF audit has no residual conflicts | `0` | `{"residual": 0, "errors": {}}` | N/A (Linux only) | True |
| `S6` | No conflicts reported on the independently clean approved set | `0` | `0` | N/A (Linux only) | True |
| `S6` | Nominal paths are contained in their tunnels | `100%` | `100.0` | N/A (Linux only) | True |
| `S6` | Every active start, goal and GCS is >=500 m outside every zone | `500.0` | `15351.503524945825` | N/A (Linux only) | True |
| `S6` | All active fields and DB revision survive application close/reopen | `True` | `true` | N/A (Linux only) | True |

### 6.4 Traceability Table (`EO1`–`EO7`, `X1`, `X2`)

The outcome names and pass rules below are the ones in `docs/trl5_validation_plan.md`.

| Outcome | What it asks for | Scenarios | Result | Key evidence from the reports |
| --- | --- | --- | --- | --- |
| `EO1` Desktop operation | The real desktop program runs the work end to end on Windows | `S1`–`S5` (Windows exe and source), `S1`–`S6` (Linux) | **PASS** | `62/62` targets on the stand-alone `minerva.exe` run from outside the checkout; `62/62` from Windows source; `78/78` on Linux. Screenshots of the real window are in every report folder. |
| `EO2` Plan and radio storage | Every accepted plan stores waypoints, radio channel and tunnel, and reloads exactly | `S1`, `S2`, `S6` | **PASS** | Close/reopen check passes in every scenario; RF clash solved by `RADIO_CHANNEL_SHIFT` in `S1`; `0` residual RF conflicts in the independent audit. |
| `EO3` Approved reservations | Atomic global revisions; replaced plans kept as history; exact reload | `S1`, `S2`, `S5`, `S6` | **PASS** | `2` superseded reservations kept in `S5`; `S6` re-route replaces the original at DB revision `4`; reload equality in all scenarios. |
| `EO4` File ingestion | Real shipped zones, crewed-flight files and METARs; gusty and stale weather rejected | `S1`, `S2`, `S5` | **PASS** | `7/7` planted zone, crewed, RF, gust and stale-weather problems caught in `S1`; crewed records unchanged in `S1`, `S2`, `S5`. |
| `EO5` Bounded planning | Every path passes independent checks; every compute <= 5 s; `S2` per-plan p95 <= 3 s | `S1`, `S2`, `S5`, `S6` | **PASS** | `S2` per-plan max `1.235 s`, p95 `1.233 s` (Linux) and max `1.237 s`, p95 `1.228 s` (Windows exe); slowest single planner or re-route call `1.194 s` (`S2`, Linux); `0` residual audit conflicts. |
| `EO6` Detection and decision | 100% of planted conflicts found (at least 14 in `S2`); no false or leftover conflicts; crewed plans unchanged; operator decision when no solution | `S1`, `S2`, `S5` | **PASS** | `108/108` planted conflicts found in `S2` with 16 drones and 2 crewed aircraft active together; `0` conflicts reported on the clean approved set; operator escalation recorded in `S1`; hold/land decision recorded in `S5`. |
| `EO7` Cleared tunnels | 100% of nominal paths inside their tunnels; no zone, space/time or RF conflict found by the independent checker | `S1`–`S6` | **PASS** | `100.0%` containment and `{"residual": 0}` in every scenario; every active start, goal and ground station at least `643.58 m` outside every zone (rule: 500 m). |
| `X1` Live recovery | Typed alerts; compute <= 5 s; safe acceptance; recovery and arrival; operator escalation when no route exists | `S4`–`S6` | **PASS** | `S5`: `2/2` re-routes conform within 2 updates and arrive within 15 m; boxed-in case returns `NO_PATH_WITHIN_GRID` in `0.006 s` and records hold/land. `S6`: re-route in `0.0048 s`, back in tunnel after `1` report, arrival `14.65 m` from goal. |
| `X2` Track association and conformance | Known IDs 100%; unknown matched by K=5; ambiguous tracks abstain; exits flagged within 2 intervals (3 at 10% loss); latency max <= 1 s, p95 <= 0.25 s | `S3`–`S6` | **PASS** | `S3`: `720/720` reports over 12 sockets, `8/8` known, `2/2` unknown, `2/2` ambiguous abstained. `S4`: lateral, vertical and time exits in `2` intervals, `3` at exactly 10% loss. `S6`: `421/421` SITL reports matched. Worst receive-to-screen latency `0.0049 s`. |

---

## 7. Highest Test Done (`S6_ARDUPILOT_SITL`)

The highest-fidelity test completed is scenario `S6_ARDUPILOT_SITL` on Ubuntu 24.04 (`146.729 s` total wall time, `16/16` targets passed). Instead of using MINERVA's internal kinematic track generator, `S6` launches the official external **ArduPilot Copter SITL version `4.7.2 (type 255)`** flight simulator binary (`SHA-256: caed35e4cb796ec06cac40b09566a18251771486b1cbac5e2bf16b7a5ed5045d`) as a separate operating system process.

The scenario executes the following end-to-end sequence:

1. **Plan approval and upload:** MINERVA plans a conflict-free 4D flight path near CFB Suffield (with active start, goal, and GCS `15351.50 m` outside the nearest restricted zone, well above the `500 m` minimum) and sends the mission waypoints to the external ArduPilot simulator over MAVLink UDP.
2. **Nominal flight monitoring:** As the simulated quadcopter takes off and flies the route, MINERVA receives its live MAVLink telemetry packets and updates the GUI window (`0.000647 s` max receive-to-GUI latency, `0.000355 s` p95). Across the monitored nominal segment, `100` out of `100` (`100%`) position reports match the assigned aircraft ID, and `100` out of `100` (`100%`) conform to the approved 4D tunnel.
3. **Off-plan deviation detection:** The test forces the external autopilot off its approved lateral path. MINERVA detects the lateral tunnel exit within **2 received position reports** (matching the `<= 2` report target) and displays the alert on the GUI in `0.000309 s`.
4. **Dynamic re-route and recovery:** MINERVA calculates a new conflict-free 4D route from the aircraft's current position in **`0.004818 s`** (target `<= 5.0 s`). When accepted, the new reservation atomically replaces the original plan in the SQLite database at revision **`4`**, and the updated waypoints are uploaded to ArduPilot. The aircraft turns onto the new path and returns to 4D tunnel conformance within **1 position report** (target `<= 2`).
5. **Arrival and independent audit:** Across the entire flight (nominal, deviation, and recovery), `421` out of `421` (`100%`) telemetry reports match the aircraft ID. The simulated quadcopter reaches its goal **`14.647 m`** from the target coordinates (target `<= 15 m`) in **`146.415 s`** (target `<= 300 s`). Afterward, the independent audit confirms `0` residual conflicts and `100.0%` tunnel containment, and closing and re-opening the application confirms that all database records and revision `4` persist intact.

---

## 8. Limits

In keeping with strict engineering honesty, the test reports establish the following boundaries and limitations on what has been shown:

* **Simulation only; never flown:** No physical drone, physical autopilot board, physical radio modem, or live air traffic control system was used in any test.
* **No real radios:** Radio frequency checks use the International Telecommunication Union (ITU-R P.525) free-space path-loss formula with fixed `2 m` ground control station antenna heights and a `10 m` minimum near-field distance clamp. It is a fast screening check, not a terrain-aware radio coverage prediction.
* **Flat ground at 750 m:** All altitudes use a flat ground reference, with `750 m` Above Mean Sea Level (AMSL) as the ArduPilot SITL home elevation. Digital terrain elevation maps, hills, wind shear, terrain masking, radio reflections (multipath), and directional antenna patterns are not modelled. Wind and gust limits are applied uniformly across the area.
* **Static zones without a live NOTAM feed:** Restricted airspace zones (`CYR229`, `CYR230`, `CYR231`), crewed flight schedules, and weather reports (METARs) are read from local files. The included NAV CANADA *Designated Airspace Handbook* data expires on **29 October 2026** and must be updated before operational use. Notice to Airmen (NOTAM) overrides are entered manually, and high-altitude Flight Levels are not supported.
* **Telemetry not authenticated:** MAVLink UDP packets are unencrypted and unsigned; cryptographic message signing is not checked.
* **Local loopback network:** All UDP telemetry tests run over the local computer loopback interface (`127.0.0.1`). This verifies software socket handling and GUI latency, not physical radio link range or interference.
* **Bounded planner and scripted operator choices:** The 4D grid planner stops after at most `40,000` node expansions or a `9.5 s` search deadline; it is not globally optimal and dense traffic can require an operator decision. During the automated scenarios, operator choices (such as accepting a re-route or ordering hold/land when boxed in) are made by the scenario script rather than a human clicking the mouse.
* **ArduPilot SITL runs on Linux only:** Scenario `S6_ARDUPILOT_SITL` is executed only on Ubuntu 24.04 Linux and is marked `NOT_APPLICABLE` on Windows.

---

## 9. Next Step to TRL 6

Reaching **Technology Readiness Level 6 (TRL 6)** requires demonstrating a representative prototype in a relevant physical environment outside the laboratory. The planned steps to move from TRL 5 to TRL 6 are:

1. **Range Control coordination at CFB Suffield:** Secure flight test permission and operating procedures with CFB Suffield Range Control, using current NAV CANADA airspace data and active range schedules.
2. **Live hardware and radio integration:** Connect a Windows laptop running the stand-alone `minerva.exe` application to physical field telemetry radios communicating with at least one real uncrewed aircraft running an ArduPilot-compatible autopilot.
3. **Live outdoor flight demonstration:** Conduct an outdoor flight test at CFB Suffield where a human operator loads current weather and airspace notices, plans and approves a mission in MINERVA, monitors live radio telemetry from the flying drone alongside live or injected crewed range traffic, and executes an in-flight deviation alert and re-route or hold/land command over the physical radio link.

---

## 10. Where the Evidence Is

All evidence files are committed in this repository and are also downloadable from the public GitHub Actions CI run:

* **Public GitHub Actions CI Run URL:**  
  <https://github.com/applycoding/minerva-airspace-deconfliction-prototype/actions/runs/40917797547>
* **Downloadable CI Run Artifacts:**
  * `minerva-windows-evidence` (contains both the stand-alone `.exe` and Windows source campaign outputs)
  * `minerva-linux-evidence` (contains the Ubuntu 24.04 + ArduPilot Copter SITL 4.7.2 campaign outputs)
* **Committed Repository Directories:**
  * `reports/trl5/ci-run-40917797547/windows-2022/` — Windows Server 2022 stand-alone `minerva.exe` run from outside the source checkout (`S1`–`S5` PASS, `62/62` targets).
  * `reports/trl5/ci-run-40917797547/windows-2022-source/` — Windows Server 2022 Python source run (`S1`–`S5` PASS, `62/62` targets).
  * `reports/trl5/ci-run-40917797547/ubuntu-24.04/` — Ubuntu 24.04 Python source run with external ArduPilot Copter SITL 4.7.2 (`S1`–`S6` PASS, `78/78` targets).
* **Files Inside Each Report Directory:**
  * `report.md` — Markdown summary table, per-scenario target tables, and limits list.
  * `report.html` — Formatted standalone HTML version of the report.
  * `report.json` — Complete machine-readable metrics, timings, target checks, and host metadata.
  * `events/*.jsonl` — Timestamped JSON Lines event logs for every scenario.
  * `screenshots/*.png` — Screenshots captured from the real MINERVA desktop window during each scenario.
  * `db/*.sqlite3` — The actual SQLite database files written, closed, re-opened, and audited in each scenario.
