import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {trainingClock,trainingDuration,sampleTrial} from '../../js/training-trace.js';
const data=JSON.parse(readFileSync(new URL('../../data/training-demonstration.json',import.meta.url)));
test('the exact final clock settles on three successful work orders',()=>{
 const end=trainingDuration(data),a=trainingClock(data,end),b=trainingClock(data,end+20);
 assert.equal(a.complete,true);assert.equal(a.deliveredKg,2000);assert.equal(a.payloadKg,0);assert.equal(a.inflightKg,0);assert.equal(a.phase,10);assert.deepEqual(a,b);
});
test('every displayed interpolation conserves ore, including transfer in flight',()=>{
 for(const trial of data.trials)for(let t=0;t<trial.duration_s;t+=.031){const s=sampleTrial(trial,t);assert(Math.abs(s.sourceKg+s.payloadKg+s.deliveredKg+s.inflightKg-3000)<.01);assert(s.sourceKg>=0&&s.payloadKg>=0&&s.deliveredKg>=0&&s.inflightKg>=0);}
});
test('a new episode is explicit, never a moving teleport',()=>{
 let cursor=0;
 for(let i=0;i<data.trials.length-1;i++){
  cursor+=data.trials[i].duration_s/data.replay_speed;
  const reset=trainingClock(data,cursor+data.reset_seconds/2);assert(reset.reset>0);assert.equal(reset.index,i);assert.equal(reset.pose[3],0);
  cursor+=data.reset_seconds;assert.equal(trainingClock(data,cursor+.001).index,i+1);
 }
});
