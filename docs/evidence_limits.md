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
