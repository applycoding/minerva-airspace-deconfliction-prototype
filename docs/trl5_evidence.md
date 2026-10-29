# Local integrated scenario evidence

Author: Arpan Bom. Simulation only; never flown.

These tables are generated from [the local report](../reports/trl5/local/report.json). The full [offline HTML report](../reports/trl5/local/report.html) embeds the actual window screenshots. This is a Linux workstation run, not a Windows or Ubuntu CI result.

Run UTC: 2026-10-29T16:41:45.224672Z. Base checkout Git SHA: 03658711abf48aeb1d9fb282bc2e363526167f53. The working changes were uncommitted during this run; that SHA does not identify a reviewed commit containing the changes. No Git writes were performed.

Command: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen /workspace/trivision/minerva/build/venv/bin/python -m minerva --run-trl5 --report-dir /tmp/trl5_local --require-sitl --sitl-dir /workspace/trivision/minerva/sitl`.

Environment: {"os_name": "Linux-6.12.94+-x86_64-with-glibc2.41", "platform_tag": "local", "cpu_model": "Intel(R) Xeon(R) Processor", "cpu_count": 8, "python_version": "3.13.5", "frozen_executable": false, "package_versions": {"PySide6-Essentials": "6.12.0", "shapely": "2.2.0", "pyproj": "3.8.0", "numpy": "2.5.4"}}.

All TRL 5 scenario targets met.

| Scenario | Status | Wall seconds | Target checks passed | Residual conflicts | Tunnel containment | Reload equality |
| --- | --- | --- | --- | --- | --- | --- |
| S1_INGEST_PLAN_RF_DB | PASS | 1.594 | 11/11 | 0 | 100.0% | True |
| S2_SWARM_16_DECONFLICTION | PASS | 3.130 | 10/10 | 0 | 100.0% | True |
| S3_LIVE_TRACK_MATCHING | PASS | 30.803 | 11/11 | 0 | 100.0% | True |
| S4_CONFORMANCE_AND_PACKET_LOSS | PASS | 45.475 | 13/13 | 0 | 100.0% | True |
| S5_DYNAMIC_REROUTE | PASS | 60.631 | 17/17 | 0 | 100.0% | True |
| S6_ARDUPILOT_SITL | PASS | 146.782 | 16/16 | 0 | 100.0% | True |

## S1_INGEST_PLAN_RF_DB

| Target | Expected | Measured |
| --- | --- | --- |
| RF interference resolves by channel reassignment | RADIO_CHANNEL_SHIFT | "RADIO_CHANNEL_SHIFT" |
| No solution escalates to an operator | True | true |
| Zone, crewed, RF, gust and stale-weather checks and planner rejection | 100% | {"detected": 7, "planted": 7} |
| Crewed records unchanged | True | true |
| Four accepted requests | 4 | 4 |
| Every measured planner/re-route call <=5 s | 5.0 | 0.46400280999660026 |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} |
| No conflicts reported on the independently clean approved set | 0 | 0 |
| Nominal paths are contained in their tunnels | 100% | 100.0 |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 643.5816119050141 |
| All active fields and DB revision survive application close/reopen | True | true |

Saved evidence: `events/S1_INGEST_PLAN_RF_DB.jsonl`, `db/S1_INGEST_PLAN_RF_DB.sqlite3` and 4 PNG window grabs. All request endpoint clearances are logged; active start, goal and GCS clearances are in the report.

## S2_SWARM_16_DECONFLICTION

| Target | Expected | Measured |
| --- | --- | --- |
| All independently planted conflicts detected; at least 14 | 100%, >=14 | {"planted": 108, "detected": 108} |
| 16 drones and two crewed plans have a common active interval | 16+2 | {"drones": 16, "crewed": 2, "overlap_s": 58.82352900505066} |
| Planning and allocation per plan, max <=5 s and p95 <=3 s | max <=5, p95 <=3 | {"max_s": 0.6775679760030471, "p95_s": 0.6421944067515142} |
| Crewed records unchanged | True | true |
| Every measured planner/re-route call <=5 s | 5.0 | 0.6496762059978209 |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} |
| No conflicts reported on the independently clean approved set | 0 | 0 |
| Nominal paths are contained in their tunnels | 100% | 100.0 |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 643.5816119050141 |
| All active fields and DB revision survive application close/reopen | True | true |

Saved evidence: `events/S2_SWARM_16_DECONFLICTION.jsonl`, `db/S2_SWARM_16_DECONFLICTION.sqlite3` and 2 PNG window grabs. All request endpoint clearances are logged; active start, goal and GCS clearances are in the report.

## S3_LIVE_TRACK_MATCHING

| Target | Expected | Measured |
| --- | --- | --- |
| All eight known tracks match on first and subsequent reports | 100% | {"correct": 8, "total": 8} |
| Both unknown tracks match by K=5 without false association | 2/2 | 2 |
| Both ambiguous tracks abstain after K=5 | 2/2 | 2 |
| Twelve simultaneous independent UDP sockets; all sent positions received | 720 | 720 |
| No drift alerts on ten nominal tracks | 0 | 0 |
| Receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"max_s": 0.0074445240024942905, "p95_s": 0.004796262903983002} |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} |
| No conflicts reported on the independently clean approved set | 0 | 0 |
| Nominal paths are contained in their tunnels | 100% | 100.0 |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 12371.272454024585 |
| All active fields and DB revision survive application close/reopen | True | true |

Saved evidence: `events/S3_LIVE_TRACK_MATCHING.jsonl`, `db/S3_LIVE_TRACK_MATCHING.sqlite3` and 2 PNG window grabs. All request endpoint clearances are logged; active start, goal and GCS clearances are in the report.

## S4_CONFORMANCE_AND_PACKET_LOSS

| Target | Expected | Measured |
| --- | --- | --- |
| Nominal track remains conforming | 0 | 0 |
| LATERAL alert within 2 report intervals | 2 | 2 |
| VERTICAL alert within 2 report intervals | 2 | 2 |
| TEMPORAL alert within 2 report intervals | 2 | 2 |
| LATERAL alert within 3 report intervals | 3 | 3 |
| Seeded outgoing packet loss is exactly 10% | 0.1 | 0.1 |
| Receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"max_s": 0.0009918130017467774, "p95_s": 0.000654337003652472} |
| New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"alerts": 4, "max_s": 0.0007142419999581762, "p95_s": 0.0007092432490026112} |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} |
| No conflicts reported on the independently clean approved set | 0 | 0 |
| Nominal paths are contained in their tunnels | 100% | 100.0 |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 13533.461665375673 |
| All active fields and DB revision survive application close/reopen | True | true |

Saved evidence: `events/S4_CONFORMANCE_AND_PACKET_LOSS.jsonl`, `db/S4_CONFORMANCE_AND_PACKET_LOSS.sqlite3` and 2 PNG window grabs. All request endpoint clearances are logged; active start, goal and GCS clearances are in the report.

## S5_DYNAMIC_REROUTE

| Target | Expected | Measured |
| --- | --- | --- |
| Drift alert received before re-route | True | true |
| Lateral drift detected within two reports | 2 | 2 |
| Pop-up crewed conflict detected | True | true |
| Both accepted re-routes conform within two updates | 2/2 | 2 |
| Box-in returns no path within five seconds | no plan, <=5 s | {"status": "NO_PATH_WITHIN_GRID", "wall_s": 0.003431273995374795} |
| Operator hold/land decision recorded; no unsafe replacement | 1 | 1 |
| Two accepted old reservations remain as superseded history | 2 | 2 |
| Pop-up crewed plan unchanged | True | true |
| Both simulated drones fly the accepted route to within 15 m | 2/2 | 2 |
| Every measured planner/re-route call <=5 s | 5.0 | 0.004737734001537319 |
| Receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"max_s": 0.0013374929985729977, "p95_s": 0.0005274193983495933} |
| New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"alerts": 1, "max_s": 0.00047726500633871183, "p95_s": 0.00047726500633871183} |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} |
| No conflicts reported on the independently clean approved set | 0 | 0 |
| Nominal paths are contained in their tunnels | 100% | 100.0 |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 12717.275474241816 |
| All active fields and DB revision survive application close/reopen | True | true |

Saved evidence: `events/S5_DYNAMIC_REROUTE.jsonl`, `db/S5_DYNAMIC_REROUTE.sqlite3` and 4 PNG window grabs. All request endpoint clearances are logged; active start, goal and GCS clearances are in the report.

## S6_ARDUPILOT_SITL

| Target | Expected | Measured |
| --- | --- | --- |
| Every monitored SITL report matches the mapped ID | 100% | {"matched": 100, "reports": 100} |
| Every monitored nominal report conforms | 100% | {"conforming": 100, "reports": 100} |
| Lateral exit flagged within two received position reports | 2 | 2 |
| Re-route atomically supersedes original at next DB revision | 4 | 4 |
| Conformance returns within two reports | 2 | 1 |
| Known-ID match across nominal, deviation and recovery | 100% | {"matched": 420, "reports": 420} |
| Arrival within 15 m and campaign hard cap | <=15 m, <=300 s | {"distance_m": 14.343427805411704, "wall_s": 146.57003470500058} |
| External version and binary SHA-256 are recorded | version + SHA-256 | {"version": "4.7.2 (type 255)", "sha256": "caed35e4cb796ec06cac40b09566a18251771486b1cbac5e2bf16b7a5ed5045d"} |
| Every measured planner/re-route call <=5 s | 5.0 | 0.003137168998364359 |
| Receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"max_s": 0.0028935149966855533, "p95_s": 0.00042454399954294786} |
| New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"alerts": 1, "max_s": 0.0004178000017418526, "p95_s": 0.0004178000017418526} |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} |
| No conflicts reported on the independently clean approved set | 0 | 0 |
| Nominal paths are contained in their tunnels | 100% | 100.0 |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 15351.503524945825 |
| All active fields and DB revision survive application close/reopen | True | true |

Saved evidence: `events/S6_ARDUPILOT_SITL.jsonl`, `db/S6_ARDUPILOT_SITL.sqlite3` and 4 PNG window grabs. All request endpoint clearances are logged; active start, goal and GCS clearances are in the report.

## External simulator provenance

Observed AUTOPILOT_VERSION: 4.7.2 (type 255); commit prefix `fb773567`. Binary SHA-256: `caed35e4cb796ec06cac40b09566a18251771486b1cbac5e2bf16b7a5ed5045d`.
The provided binary's full commit was specified as fb773567896014da007bca58358704d4a0d8516f; the eight-byte version prefix is the independently observed portion. Local git-version.txt was unavailable. Harness version: pymavlink 2.4.50.
Ignored other message IDs: 600. Unparsed/invalid frames: 3. Neither is reported as packet loss.

## Regression and outstanding work

Whole-suite pytest: 107 passed in 28.04 s on the final source, including the campaign regression tests. Existing tests were not weakened or deleted. The three new tests exercise real S1/shortened S3 and unavailable/not-applicable SITL handling, without launching SITL in pytest.

Windows source and standalone campaigns have not run locally. The updated ci workflow must execute them, and Linux CI must run its required external-simulator campaign. A local PyInstaller attempt stops before module analysis because this host lacks libpython3.13.so.1.0. No package installation or network download was attempted locally. The fetch script passed shell syntax checking, but its download behaviour still needs CI network access.

Test operator: [NAME, TITLE]. Reviewer: [NAME, TITLE]. These personnel fields have not been supplied; the report author is Arpan Bom.

No readiness-level claim is made from this local run. The applicant must review the evidence, fill in personnel details and obtain the required platform results on the reviewed commit.

## Limits

- Simulation only; never flown. No physical aircraft, autopilot, radio or live air traffic control was exercised. Outdoor range testing and Range Control integration remain for later readiness work.
- Altitudes use a flat ground reference, with 750 m AMSL for SITL home. No terrain elevation, wind shear, terrain masking, multipath or antenna radiation patterns are modelled. Uniform surface wind and gust limits apply.
- RF uses ITU-R P.525 free-space screening, fixed 2 m GCS receivers and a 10 m near-field clamp; it is not a coverage prediction.
- Zones, crewed plans and METARs come from local files. The shipped Handbook issue ends on 29 October 2026 and needs rechecking before operational use. NOTAM overrides are manual; Flight Levels are unsupported.
- Loopback MAVLink UDP is unencrypted and unauthenticated; message signing is not verified. Local socket testing does not establish physical datalink performance.
- The spatial grid planner is bounded to 40000 expansions and a 9.5 s search deadline, not globally optimal. Dense intersecting traffic may require operator intervention.
- These tests are engineering evidence offered towards a readiness assessment; the assessment itself is the applicant's responsibility. Windows source and frozen results require execution on Windows and cannot be inferred from Linux results.
