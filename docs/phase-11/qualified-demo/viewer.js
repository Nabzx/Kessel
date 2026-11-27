import * as THREE from 'three';
import {createReferenceLoader} from '../../../js/loader-stage.js';
import {authoredAsset} from '../../../js/authored-assets.js';
import {texture,box,lightRig} from '../../../js/scene-utils.js';
import {heightField} from '../../../js/height-field.js';
import {SimulationClient} from './client.mjs';
import {present,command} from './presentation.mjs';
const $=id=>document.getElementById(id);
const client=new SimulationClient(api,draw);
let loader,pile,receiver,frame,boundRun=null,info=null,exporting=false;
const scene=new THREE.Scene();scene.background=new THREE.Color('#050a0c');
const root=new THREE.Group();scene.add(root);lightRig(root,22,'mine');
const renderer=new THREE.WebGLRenderer({canvas:$('world'),antialias:true,powerPreference:'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
const camera=new THREE.PerspectiveCamera(42,1,.1,200),boundaries=new THREE.Group();root.add(boundaries);
function surface(map,colour){const mesh=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshStandardMaterial({map,color:colour,roughness:1}));root.add(mesh);mesh.receiveShadow=mesh.castShadow=true;return(cells,x,y,dx=.5,dy=.5)=>{const f=heightField(cells,8,8,dx,dy);mesh.visible=f.volume>1e-12;mesh.geometry.dispose();mesh.geometry=new THREE.BufferGeometry();mesh.geometry.setAttribute('position',new THREE.Float32BufferAttribute(f.positions,3));const uv=[];for(let i=0;i<f.positions.length;i+=3)uv.push(f.positions[i],-f.positions[i+2]);mesh.geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));mesh.geometry.computeVertexNormals();mesh.position.set(x,.008,-y);};}
function fit(){const mobile=innerWidth<=700,rect=$('world').getBoundingClientRect(),panel=$('story').getBoundingClientRect(),controls=$('controls').getBoundingClientRect();const w=innerWidth,h=mobile?rect.height:innerHeight;
renderer.setSize(w,h,false);camera.aspect=w/h;const safe=mobile?{l:12,r:w-12,t:15,b:h-15}:{l:24,r:panel.left-24,t:90,b:controls.top-16};
camera.setViewOffset(w,h,w/2-(safe.l+safe.r)/2,h/2-(safe.t+safe.b)/2,w,h);
const centre=new THREE.Vector3(3.5,1,0),direction=new THREE.Vector3(21,20.5,28).normalize();
const corners=[];for(const x of [-9,15])for(const y of [0,3.4])for(const z of [-6,6])corners.push(new THREE.Vector3(x,y,z));
let lo=5,hi=220;for(let i=0;i<36;i++){const d=(lo+hi)/2;camera.position.copy(centre).addScaledVector(direction,d);camera.lookAt(centre);camera.updateMatrixWorld();camera.updateProjectionMatrix();const p=corners.map(v=>v.clone().project(camera));if(p.every(v=>(v.x+1)*w/2>=safe.l&&(v.x+1)*w/2<=safe.r&&(1-v.y)*h/2>=safe.t&&(1-v.y)*h/2<=safe.b))hi=d;else lo=d;}
renderer.render(scene,camera);}
function rebuild(){while(boundaries.children.length){const o=boundaries.children[0];boundaries.remove(o);o.geometry?.dispose();o.material?.dispose();}const s=frame.state,steel=new THREE.MeshStandardMaterial({color:0x596560,roughness:.8});for(const side of [-1,1])box([2*s[90],.5,.12],[s[88],.25,-s[89]+side*s[91]],steel,boundaries);box([.12,.5,2*s[91]],[s[88]+s[90],.25,-s[89]],steel,boundaries);
for(const b of client.state.scenario.scene.obstacles)box([b[1]-b[0],2.8,b[3]-b[2]],[(b[0]+b[1])/2,1.4,-(b[2]+b[3])/2],new THREE.MeshStandardMaterial({color:0x8a6d52,roughness:1}),boundaries);}
async function api(path,body){
  const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,cache:'no-store'});
  const data=await response.json();if(!response.ok)throw Error(data.error||`Local service returned ${response.status}.`);return data;
}
function controls(){
  const run=client.state,changing=!!client.resetToken||client.controlBusy;
  $('play').disabled=!run||run.playback.finished||changing||exporting;
  $('play').textContent=client.desiredRunning||run?.playback.running?'Pause':'Run';
  $('step').disabled=!client.canStep||exporting;
  $('reset').disabled=!info||!!client.resetToken||exporting;
  $('export').disabled=!run||changing||!!client.stepToken||exporting;
  $('family').disabled=$('controller').disabled=$('seed').disabled=!!client.resetToken||exporting;
}
function draw(){
  controls();const run=client.state;if(!run||!loader)return;
  if(run.frames.length)frame=run.frames.at(-1);if(!frame)return;
  if(boundRun!==run.run_id){boundRun=run.run_id;rebuild();fit();}
  const s=frame.state,t=run.telemetry,p=present(run,frame);
  loader.apply(s.slice(0,7),frame.wheel_angles_rad,s[7]);pile(s.slice(15,79),s[79],s[80]);
  receiver(Array(64).fill(s[8]/(s[81]*4*s[90]*s[91])),s[88]-s[90],s[89]-s[91],s[90]/4,s[91]/4);
  $('payload').textContent=`${(s[7]/1000).toFixed(2)} t`;$('delivered').textContent=`${(s[8]/1000).toFixed(2)} t`;$('clock').textContent=`${s[10].toFixed(1)} s`;
  $('description').textContent=info.family_labels[run.family]+'.';
  $('source').textContent=`New synthetic execution. ${run.control_description}. No machine connection.`;
  $('control-mode').textContent=p.mode;$('control-owner').textContent=p.owner;$('sensor-health').textContent=p.sensor;
  $('coverage').textContent=p.coverage;$('range-age').textContent=p.age;$('input-time').textContent=p.inputTime;
  const status=document.querySelector('.runtime-status');status.dataset.override=String(p.override);status.dataset.unusable=String(!t.sensor.usable);
  $('outcome').textContent=p.outcome;
  for(let i=0;i<4;i++){$(`proposal-${i}`).textContent=command(t.neural_proposal?.[i]);$(`applied-${i}`).textContent=command(t.applied_action?.[i]);}
  $('decision-count').textContent=`${run.outcome.decisions} decisions executed. Task clock ${t.task_time_s.toFixed(1)} s.`;
  $('identity').textContent=`Practice seed ${run.scenario.seed}. Run ${run.run_id}. Checkpoint SHA-256 ${run.checkpoint_sha256}. Qualification SHA-256 ${run.qualification_sha256}. Runtime SHA-256 ${run.runtime_sha256}.`;
  [...$('phases').children].forEach((element,index)=>element.setAttribute('aria-current',index===frame.phase?'step':'false'));
  renderer.render(scene,camera);
}
function error(error){
  client.desiredRunning=false;controls();$('error').textContent=error.message;$('error').hidden=false;$('retry').hidden=false;
  document.body.dataset.error='true';
}
async function act(action){
  $('error').hidden=$('retry').hidden=true;
  try{await action();document.body.dataset.error='false';}
  catch(e){error(e);if(client.state?.playback.running)try{await client.pause();}catch{/* Reconnect explicitly after an unavailable service. */}}
}
function selection(){return {family:$('family').value,source:$('controller').value,seed:Number($('seed').value)};}
function reset(){return act(()=>client.reset(selection()));}
function sources(){
  const previous=$('controller').value;$('controller').replaceChildren();
  for(const source of info.supported_sources[$('family').value]){const option=document.createElement('option');option.value=source;option.textContent=info.source_labels[source];$('controller').append(option);}
  if([...$('controller').options].some(o=>o.value===previous))$('controller').value=previous;
}
async function download(){
  exporting=true;controls();
  try{const trace=await client.exportTrace();if(!trace)return;
    const url=URL.createObjectURL(new Blob([JSON.stringify(trace,null,2)+'\n'],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download=`kessel-synthetic-${trace.run_id}.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }finally{exporting=false;controls();}
}
async function start(){
  try{
    info=await api('/api/info');$('family').replaceChildren();
    for(const family of info.families){const option=document.createElement('option');option.value=family;option.textContent=info.family_labels[family];$('family').append(option);}
    sources();$('seed').min=info.seed_min;$('seed').max=info.seed_max;
    const response=await fetch('data/experience.json');if(!response.ok)throw Error('Scene configuration unavailable.');const config=await response.json();
    const [ore,floor,model,asset]=await Promise.all([texture(config.assets.ore),texture(config.assets.floor,8),fetch(config.assets.loader).then(r=>r.json()),authoredAsset(config.visuals.authored.reference_loader)]);
    loader=createReferenceLoader(model,ore,asset);root.add(loader.root);pile=surface(ore,0xb1a08a);receiver=surface(ore,0xa99c86);
    const ground=new THREE.Mesh(new THREE.PlaneGeometry(36,14),new THREE.MeshStandardMaterial({map:floor,color:0x67736d,roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.set(3,-.012,0);ground.receiveShadow=true;root.add(ground);
    await document.fonts.ready;await client.reset(selection());fit();document.body.dataset.ready='true';
  }catch(e){error(Error(`Start the qualified simulation service, then reconnect. ${e.message}`));}
}
$('reset').onclick=reset;$('family').onchange=sources;$('retry').onclick=()=>location.reload();
$('step').onclick=()=>act(()=>client.step(1));$('play').onclick=()=>act(()=>client.desiredRunning||client.state?.playback.running?client.pause():client.play());
$('export').onclick=()=>act(download);addEventListener('resize',fit);
let previous=0;function tick(now){if(client.playing&&!client.stepToken&&now-previous>=100){previous=now;act(()=>client.step(1,true));}requestAnimationFrame(tick);}requestAnimationFrame(tick);start();
