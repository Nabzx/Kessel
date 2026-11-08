import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
const source = await readFile(new URL("../../js/recorded-data.js", import.meta.url), "utf8");
const { validateBundle, loadExperiment, ReplayClock, sampleEpisode } = await import("data:text/javascript;base64," + Buffer.from(source).toString("base64"));
const bytes = await readFile(new URL("../../data/experiments/loader-v1.json", import.meta.url));
const bundle = JSON.parse(bytes), catalogue = JSON.parse(await readFile(new URL("../../data/experiments/index.json", import.meta.url)));

test("recorded bundle validates actual rewards and missing forecasts", () => {
  assert.equal(validateBundle(bundle).source_mode, "recorded_synthetic");
  const corrupted = structuredClone(bundle);
  corrupted.episodes[0].records[0].predictions[0].residual.position_m += 0.1;
  assert.throws(() => validateBundle(corrupted), /residual differs/);
  const missing = structuredClone(bundle);
  missing.episodes[0].records[0].state[0] = Infinity;
  assert.throws(() => validateBundle(missing), /Non-finite/);
});

test("single playback clock preserves boundaries, pause, pace and reduced motion", () => {
  const clock = new ReplayClock(bundle, true);
  assert.equal(clock.update(20).time, 0);
  clock.toggle(); clock.update(2); assert.equal(clock.state().index, 0);
  clock.setPace(2);clock.update(1); assert.equal(clock.state().index, 1);
  clock.checkpoint(2);assert.equal(clock.state().paused, true);
  clock.seek(bundle.episodes[2].records.at(-1).t_s);assert.equal(clock.state().complete, true);
  const state = sampleEpisode(clock.state().episode, clock.state().time);
  assert.equal(state.frame.action, null);assert.equal(state.frame.events[0], bundle.episodes[2].outcome);
  clock.replay();clock.toggle();clock.update(100);assert.equal(clock.state().index, 2);assert.equal(clock.state().paused, true);
});

test("visual interpolation cannot invent decisions, material or erase terminal records", () => {
  const ep = bundle.episodes[0], a = ep.records[0], b = ep.records[1];
  const sampled = sampleEpisode(ep, (a.t_s + b.t_s) / 2);
  assert.equal(sampled.frame, a);assert.equal(sampled.frame.action, a.action);
  assert.equal(sampled.frame.state[7], a.state[7]);
  assert.ok(Math.abs(sampled.pose[0] - (a.state[0] + b.state[0]) / 2) < 1e-10);
});

test("load checks hashes and cannot silently fall back when a bundle is invalid", async () => {
  const fetcher = async (url) => url.endsWith("index.json") ? new Response(JSON.stringify(catalogue)) : new Response(bytes);
  assert.equal((await loadExperiment(undefined, fetcher)).run_id, bundle.run_id);
  const broken = async (url) => url.endsWith("index.json") ? new Response(JSON.stringify(catalogue)) : new Response(Buffer.alloc(bytes.length));
  await assert.rejects(loadExperiment(undefined, broken), /checksum differs/);
  await assert.rejects(loadExperiment(undefined, async () => new Response("", {status:404})), /catalogue unavailable/);
});

const reference=JSON.parse(await readFile(new URL('../../data/experiments/reference-v1.json',import.meta.url)));
test('reference source carries controller identity and every post-action event boundary',()=>{
 validateBundle(reference);assert.equal(reference.agent.learned,false);
 for(const ep of reference.episodes){assert.equal(ep.policy,null);for(const event of ep.timeline)assert.ok(Math.abs(ep.records[event.index].t_s-event.t_s)<1e-9);}
 const bad=structuredClone(reference);bad.episodes[0].policy={checkpoint_sha256:'a'.repeat(64)};assert.throws(()=>validateBundle(bad),/Reference presented as policy/);
});
test('variable episode clock preserves pause, event seek, pace and a finite terminal hold',()=>{
 const clock=new ReplayClock(reference,true),duration=reference.episodes[0].records.at(-1).t_s;
 clock.replay(true);clock.toggle();clock.update(clock.activeSeconds(0)+.01);assert.equal(clock.state().holding,true);assert.equal(clock.state().time,duration);
 clock.update(.65);assert.equal(clock.state().index,1);clock.checkpoint(0);
 const event=reference.episodes[0].timeline.find(e=>e.kind==='Deposition');clock.seek(event.t_s);const sampled=sampleEpisode(clock.state().episode,clock.state().time);
 assert.ok(sampled.frame.state[8]>0);assert.equal(clock.state().paused,true);
 clock.setPace(2);clock.toggle();clock.update(100);assert.equal(clock.state().complete,true);assert.equal(clock.state().index,0);
 assert.throws(()=>clock.seek(NaN),/Invalid seek/);assert.throws(()=>clock.update(-1),/Invalid playback/);
});

 test('guided reference stops on its complete cycle and source speed stays constant',()=>{
 const c=new ReplayClock(reference,false);c.update(100);assert.equal(c.state().index,0);assert.equal(c.state().complete,true);assert.ok(c.state().episode.metrics.delivered_kg>2000);
 for(let i=0;i<reference.episodes.length;i++){c.checkpoint(i);assert.ok(Math.abs(c.state().acceleration-3)<1e-8);}
 });

test('rounded browser seeks retain terminal frames and reference replay retains the selected case',()=>{
 const c=new ReplayClock(reference,true);c.checkpoint(2);c.replay();assert.equal(c.state().index,2);
 c.seek(Number(reference.episodes[2].records.at(-1).t_s.toFixed(3)));assert.equal(c.state().complete,true);
 const policy=new ReplayClock(bundle,true);for(let i=0;i<bundle.episodes.length;i++){policy.checkpoint(i);assert.ok(Math.abs(policy.state().acceleration-4)<1e-8);policy.seek(Number(bundle.episodes[i].records.at(-1).t_s.toFixed(3)));assert.equal(policy.state().complete,true);}
});
