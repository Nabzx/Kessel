# ADR-0039: Stuck detection at actuator limits

Status: Accepted

Supersedes ADR-0036's immobility implementation detail. Other reference
dynamics and the source boundary remain unchanged.

## Evidence and decision

An adversarial fixture with negligible traction, a raised boom already at its
limit and commands `[1,0,1,0]` remained stationary while its stuck timer stayed
zero. The old condition inspected requested joint controls rather than physical
joint movement. A learned policy could therefore avoid the intended outcome by
holding a saturated actuator command.

Use actual joint displacement per physical step when deciding whether there
is meaningful actuator movement. Retain the existing drive-demand, low-speed
and elapsed-time conditions. A request that cannot move the joint does not
reset the timer. This is an explicit synthetic failure criterion, not a safety
certification. Add the fixture to regression and adversarial checks and rerun
the conventional and learned comparisons on the corrected source.

Refs: #226, #214. Recorded reproduction: zero speed, boom 1.1 rad and zero stuck
time after three decisions despite a 0.2-second configured stuck limit.
