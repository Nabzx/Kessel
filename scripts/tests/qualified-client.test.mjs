import test from 'node:test';
import assert from 'node:assert/strict';
import {SimulationClient} from '../../docs/phase-11/qualified-demo/client.mjs';
import {present,command} from '../../docs/phase-11/qualified-demo/presentation.mjs';

const state=(decisions=0,epoch=1,running=false,extra={})=>({run_id:'a',outcome:{decisions},frames:[{t_s:decisions*.1}],playback:{epoch,running,finished:false},...extra});
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};

test('pause rejects late automatic responses without moving the displayed state backwards',async()=>{
  const step=deferred(),calls=[];
  const client=new SimulationClient(async(path,body)=>{calls.push({path,body});return path==='/api/step'?step.promise:state(1,3);});
  client.state=state(0,2,true);client.desiredRunning=true;
  const pending=client.step(1,true);assert.equal(client.canStep,false);
  await client.pause();assert.equal(client.playing,false);
  step.resolve(state(1,2,true));await pending;
  assert.equal(client.state.playback.epoch,3);assert.equal(client.state.playback.running,false);
  assert.equal(client.canStep,true);assert.equal(calls[0].body.playback_epoch,2);
});

test('a rejected automatic request cancelled by pause does not become a connection error',async()=>{
  const step=deferred();const client=new SimulationClient(path=>path==='/api/step'?step.promise:Promise.resolve(state(0,3)));
  client.state=state(0,2,true);client.desiredRunning=true;
  const pending=client.step(1,true);await client.pause();step.reject(Error('stale playback request'));assert.equal(await pending,null);
  assert.equal(client.canStep,true);
});

test('reset invalidates outstanding steps and leaves the new run paused',async()=>{
  const step=deferred();const client=new SimulationClient(path=>path==='/api/step'?step.promise:Promise.resolve(state(0,4,false,{run_id:'b'})));
  client.state=state(0,2,true);client.desiredRunning=true;const pending=client.step(1,true);
  await client.reset({seed:19000});step.resolve(state(1,2,true));await pending;
  assert.equal(client.state.run_id,'b');assert.equal(client.state.outcome.decisions,0);assert.equal(client.playing,false);assert.equal(client.canStep,true);
});

test('manual steps require confirmed pause, use the current counter and cannot overlap',async()=>{
  const response=deferred();let body;
  const client=new SimulationClient(async(path,value)=>{body=value;return response.promise;});client.state=state(4,3,true);
  await assert.rejects(client.step(),/Pause/);client.state.playback.running=false;
  const pending=client.step(2);assert.equal(await client.step(),null);assert.deepEqual(body,{run_id:'a',after:4,steps:2,automatic:false,playback_epoch:3});
  response.resolve(state(6,3));await pending;assert.equal(client.state.outcome.decisions,6);
});

test('export confirms pause before reading the trace and drops exports replaced by reset',async()=>{
  const calls=[],exported=deferred();
  const client=new SimulationClient(async path=>{calls.push(path);if(path==='/api/export')return exported.promise;return path==='/api/reset'?state(0,5,false,{run_id:'b'}):state(3,4);});
  client.state=state(3,3,true);client.desiredRunning=true;
  const pending=client.exportTrace();await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,['/api/pause','/api/export']);assert.equal(client.playing,false);
  await client.reset({seed:19000});exported.resolve({run_id:'a'});assert.equal(await pending,null);
});

test('a hold ending disables playback even when the environment is not terminal',async()=>{
  const client=new SimulationClient(async()=>state(100,3,false,{outcome:{decisions:100,done:false},playback:{epoch:3,running:false,finished:true,end_reason:'hold_window_passed'}}));
  client.state=state(99,2,true);client.desiredRunning=true;await client.step(1,true);
  assert.equal(client.playing,false);assert.equal(client.canStep,false);await assert.rejects(client.play(),/finished/);assert.equal(await client.step(),null);
});

test('presentation distinguishes consumed sensor input, controller ownership and actual outcomes',()=>{
  const run=state();run.telemetry={status:'ready',owner:null,input_time_s:1,sensor:{fresh:true,usable:true,age_s:0,valid_cells:25,total_cells:25}};
  assert.equal(present(run,{t_s:1.1}).inputTime,'Range preview; no decision executed.');
  for(const [status,label] of Object.entries({neural:'Neural policy',stopping:'Stopping',holding:'Holding',recovering:'Recovering range'})){
    run.telemetry.status=status;run.telemetry.owner=status==='neural'?'neural_policy':'conventional_supervisor';
    const p=present(run,{t_s:1.1});assert.equal(p.mode,label);assert.equal(p.override,status!=='neural');assert.equal(p.inputTime,'Input at 1.0 s / state at 1.1 s');
  }
  run.telemetry.sensor={fresh:true,usable:false,age_s:0,valid_cells:15,total_cells:25};assert.equal(present(run,{t_s:1.1}).sensor,'Range incomplete');
  run.telemetry.sensor.fresh=false;assert.equal(present(run,{t_s:1.1}).sensor,'Range stale');
  run.playback.finished=true;run.playback.end_reason='hold_window_passed';assert.match(present(run,{t_s:1.1}).outcome,/No delivery counted/);
  run.playback.end_reason='hold_window_failed';assert.match(present(run,{t_s:1.1}).outcome,/failed/);
  run.playback.end_reason='environment_terminal';run.scenario_evaluation={passed:false};run.outcome.full_success=true;
  assert.match(present(run,{t_s:1.1}).outcome,/recovery scenario did not pass/);
  run.scenario_evaluation.passed=true;run.outcome.delivered_kg=2000;assert.equal(present(run,{t_s:1.1}).outcome,'Delivery complete: 2.00 t.');
  assert.equal(command(null),'Not run');assert.equal(command(-.0001),'0.00');assert.equal(command(.123),'0.12');
});
