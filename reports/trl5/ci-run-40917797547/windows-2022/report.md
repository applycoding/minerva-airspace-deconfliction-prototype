# MINERVA integrated scenario campaign

Simulation only; never flown.

All TRL 5 scenario targets met

Author: Arpan Bom. UTC: 2026-10-29T17:11:07.669520Z. Git: e8334478cc4afcb73539517215cff9c65c86cc4a.

| Scenario | Status | Wall seconds |
| --- | --- | --- |
| S1_INGEST_PLAN_RF_DB | PASS | 2.506 |
| S2_SWARM_16_DECONFLICTION | PASS | 5.523 |
| S3_LIVE_TRACK_MATCHING | PASS | 31.210 |
| S4_CONFORMANCE_AND_PACKET_LOSS | PASS | 45.695 |
| S5_DYNAMIC_REROUTE | PASS | 60.846 |
| S6_ARDUPILOT_SITL | NOT_APPLICABLE | 0.002 |

## S1_INGEST_PLAN_RF_DB



| Target | Expected | Measured | Pass |
| --- | --- | --- | --- |
| RF interference resolves by channel reassignment | RADIO_CHANNEL_SHIFT | "RADIO_CHANNEL_SHIFT" | True |
| No solution escalates to an operator | True | true | True |
| Zone, crewed, RF, gust and stale-weather checks and planner rejection | 100% | {"detected": 7, "planted": 7} | True |
| Crewed records unchanged | True | true | True |
| Four accepted requests | 4 | 4 | True |
| Every measured planner/re-route call <=5 s | 5.0 | 0.8830891000000065 | True |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} | True |
| No conflicts reported on the independently clean approved set | 0 | 0 | True |
| Nominal paths are contained in their tunnels | 100% | 100.0 | True |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 643.5816119050141 | True |
| All active fields and DB revision survive application close/reopen | True | true | True |

## S2_SWARM_16_DECONFLICTION



| Target | Expected | Measured | Pass |
| --- | --- | --- | --- |
| All independently planted conflicts detected; at least 14 | 100%, >=14 | {"planted": 108, "detected": 108} | True |
| 16 drones and two crewed plans have a common active interval | 16+2 | {"drones": 16, "crewed": 2, "overlap_s": 58.82352900505066} | True |
| Planning and allocation per plan, max <=5 s and p95 <=3 s | max <=5, p95 <=3 | {"max_s": 1.2367047000000184, "p95_s": 1.2281753249999383} | True |
| Crewed records unchanged | True | true | True |
| Every measured planner/re-route call <=5 s | 5.0 | 1.1922749000000294 | True |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} | True |
| No conflicts reported on the independently clean approved set | 0 | 0 | True |
| Nominal paths are contained in their tunnels | 100% | 100.0 | True |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 643.5816119050141 | True |
| All active fields and DB revision survive application close/reopen | True | true | True |

## S3_LIVE_TRACK_MATCHING



| Target | Expected | Measured | Pass |
| --- | --- | --- | --- |
| All eight known tracks match on first and subsequent reports | 100% | {"correct": 8, "total": 8} | True |
| Both unknown tracks match by K=5 without false association | 2/2 | 2 | True |
| Both ambiguous tracks abstain after K=5 | 2/2 | 2 | True |
| Twelve simultaneous independent UDP sockets; all sent positions received | 720 | 720 | True |
| No drift alerts on ten nominal tracks | 0 | 0 | True |
| Receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"max_s": 0.004912200000035227, "p95_s": 0.004471694999915598} | True |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} | True |
| No conflicts reported on the independently clean approved set | 0 | 0 | True |
| Nominal paths are contained in their tunnels | 100% | 100.0 | True |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 12371.272454024585 | True |
| All active fields and DB revision survive application close/reopen | True | true | True |

## S4_CONFORMANCE_AND_PACKET_LOSS



