import * as THREE from 'three';
import {loadExperiment, sampleEpisode} from '../../../js/recorded-data.js';
import {createReferenceLoader} from '../../../js/loader-stage.js';
import {authoredAsset} from '../../../js/authored-assets.js';
import {texture, box, lightRig} from '../../../js/scene-utils.js';
import {visibleBounds, boxCorners} from '../../../js/replay-framing.js';
import {heightField} from '../../../js/height-field.js';

const $ = id => document.getElementById(id);
const beats = {
  earth: {label:'Earth',title:'Physical AI for extreme environments.',copy:'The existing opening establishes the wider ambition before introducing the mining task.',image:'earth.jpg',source:'Existing concept walkthrough',method:'Current Earth opening. This screenshot is presentation context, not measured machine data.'},
  environments: {label:'Environments',title:'Start underground.',copy:'The current route introduces environment selection before the task. Other environments remain future directions.',image:'environments.jpg',source:'Existing concept walkthrough',method:'Current environment selector. Only the opening differs between these two proposed routes.'},
  surface: {label:'Surface',title:'Below the surface.',copy:'The current surface chapter supplies a sense of place. Its site and vehicle motion are authored.',image:'surface.jpg',source:'Authored surface illustration',method:'Current local surface film, captured as a still. It is not mine survey evidence or observed operations.'},
  task: {label:'The task',title:'One loader. One job.',copy:'Move at least two tonnes from the pile to the receiver. A conventional controller completes this recorded synthetic cycle.',source:'Recorded synthetic · conventional controller',method:'The first declared reference episode, including its actual actions and material ledger. This successful cycle is not a learned policy.'},
  observe: {label:'Observe',title:'Observe the pile.',copy:'The inputs are nearby pile heights, machine pose and payload. The points show recorded height samples, not an obstacle map.',source:'Same reference recording · local height samples',method:'The 5 × 5 local height crop and validity mask are attached to the recorded bucket frame. Missing measurements remain masked. No camera or LiDAR reconstruction is implied.'},
  predict: {label:'Predict',title:'Predict the outcome.',copy:'A learned world model forecasts the next state for this action. Compare it with the reference simulator’s actual future.',source:'Same reference recording · raw learned forecast',method:'The first scoop-phase record with a retained four-decision forecast. Actions, prediction and future reference state share this exact anchor. No missing forecasts are fabricated. Spread is not confidence.'},
  learn: {label:'Learn',title:'Learn the task.',copy:'Reinforcement learning trains the policy that chooses actions. This run picks up material, then hits a wall. No delivery.',source:'New recording · learned policy · seed 7',method:'First declared curriculum-follow-up episode. Its real failure is retained. The earlier successful controller and this learned policy are different runs, not before/after checkpoints of one training sequence.'},
  retrofit: {label:'Retrofit',title:'Run it onboard.',copy:'The proposed retrofit connects sensors, local compute and a machine interface. The sensing–policy–action loop is intended to run locally.',source:'Proposed architecture · no deployed kit shown',method:'Architecture explanation alongside the same reference machine illustration. This study does not validate hardware, mounting, edge latency or real-machine control.'},
};
const core = ['task','observe','predict','learn','retrofit'];
let route='mine', index=0, lens='job', elapsed=0, playing=false, horizon=4, loaded=false;
let bundle, learnedBundle, episode, loader, envelope, source, receiver, observationDots, fit, anchor;
const walls=[];
const scene=new THREE.Scene();scene.background=new THREE.Color('#050a0c');
const camera=new THREE.PerspectiveCamera(42,innerWidth/innerHeight,.1,200);
const renderer=new THREE.WebGLRenderer({canvas:$('world'),antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
const root=new THREE.Group();scene.add(root);lightRig(root,22,'mine');
const frames=[];
const schedule=()=>route==='context'?['earth','environments','surface',...core]:core;
const current=()=>schedule()[index];
const metric=v=>`${(v/1000).toFixed(2)} t`;
function poseTimes(ep){return ep.records.flatMap((row,i)=>i+1<ep.records.length?[row.t_s,(row.t_s+ep.records[i+1].t_s)/2]:[row.t_s]);}
function surface(map,colour){
  const mesh=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshStandardMaterial({map,color:colour,roughness:1}));root.add(mesh);mesh.receiveShadow=mesh.castShadow=true;
  return (cells,x,y,dx=.5,dy=.5)=>{const field=heightField(cells,8,8,dx,dy);mesh.visible=field.volume>1e-12;mesh.geometry.dispose();mesh.geometry=new THREE.BufferGeometry();mesh.geometry.setAttribute('position',new THREE.Float32BufferAttribute(field.positions,3));const uv=[];for(let i=0;i<field.positions.length;i+=3)uv.push(field.positions[i],-field.positions[i+2]);mesh.geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));mesh.geometry.computeVertexNormals();mesh.geometry.computeBoundingSphere();mesh.position.set(x,.008,-y);return field;};
}
function taskEnvelope(ep){
  const bounds=new THREE.Box3(),scratch=new THREE.Box3(),s=ep.records[0].state;
  for(const time of poseTimes(ep)){const p=sampleEpisode(ep,time);loader.apply(p.pose,p.wheelAngles,p.frame.state[7]);bounds.union(visibleBounds(loader.root,scratch));}
  bounds.expandByPoint(new THREE.Vector3(s[79],0,-s[80]-4));bounds.expandByPoint(new THREE.Vector3(s[79]+4,Math.max(2.4,...s.slice(15,79)),-s[80]));
  bounds.expandByPoint(new THREE.Vector3(s[88]-s[90],0,-s[89]-s[91]));bounds.expandByPoint(new THREE.Vector3(s[88]+s[90],2.4,-s[89]+s[91]));
  return bounds.expandByScalar(.2);
}
function safeArea(){
  const panel=$('story').getBoundingClientRect(),controls=$('view-controls').getBoundingClientRect();
  return innerWidth<=700?{left:20,right:innerWidth-20,top:88,bottom:panel.top-16}:{left:current()==='predict'?316:28,right:panel.left-28,top:102,bottom:controls.top-18};
}
function refit(){
  if(!loaded)return;
  renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;
  const safe=safeArea(),bounds=envelope.clone();
  if(lens==='contact'){
    bounds.makeEmpty();const s=episode.records[0].state;
    bounds.expandByPoint(new THREE.Vector3(s[79]-4,0,-s[80]-4));bounds.expandByPoint(new THREE.Vector3(s[79]+4,2.8,-s[80]));
  }
  const centre=bounds.getCenter(new THREE.Vector3()),direction=new THREE.Vector3(21,20.5,28).normalize(),corners=boxCorners(bounds);
  camera.setViewOffset(innerWidth,innerHeight,innerWidth/2-(safe.left+safe.right)/2,innerHeight/2-(safe.top+safe.bottom)/2,innerWidth,innerHeight);
  function project(distance){camera.position.copy(centre).addScaledVector(direction,distance);camera.lookAt(centre);camera.updateMatrixWorld(true);camera.updateProjectionMatrix();const p=corners.map(v=>screen(v));return {left:Math.min(...p.map(v=>v.x)),right:Math.max(...p.map(v=>v.x)),top:Math.min(...p.map(v=>v.y)),bottom:Math.max(...p.map(v=>v.y))};}
  let low=3,high=180;
  for(let i=0;i<36;i++){const mid=(low+high)/2,p=project(mid);if(p.left>=safe.left&&p.right<=safe.right&&p.top>=safe.top&&p.bottom<=safe.bottom)high=mid;else low=mid;}
  fit={safe,projected:project(high),distance:high,bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()}};
  $('detail-note').textContent=lens==='contact'?'Detail view may exclude the receiver.':'';
  document.querySelectorAll('[data-lens]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.lens===lens)));
  draw();
}
function screen(point){const p=point.clone().project(camera);return {x:(p.x+1)*innerWidth/2,y:(1-p.y)*innerHeight/2};}
function label(id,point){const p=screen(point),s=fit.safe;$(id).hidden=p.x<s.left+30||p.x>s.right-30||p.y<s.top||p.y>s.bottom;$(id).style.left=`${p.x}px`;$(id).style.top=`${p.y}px`;}
function forecast(frame){
  const p=frame.predictions.find(p=>p.horizon_decisions===horizon&&p.prediction);
  if(!p){$('forecast-readout').textContent='No retained forecast at this horizon.';return;}
  const actual=episode.records[p.reference_index].state,origin=frame.state;
  const extent=Math.max(.02,...[p.prediction,actual].flatMap(s=>[Math.abs(s[0]-origin[0]),Math.abs(s[1]-origin[1])]))*1.2;
  const xy=s=>[120+(s[0]-origin[0])*90/extent,63-(s[1]-origin[1])*45/extent];
  const [x,y]=xy(actual),[px,py]=xy(p.prediction);$('actual-dot').setAttribute('cx',x);$('actual-dot').setAttribute('cy',y);$('predicted-dot').setAttribute('d',`M${px} ${py-6}l6 6 -6 6 -6 -6Z`);
  const error=Math.hypot(p.prediction[0]-actual[0],p.prediction[1]-actual[1]);
  const invalid=Object.entries(p.violations).some(([k,v])=>k==='mass_error_kg'?Math.abs(v)>1:!!v);
  $('forecast-readout').textContent=`Magnified rear-axle displacement · axis ±${extent.toFixed(3)} m. Position error ${(error*1000).toFixed(1)} mm. Raw forecast${invalid?' · physical checks failed':''}.`;
}
function draw(){
  if(!loaded)return;
  const sampled=sampleEpisode(episode,elapsed),r=sampled.frame,s=r.state;
  loader.apply(sampled.pose,sampled.wheelAngles,s[7]);
  walls[0].position.z=-s[86]-.25;walls[1].position.z=s[86]+.2;
  source(s.slice(15,79),s[79],s[80]);
  const weights=Array.from({length:64},(_,k)=>Math.exp(-((k%8-3.5)**2+(Math.floor(k/8)-3.5)**2)/5)),sum=weights.reduce((a,b)=>a+b,0);
  receiver(weights.map(w=>w*s[8]/(s[81]*(s[90]*s[91]/16)*sum)),s[88]-s[90],s[89]-s[91],s[90]/4,s[91]/4);
  const heading=s[2]+s[4],mx=s[0]+1.8*Math.cos(s[2])+(1.6+1.2*Math.cos(s[5]))*Math.cos(heading),my=s[1]+1.8*Math.sin(s[2])+(1.6+1.2*Math.cos(s[5]))*Math.sin(heading),dummy=new THREE.Object3D();
  for(let k=0;k<25;k++){const a=(Math.floor(k/5)-1)*.75,b=(k%5-2)*.75;dummy.position.set(mx+a*Math.cos(heading)-b*Math.sin(heading),r.observation[15+k]+.06,-(my+a*Math.sin(heading)+b*Math.cos(heading)));dummy.scale.setScalar(r.observation[40+k]?1:0);dummy.updateMatrix();observationDots.setMatrixAt(k,dummy.matrix);}
  observationDots.instanceMatrix.needsUpdate=true;observationDots.visible=$('observations').checked;
  $('payload').textContent=metric(s[7]);$('delivered').textContent=metric(s[8]);$('clock').textContent=`${elapsed.toFixed(1)} s`;$('seek').value=elapsed;
  $('action-readout').hidden=!$('actions').checked;$('action-readout').textContent=r.action?['Drive','Steer','Boom','Bucket'].map((n,i)=>`${n} ${r.action[i].toFixed(2)}`).join(' / '):'Terminal record: no next action';
  if(current()==='predict')forecast(r);
  if(fit){label('pile-label',new THREE.Vector3(s[79]+2,1.8,-s[80]-2));label('receiver-label',new THREE.Vector3(s[88],1.5,-s[89]));}
  renderer.render(scene,camera);
}
function selectStep(n){
  if(!loaded)return;
  index=Math.max(0,Math.min(schedule().length-1,n));playing=false;lens='job';const key=current(),beat=beats[key];
  episode=key==='learn'?learnedBundle.episodes[0]:bundle.episodes[0];envelope=taskEnvelope(episode);
  elapsed=0;
  if(key==='observe')elapsed=episode.records.find(r=>r.phase==='Scoop'&&r.state[7]>0)?.t_s||0;
  if(key==='predict'){
    anchor=episode.records.find(r=>r.phase==='Scoop'&&r.predictions.some(p=>p.horizon_decisions===4&&p.prediction));elapsed=anchor.t_s;horizon=4;$('horizon').value='4';
    for(const option of $('horizon').options)option.disabled=!anchor.predictions.some(p=>p.horizon_decisions===Number(option.value)&&p.prediction);
  }
  if(key==='learn')elapsed=episode.records.at(-1).t_s;
  $('story-title').textContent=beat.title;$('story-copy').textContent=beat.copy;$('source').textContent=beat.source;$('step-count').textContent=`${index+1} / ${schedule().length} · ${beat.label}`;
  $('method').textContent=`${beat.method}\n\n${beat.image?'Captured from the current walkthrough.':`Run ${key==='learn'?learnedBundle.run_id:bundle.run_id}\nEpisode ${episode.name}\n${episode.policy?`Policy ${episode.policy.checkpoint_sha256}`:`Controller ${bundle.agent.configuration_sha256}`}\nRecorded outcome: ${episode.outcome}.`}`;
  $('context-frame').hidden=!beat.image;if(beat.image)$('context-frame').src=`docs/phase-11/narrative-study/evidence/${beat.image}`;
  document.body.dataset.context=String(!!beat.image);$('metrics').hidden=!!beat.image||key==='retrofit';$('forecast-inset').hidden=key!=='predict';$('kit-flow').hidden=key!=='retrofit';$('horizon-label').hidden=key!=='predict';
  $('observations').checked=key==='observe';$('actions').checked=key==='predict';$('seek').max=episode.records.at(-1).t_s;
  $('seek').disabled=$('play').disabled=key==='predict'||key==='retrofit';$('previous').disabled=index===0;$('next').textContent=index===schedule().length-1?'Restart story':'Next';$('play').textContent='Play recording';
  $('steps').replaceChildren(...schedule().map((id,i)=>{const b=document.createElement('button');b.textContent=beats[id].label;b.setAttribute('aria-current',i===index?'step':'false');b.setAttribute('aria-pressed',String(i===index));b.onclick=()=>selectStep(i);return b;}));
  $('route-duration').textContent=route==='mine'?'~60 s narrative target':'~90 s narrative target';
  refit();
}
async function start(){
  try{
    $('error').hidden=$('retry').hidden=true;
    const config=await fetch('data/experience.json').then(r=>{if(!r.ok)throw Error('Scene configuration unavailable');return r.json();});
    [bundle,learnedBundle]=await Promise.all([loadExperiment(undefined,fetch,'reference-cycle-v1'),loadExperiment(undefined,fetch,'curriculum-followup-v1')]);
    const [ore,floor,model,authored]=await Promise.all([texture(config.assets.ore),texture(config.assets.floor,8),fetch(config.assets.loader).then(r=>r.json()),authoredAsset(config.visuals.authored.reference_loader)]);
    loader=createReferenceLoader(model,ore,authored);root.add(loader.root);source=surface(ore,0xb1a08a);receiver=surface(ore,0xa99c86);
    const ground=new THREE.Mesh(new THREE.PlaneGeometry(34,12),new THREE.MeshStandardMaterial({map:floor,color:0x67736d,roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.set(3.5,-.012,0);ground.receiveShadow=true;root.add(ground);
    const concrete=new THREE.MeshStandardMaterial({color:0x47514c,roughness:1});walls.push(box([29,1,.5],[3.5,.5,0],concrete,root),box([29,.25,.4],[3.5,.125,0],concrete,root));
    observationDots=new THREE.InstancedMesh(new THREE.SphereGeometry(.09,8,6),new THREE.MeshBasicMaterial({color:0x9cd6bc,depthTest:false}),25);observationDots.renderOrder=2;observationDots.frustumCulled=false;root.add(observationDots);
    const s=bundle.episodes[0].records[0].state,steel=new THREE.MeshStandardMaterial({color:0x596560,roughness:.7,metalness:.5});
    for(const side of [-1,1])box([s[90]*2,.5,.12],[s[88],.25,-s[89]+side*s[91]],steel,root);
    box([.12,.5,s[91]*2],[s[88]+s[90],.25,-s[89]],steel,root);
    loaded=true;selectStep(0);document.body.dataset.ready='true';
  }catch(error){$('story-title').textContent='The record could not load.';$('story-copy').textContent='Check the local server and retry. The study needs the existing assets and experiment files.';$('error').textContent=error.message;$('error').hidden=$('retry').hidden=false;}
}
document.querySelectorAll('[data-route]').forEach(b=>b.onclick=()=>{route=b.dataset.route;document.querySelectorAll('[data-route]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));selectStep(0);});
document.querySelectorAll('[data-lens]').forEach(b=>b.onclick=()=>{lens=b.dataset.lens;refit();});
$('previous').onclick=()=>selectStep(index-1);$('next').onclick=()=>selectStep(index===schedule().length-1?0:index+1);
$('play').onclick=()=>{if(elapsed>=episode.records.at(-1).t_s)elapsed=0;playing=!playing;$('play').textContent=playing?'Pause recording':'Play recording';};
$('seek').oninput=()=>{elapsed=Number($('seek').value);playing=false;$('play').textContent='Play recording';draw();};
for(const id of ['observations','actions'])$(id).onchange=draw;
$('horizon').onchange=()=>{horizon=Number($('horizon').value);draw();};$('retry').onclick=()=>location.reload();
addEventListener('resize',refit);new ResizeObserver(()=>{if(loaded)refit();}).observe($('story'));
let last=performance.now();
function frame(now){const raw=(now-last)/1000,dt=Math.min(.1,raw);last=now;frames.push(raw);if(frames.length>180)frames.shift();if(playing&&loaded){elapsed=Math.min(episode.records.at(-1).t_s,elapsed+dt);if(elapsed===episode.records.at(-1).t_s){playing=false;$('play').textContent='Play recording';}draw();}requestAnimationFrame(frame);}
requestAnimationFrame(frame);start();
window.narrativeStudy={step:id=>selectStep(schedule().indexOf(id)),diagnostics:()=>({loaded,route,step:current(),lens,elapsed,playing,fit,source:current()==='learn'?learnedBundle?.run_id:bundle?.run_id,episode:episode?.name,frameIndex:episode?sampleEpisode(episode,elapsed).index:null,geometrySourceMode:'recorded_synthetic',viewSourceMode:beats[current()].image?'authored_context':current()==='retrofit'?'proposed_architecture':'recorded_synthetic',authoredOutcome:false,pose:episode?sampleEpisode(episode,elapsed).pose:null,meanFps:frames.length/frames.reduce((a,b)=>a+b,0),gpu:renderer.getContext().getParameter(renderer.getContext().getExtension('WEBGL_debug_renderer_info')?.UNMASKED_RENDERER_WEBGL||renderer.getContext().RENDERER)}),auditFrames(){
  const projections=[];for(const time of poseTimes(episode)){const p=sampleEpisode(episode,time);loader.apply(p.pose,p.wheelAngles,p.frame.state[7]);const b=visibleBounds(loader.root),points=boxCorners(b).map(screen);projections.push({time,left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),top:Math.min(...points.map(p=>p.y)),bottom:Math.max(...points.map(p=>p.y))});}draw();return projections;
}};
