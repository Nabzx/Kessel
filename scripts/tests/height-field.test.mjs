import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const src=await readFile(new URL('../../js/height-field.js',import.meta.url),'utf8');
const {heightField}=await import('data:text/javascript;base64,'+Buffer.from(src).toString('base64'));
test('height field preserves each physical cell, holes, footprint and bounded relief',()=>{
 for(const cells of [Array(64).fill(1),Array.from({length:64},(_,i)=>i%7===0?0:(i*13%31)/20),Array.from({length:64},(_,i)=>i===22?1:0)]){
  const result=heightField(cells);result.cellVolumes.forEach((v,i)=>assert.ok(Math.abs(v-cells[i]*.25)<1e-12));
  for(let i=0;i<result.positions.length;i+=3){assert.ok(result.positions[i]>=0&&result.positions[i]<=4);assert.ok(result.positions[i+2]>=-4&&result.positions[i+2]<=0);assert.ok(result.positions[i+1]>=0&&result.positions[i+1]<=Math.max(...cells)*result.maximumReliefFactor+1e-12);}
 }
});
test('non-physical negative and missing cells are rejected',()=>{assert.throws(()=>heightField([-1]));assert.throws(()=>heightField(Array(64).fill(NaN)));});
