import test from 'node:test';
import assert from 'node:assert/strict';
import {ghostForecast,present} from '../../docs/phase-11/sensor-demo/presentation.mjs';

const forecast={source:'sensor_observation_residual_ensemble',input_usable:true,accepted:false,render_pose:[0,0,0,0,0,0,0],observation:{proprio:Array(15).fill(0)},measured_error:null};
const run={telemetry:{status:'ready',sensor:{fresh:true,age_s:0,valid_cells:25}},playback:{finished:false}};
test('failed model needs explicit inspection and usable inputs for a ghost',()=>{
  assert.equal(ghostForecast(forecast),null);
  assert.deepEqual(ghostForecast(forecast,true).pose,forecast.render_pose);
  assert.equal(ghostForecast({...forecast,input_usable:false},true),null);
  assert.equal(ghostForecast({...forecast,source:'privileged_hybrid_shadow'},true),null);
});
test('failed gate and partial interval never become a qualified sensor error',()=>{
  const result=present(run,{forecast});
  assert.match(result.forecastStatus,/failed fresh qualification/);
  assert.match(result.forecastStatus,/outside the 0.1 s/);
  assert.equal(result.positionError,'Not measured');
  assert.equal(result.loadError,'Not measured');
});