| Target | Expected | Measured | Pass |
| --- | --- | --- | --- |
| Nominal track remains conforming | 0 | 0 | True |
| LATERAL alert within 2 report intervals | 2 | 2 | True |
| VERTICAL alert within 2 report intervals | 2 | 2 | True |
| TEMPORAL alert within 2 report intervals | 2 | 2 | True |
| LATERAL alert within 3 report intervals | 3 | 3 | True |
| Seeded outgoing packet loss is exactly 10% | 0.1 | 0.1 | True |
| Receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"max_s": 0.0010938999998870713, "p95_s": 0.0009168999999928928} | True |
| New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"alerts": 4, "max_s": 0.0008660999999392516, "p95_s": 0.0008558999999650041} | True |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} | True |
| No conflicts reported on the independently clean approved set | 0 | 0 | True |
| Nominal paths are contained in their tunnels | 100% | 100.0 | True |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 13533.461665375673 | True |
| All active fields and DB revision survive application close/reopen | True | true | True |

## S5_DYNAMIC_REROUTE



| Target | Expected | Measured | Pass |
| --- | --- | --- | --- |
| Drift alert received before re-route | True | true | True |
| Lateral drift detected within two reports | 2 | 2 | True |
| Pop-up crewed conflict detected | True | true | True |
| Both accepted re-routes conform within two updates | 2/2 | 2 | True |
| Box-in returns no path within five seconds | no plan, <=5 s | {"status": "NO_PATH_WITHIN_GRID", "wall_s": 0.00597620000007737} | True |
| Operator hold/land decision recorded; no unsafe replacement | 1 | 1 | True |
| Two accepted old reservations remain as superseded history | 2 | 2 | True |
| Pop-up crewed plan unchanged | True | true | True |
| Both simulated drones fly the accepted route to within 15 m | 2/2 | 2 | True |
| Every measured planner/re-route call <=5 s | 5.0 | 0.00676700000008168 | True |
| Receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"max_s": 0.0007060000000365108, "p95_s": 0.0005652199999872209} | True |
| New-alert receive-to-GUI latency max <=1 s and p95 <=0.25 s | max <=1, p95 <=0.25 | {"alerts": 1, "max_s": 0.0006852999999864551, "p95_s": 0.0006852999999864551} | True |
| Independent flight-limit, zone, space/time and RF audit has no residual conflicts | 0 | {"residual": 0, "errors": {}} | True |
| No conflicts reported on the independently clean approved set | 0 | 0 | True |
| Nominal paths are contained in their tunnels | 100% | 100.0 | True |
| Every active start, goal and GCS is >=500 m outside every zone | 500.0 | 12717.275474241816 | True |
| All active fields and DB revision survive application close/reopen | True | true | True |

## S6_ARDUPILOT_SITL

External SITL campaign runs on Linux only

| Target | Expected | Measured | Pass |
| --- | --- | --- | --- |

## Limits

- Simulation only; never flown. No physical aircraft, autopilot, radio or live air traffic control was exercised. Outdoor range testing and Range Control integration remain for later readiness work.
- Altitudes use a flat ground reference, with 750 m AMSL for SITL home. No terrain elevation, wind shear, terrain masking, multipath or antenna radiation patterns are modelled. Uniform surface wind and gust limits apply.
- RF uses ITU-R P.525 free-space screening, fixed 2 m GCS receivers and a 10 m near-field clamp; it is not a coverage prediction.
- Zones, crewed plans and METARs come from local files. The shipped Handbook issue ends on 29 October 2026 and needs rechecking before operational use. NOTAM overrides are manual; Flight Levels are unsupported.
- Loopback MAVLink UDP is unencrypted and unauthenticated; message signing is not verified. Local socket testing does not establish physical datalink performance.
- The spatial grid planner is bounded to 40000 expansions and a 9.5 s search deadline, not globally optimal. Dense intersecting traffic may require operator intervention.
- These tests are engineering evidence offered towards a readiness assessment; the assessment itself is the applicant's responsibility. Windows source and frozen results require execution on Windows and cannot be inferred from Linux results.
