# ADR-0073: Blocked-path observation and stopping

Status: Accepted for the maintainer's 27 November request to work through
blocked paths, robustness and world-model calibration, with regular merges.

## Observation boundary

Add an isolated `kessel_lab` clearance channel and supervisor. Preserve every
frozen training kernel, checkpoint, source capsule, evidence and runtime.
The channel is an idealised synthetic geometric sensor, not implemented lidar
or camera perception. Its producer may read scene geometry. The controller may
read only the packet and existing local observations, never environment state.
Do not call a privileged geometry query an observation-only learned detector.

Version four body-envelope clearance distances in metres (forward, rear, left,
right), timestamp, maximum sensing distance, validity and a declared frame.
Derive conservative component AABBs from the existing collision envelope.
Include obstacles and tunnel boundaries. Missing, invalid, out-of-order or stale
packets request stopping; malformed observations produce no command. No obstacle
avoidance, perception uncertainty or field safety claim follows.

The frozen bootstrap supervisor supplies conventional stopping/holding commands.
Use a separately named wrapper. Trigger on a forward/rear distance below
0.6 + 0.2*abs(speed) + speed**2/1.2 metres, or lateral distance below 0.3 m.
Preserve original range health and disclose both trigger types, proposals,
applied commands and stopped/held state. Hold phase/task memory during override.
A persistent blockage is a stop, never a delivery or simulator termination.

## Bounded practice pilot

Use consumed practice bases 19000/19001, three frozen checkpoint seeds 7/19/41.
For each base/seed run healthy, original blocked corridor, forward loaded
approach to a box, reverse loaded approach to a box, and stale clearance input.
Loaded cases are explicit fixtures, not empty-start deliveries. Forward/reverse
fixtures start at +/-0.8 m/s with 2,500 kg and +/-0.06 rad grades respectively.
Box gaps initially 1.2 m, within the declared stopping envelope. Healthy controls
must match the original neural trace exactly; no-box sensor faults stop safely.

Require detection by 0.1 s, speed <=0.08 m/s for three samples within 2.5 s,
stop path <=2 m, followed by ten seconds with max speed <=0.1 m/s, hold path
<=0.25 m and no collision. Do not change dynamics or limits to obtain a pass.
Record all 30 cases, observations, channel packets, proposals, overrides and
physical outcomes. Independently replay all applied actions and sensor packets.
Cap evaluation at 12,000 decisions, replay at 12,000, one CPU thread and 180
seconds total. Keep incomplete/failing evidence. No teacher or model updates.
This consumed-practice pilot grants no fresh qualification/runtime admission.

Use in-process contract/controller tests and a standard-library evidence
verifier in CI. No browser, desktop automation or listening service. Merge the
verified implementation and honest results before the next stage.
