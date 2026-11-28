import test from 'node:test';
import assert from 'node:assert/strict';
import {present} from '../../docs/phase-11/harvest-demo/presentation.mjs';

function sample() {return {telemetry:{status:'no_progress_hold',owner:'conventional_initial_no_progress_hold',override:true,input_time_s:13,sensor:{fresh:true,age_s:0,valid_cells:25}},playback:{finished:true},scenario_evaluation:{criterion:'accepted_refusal',passed:true},outcome:{delivered_kg:0}};}
test('accepted holds stay distinct from successful delivery',()=>{
  const text=present(sample(),{t_s:13});assert.match(text.outcome,/Delivered mass remains zero/);assert.match(text.owner,/Conventional/);
});
test('withheld and short-terminal forecasts retain their actual scope',()=>{
  const run=sample(),frame={t_s:5,forecast:{accepted:false,produced_at_s:4.9,measured_error:{position_m:.002,carried_kg:4,actual_interval_s:.02}}};
  assert.match(present(run,frame).forecastStatus,/withheld/);frame.forecast.accepted=true;
  assert.match(present(run,frame).forecastStatus,/0.02 s terminal/);assert.equal(present(run,frame).positionError,'2.00 mm');
});
