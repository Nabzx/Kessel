const modes = {ready:'Ready for a decision', neural:'Neural policy', stopping:'Stopping', holding:'Holding', recovering:'Recovering range'};
export function present(run, frame) {
  const t = run.telemetry;
  const sensor = !t.sensor.fresh || t.sensor.age_s > .2 ? 'Range stale' : t.sensor.usable ? 'Range complete' : 'Range incomplete';
  let outcome = 'Empty-start delivery target: 2.00 t.';
  if (run.playback.finished) {
    if (run.playback.end_reason === 'hold_window_passed') outcome = 'Ten-second stop/hold check met. No delivery counted.';
    else if (run.playback.end_reason === 'hold_window_failed') outcome = 'Stop/hold check failed. Inspect the executed trace.';
    else if (run.scenario_evaluation.passed) outcome = `Delivery complete: ${(run.outcome.delivered_kg/1000).toFixed(2)} t.`;
    else if (run.outcome.full_success) outcome = 'Material delivered, but the selected recovery scenario did not pass.';
    else outcome = `Run ended: ${run.outcome.reason}. Scenario did not pass.`;
  }
  return {mode:modes[t.status] || 'Unknown control state', sensor,
    owner:t.owner === 'conventional_supervisor' ? 'Conventional stopping supervisor' : t.owner === 'neural_policy' ? 'Neural continuous controls' : 'No command applied yet',
    coverage:`${t.sensor.valid_cells}/${t.sensor.total_cells} cells valid`, age:`${t.sensor.age_s.toFixed(1)} s`,
    inputTime:t.status === 'ready' ? 'Range preview; no decision executed.' : `Input at ${t.input_time_s.toFixed(1)} s / state at ${frame.t_s.toFixed(1)} s`,
    outcome, override:t.owner === 'conventional_supervisor'};
}
export function command(value) { return value == null ? 'Not run' : (Math.abs(value) < .005 ? 0 : value).toFixed(2); }
