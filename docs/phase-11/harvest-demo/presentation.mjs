export function command(value) { return value == null ? 'Not run' : (Math.abs(value) < .005 ? 0 : value).toFixed(2); }
export function present(run, frame) {
  const t = run.telemetry, forecast = frame.forecast;
  const sensor = !t.sensor.fresh || t.sensor.age_s > .2 ? 'Range stale' : t.sensor.valid_cells >= 5 ? 'Range usable' : 'Range unavailable';
  let outcome = 'Empty-start delivery target: 2.00 t.';
  if (run.playback.finished) {
    if (run.scenario_evaluation.criterion === 'accepted_refusal') outcome = run.scenario_evaluation.passed ? 'Accepted no-progress stop and ten-second hold. Delivered mass remains zero.' : 'Start-hold check failed. Inspect the trace.';
    else if (run.scenario_evaluation.criterion === 'stop') outcome = run.scenario_evaluation.passed ? 'Ten-second controlled hold completed. No delivery counted.' : 'Stop/hold check failed. Inspect the trace.';
    else outcome = run.scenario_evaluation.passed ? `Delivery complete: ${(run.outcome.delivered_kg/1000).toFixed(2)} t.` : `Run ended: ${run.outcome.reason}. Scenario did not pass.`;
  }
  const owner = t.owner === 'learned_linear_feedback' ? 'Fitted continuous feedback with conventional planning' : t.owner === 'conventional_initial_no_progress_hold' ? 'Conventional initial no-progress hold' : t.override ? 'Conventional stopping guard' : t.owner ? 'Conventional feedback and planning' : 'No command applied yet';
  return {mode:t.status.replaceAll('_',' '),owner,sensor,outcome,coverage:`${t.sensor.valid_cells}/25 cells valid`,age:`${t.sensor.age_s.toFixed(1)} s`,
    inputTime:t.status === 'ready' ? 'Sensor preview; no decision executed.' : `Input ${t.input_time_s.toFixed(1)} s / state ${frame.t_s.toFixed(1)} s`,override:t.override,
    forecastStatus:!forecast ? 'No decision forecast yet.' : !forecast.accepted ? 'Forecast withheld by the frozen uncertainty/validity gate.' : forecast.measured_error?.actual_interval_s < .099 ? `Nominal 0.1 s forecast compared with a ${forecast.measured_error.actual_interval_s.toFixed(2)} s terminal interval.` : `Compared forecast from ${forecast.produced_at_s.toFixed(1)} s, nominal horizon 0.1 s.`,
    positionError:forecast?.measured_error ? `${(forecast.measured_error.position_m*1000).toFixed(2)} mm` : 'Not measured',
    loadError:forecast?.measured_error ? `${forecast.measured_error.carried_kg.toFixed(2)} kg` : 'Not measured'};
}
