import * as THREE from 'three';
import {createReferenceLoader} from './loader-stage.js';
import {authoredAsset} from './authored-assets.js';
import {texture,box,lightRig,seeded,line} from './scene-utils.js';
import {fitReplay} from './replay-framing.js';
import {trainingClock,trainingDuration} from './training-trace.js';

export async function createLearning(config){
 const [trace,ore,floor,normal,model,asset]=await Promise.all([
  fetch('data/training-demonstration.json').then(r=>{if(!r.ok)throw Error('Training demonstration unavailable');return r.json();}),
  texture(config.assets.ore),texture(config.assets.floor,9),texture(config.assets.floor_normal,9,false),
  fetch(config.assets.loader).then(r=>r.json()),authoredAsset(config.visuals.authored.reference_loader)
 ]);
 const root=new THREE.Group();root.name='illustrative-training-demonstration';
 const ground=new THREE.Mesh(new THREE.PlaneGeometry(38,38),new THREE.MeshStandardMaterial({map:floor,normalMap:normal,normalScale:new THREE.Vector2(.25,.25),color:0x697570,roughness:.97}));ground.rotation.x=-Math.PI/2;ground.position.set(2,.005,-5);ground.receiveShadow=true;root.add(ground);
 const grid=new THREE.GridHelper(38,38,0x516963,0x344945);grid.position.set(2,.025,-5);grid.material.transparent=true;grid.material.opacity=.22;root.add(grid);
 const steel=new THREE.MeshStandardMaterial({color:0x454f4b,metalness:.55,roughness:.7});
 const concrete=new THREE.MeshStandardMaterial({color:0x58605a,roughness:.98});
 const amber=new THREE.MeshStandardMaterial({color:0xb2954f,roughness:.7});
 const equipment=new THREE.Group();root.add(equipment);
 const loader=createReferenceLoader(model,ore,asset);root.add(loader.root);
 const source=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1,1),new THREE.MeshStandardMaterial({map:ore,color:0x9d9584,roughness:1}),160),deposited=new THREE.InstancedMesh(source.geometry,source.material,100);
 // Allocate once. Each episode retains its exact material ledger.
 source.castShadow=source.receiveShadow=true;deposited.castShadow=deposited.receiveShadow=true;root.add(source,deposited);
 const rand=seeded(5402),pose=new THREE.Object3D(),scatter=Array.from({length:160},(_,i)=>{const a=rand()*Math.PI*2,r=Math.sqrt(rand());return {x:Math.cos(a)*r,y:Math.sin(a)*r,h:(1-r)*.85,scale:.15+rand()*.18,rotation:[rand()*3,rand()*3,rand()*3]};});
 function pile(mesh,centre,kg,total,rx,ry){
  const volume=Math.cbrt(Math.max(.001,kg/total));mesh.visible=kg>1;
  for(let i=0;i<mesh.count;i++){const s=scatter[i];pose.position.set(centre[0]+s.x*rx*volume,(s.h+.12)*volume,-centre[1]-s.y*ry*volume);pose.scale.set(s.scale*1.2*volume,s.scale*.75*volume,s.scale*volume);pose.rotation.set(...s.rotation);pose.updateMatrix();mesh.setMatrixAt(i,pose.matrix);}
  mesh.instanceMatrix.needsUpdate=true;mesh.computeBoundingSphere();
 }
 const grains=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.06,0),source.material,20);grains.castShadow=true;root.add(grains);
 let route=null,blocked=null,trialIndex=-1,elapsed=0,playing=!matchMedia('(prefers-reduced-motion: reduce)').matches,state=null,frameAudit=null;
 const total=trainingDuration(trace),envelope=new THREE.Box3(new THREE.Vector3(-12,0,-18.5),new THREE.Vector3(16,3,8.5));
 lightRig(root,24,'mine');
 // Industrial services are opaque, physical and outside the travel envelope.
 for(const x of [-12.8,17.3]){box([.3,1.3,31],[x,.65,-5],concrete,root);for(let k=0;k<7;k++)box([.1,2.2,.1],[x,1.1,8-k*5],steel,root);}
 function label(text,point){
  const canvas=document.createElement('canvas');canvas.width=256;canvas.height=48;const c=canvas.getContext('2d');c.font='20px monospace';c.fillStyle='#a4cab6';c.fillText(text,8,30);
  const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(canvas),transparent:true,depthTest:false}));sprite.scale.set(5,.94,1);sprite.position.set(point[0],1.5,-point[1]);equipment.add(sprite);
 }
 function setTrial(index){
  trialIndex=index;equipment.traverse(o=>{if(o.isSprite){o.material.map.dispose();o.material.dispose();}else if(o.isMesh)o.geometry.dispose();});equipment.clear();if(route){root.remove(route);route.geometry.dispose();route.material.dispose();}if(blocked){root.remove(blocked);blocked.geometry.dispose();blocked.material.dispose();blocked=null;}
  const trial=trace.trials[index],[x,y]=trial.receiver;label('LOAD / 02 t',[trial.load_point[0],trial.load_point[1]-2]);label('RECEIVER',[x,y+2]);
  box([2.4,.10,2.2],[x,.05,-y],steel,equipment);
  for(const side of [-1,1])box([2.4,.65,.08],[x,.325,-y+side*1.1],steel,equipment);
  box([.08,.65,2.2],[x-1.2,.325,-y],steel,equipment);
  // Open receiving side faces the bucket. No front wall through its mouth.
  for(const side of [-1,1])box([.13,.8,.13],[trial.load_point[0]+1.6,.4,-trial.load_point[1]+side*1.5],amber,equipment);
  const points=trial.rows.filter((r,i)=>i%10===0&&r[12]>=4&&r[12]<=7).map(r=>[r[1],.05,-r[2]]);
  route=line(points.length?points:[[0,.05,-trial.load_point[1]],[7.8,.05,-trial.load_point[1]]],index>1?0x63d6aa:0xd19172,.7);root.add(route);
  if(trial.obstacle){
   const [ox,oy]=trial.obstacle.centre;label('OBSTACLE',[ox,oy+1.8]);box([1.3,.9,1.6],[ox,.45,-oy],concrete,equipment);box([1.35,.12,1.65],[ox,.86,-oy],amber,equipment);
   // A broken path is a route annotation on the floor, not a prediction box.
   const nominal=Array.from({length:36},(_,i)=>{const a=i/35*Math.PI;return [6*Math.sin(a),.055,-(6*(1-Math.cos(a)))];});
   blocked=line(nominal,0xbd795e,.45);root.add(blocked);
  }
 }
 function update(dt){
  if(playing)elapsed=Math.min(total,elapsed+Math.max(0,Math.min(dt,.1)));
  state=trainingClock(trace,elapsed);if(state.complete)playing=false;
  if(state.index!==trialIndex)setTrial(state.index);
  loader.apply(state.pose,state.wheelAngles,state.payloadKg);
  pile(source,state.trial.load_point,state.sourceKg,3000,1.3,1);
  pile(deposited,state.trial.receiver,state.deliveredKg,2000,.85,.75);
  grains.visible=state.inflightKg>.1;
  if(grains.visible){
   const lip=loader.bucket.localToWorld(new THREE.Vector3(0,0,1.05));
   for(let i=0;i<20;i++){const age=((state.time*2.4+i/20)%1)*.42;pose.position.set(lip.x+(i%3-1)*.08,Math.max(.08,lip.y-4.905*age*age),lip.z+(i%5-2)*.045);pose.scale.setScalar(.7+(i%3)*.3);pose.updateMatrix();grains.setMatrixAt(i,pose.matrix);}grains.instanceMatrix.needsUpdate=true;grains.computeBoundingSphere();
  }
  return {...state,elapsed,duration:total,playing,episodes:Math.round((state.index?trace.trials[state.index-1].represented_episodes:0)+(state.trial.represented_episodes-(state.index?trace.trials[state.index-1].represented_episodes:0))*Math.min(1,state.time/state.trial.duration_s)),reward:state.trial.reward,action:trace.phases[state.phase],jobs:trace.trials.slice(0,state.index).filter(t=>t.outcome==='success').length+(state.trial.outcome==='success'&&state.complete?1:state.phase===10?1:0)};
 }
 update(0);
 return {root,sourceMode:'authored',trace,update,replay(){elapsed=0;playing=true;trialIndex=-1;},pause(){playing=!playing;},get running(){return playing;},checkpoint(index){elapsed=trace.trials.slice(0,[0,1,2][index]||0).reduce((s,t)=>s+t.duration_s/trace.replay_speed+trace.reset_seconds,0);playing=true;},fitCamera(camera,panel,header){frameAudit=fitReplay(camera,envelope,panel,header);return frameAudit.target;},diagnostics(){const s=update(0);return {sourceMode:'authored',source:trace.source,learnedPolicyResult:false,elapsed,duration:total,playing,index:s.index,phase:s.action,jobs:s.jobs,payloadKg:s.payloadKg,deliveredKg:s.deliveredKg,sourceKg:s.sourceKg,inflightKg:s.inflightKg,completed:s.complete,pose:s.pose,frame:frameAudit};}};
}
