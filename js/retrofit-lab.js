import * as THREE from 'three';
import {visibleBounds,boxCorners} from './replay-framing.js';

export async function attachRetrofitLab(config,base){
 const response=await fetch('data/retrofit-showcase.json');if(!response.ok)throw Error('Retrofit engineering content unavailable');const content=await response.json();
 const $=id=>document.getElementById(id),reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const entries=new Map(base.components.map(e=>[e.spec.id,e]));
 let focusPart=false,focusAmount=0;
 let view='assembled',selected='enclosure',hover=null,yaw=-.18,pitch=.35,signalTime=0,signalStage=0,signalPlaying=!reduced,frameKey='',frameAudit=null;
 const originalOpacity=new WeakMap(),originalTransparency=new WeakMap(),originalDepth=new WeakMap(),originalShadow=new WeakMap();
 const baseUpdate=base.update.bind(base),baseDiagnostics=base.diagnostics.bind(base),baseFocus=base.focus.bind(base);
 // Consistent metal, board and package response under a local studio rig.
 base.root.traverse(o=>{if(!o.isMesh)return;for(const m of Array.isArray(o.material)?o.material:[o.material]){
  if(!m?.isMeshStandardMaterial)continue;
  if(/Anodised|Machined|BareSteel/.test(m.name)){m.color.multiplyScalar(1.45);m.roughness=.34;}
  if(/PCB/.test(m.name)){m.color.set('#245b48');m.roughness=.67;}
 }});
 const key=new THREE.DirectionalLight(0xe6f3e9,3.1);key.position.set(4,7,8);base.root.add(key);
 const rim=new THREE.DirectionalLight(0x8eafc4,2.2);rim.position.set(-5,4,-6);base.root.add(rim);
 const fill=new THREE.HemisphereLight(0xc9e3db,0x18202b,1.4);base.root.add(fill);
 function plate(text,w,h,parent,position,up=false){
  const c=document.createElement('canvas');c.width=1024;c.height=128;const ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);ctx.fillStyle='#c0d0c2';ctx.font='40px monospace';ctx.textAlign='center';ctx.fillText(text,512,80);
  const map=new THREE.CanvasTexture(c);map.colorSpace=THREE.SRGBColorSpace;
  const mesh=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({map,transparent:true,depthWrite:false,opacity:.85}));mesh.position.fromArray(position);if(up)mesh.rotation.x=-Math.PI/2;parent.add(mesh);
 }
 plate('K E S S E L   /   K-01',1.75,.16,entries.get('cover').group,[0,.02,1.315]);
 for(const id of ['compute','controls','power']){const e=entries.get(id);plate(content.components[id].code+'   REV 01',e.spec.size[0]*.8,.1,e.group,[0,.029,-e.spec.size[2]*.40],true);}
 const ferrite=new THREE.MeshStandardMaterial({color:0x18232a,roughness:.62,metalness:.15}),copper=new THREE.MeshStandardMaterial({color:0x9d7851,metalness:.82,roughness:.42});
 for(const x of [-.25,.25]){const coil=new THREE.Mesh(new THREE.TorusGeometry(.10,.035,7,24),copper);coil.rotation.x=Math.PI/2;coil.position.set(x,.12,.15);entries.get('power').group.add(coil);const core=new THREE.Mesh(new THREE.CylinderGeometry(.065,.065,.065,16),ferrite);core.position.set(x,.1,.15);entries.get('power').group.add(core);}
 // Retain a fixed base envelope; never fit against the 100 m shadow receiver.
 baseUpdate(0);
 const dock=$('kit-components'),callouts=$('kit-callouts'),svg=$('kit-leaders');dock.replaceChildren();callouts.replaceChildren();
 const buttons=new Map(),labels=new Map();
 for(const [i,e] of [...entries.values()].entries()){
  const info=content.components[e.spec.id],button=document.createElement('button');button.role='tab';button.id='kit-part-'+e.spec.id;button.dataset.component=e.spec.id;button.setAttribute('aria-controls','kit-part-panel');button.innerHTML=`<span>${String(i+1).padStart(2,'0')} / ${info.code}</span><strong>${info.label}</strong>`;dock.append(button);buttons.set(e.spec.id,button);
  const label=document.createElement('button');label.className='kit-callout';label.dataset.component=e.spec.id;label.innerHTML=`<i></i>${info.code}`;label.setAttribute('aria-label','Inspect '+info.label);callouts.append(label);labels.set(e.spec.id,label);
  for(const element of [button,label]){element.addEventListener('click',()=>select(e.spec.id));element.addEventListener('mouseenter',()=>{hover=e.spec.id;});element.addEventListener('mouseleave',()=>{hover=null;});}
  button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const ids=[...entries.keys()],n=event.key==='Home'?0:event.key==='End'?ids.length-1:(i+(event.key==='ArrowRight'?1:-1)+ids.length)%ids.length;select(ids[n]);buttons.get(ids[n]).focus();});
 }
 function inspector(){
  const info=content.components[selected];$('kit-part-panel').setAttribute('aria-labelledby','kit-part-'+selected);$('kit-part-code').textContent=info.code+' / '+info.label;$('kit-part-title').textContent=info.title;$('kit-part-description').textContent=info.description;
  $('kit-part-facts').replaceChildren(...info.facts.map(([key,value])=>{const row=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value;row.append(dt,dd);return row;}));
  for(const [id,b] of buttons){b.setAttribute('aria-selected',String(id===selected));b.tabIndex=id===selected?0:-1;}
 }
 function setView(next){
  view=next;if(next!=='exploded')focusPart=false;base.setTarget(next==='assembled'?0:1);frameKey='';
  for(const [id,name] of [['kit-view-assembled','assembled'],['assemble-kit','exploded'],['kit-view-signal','signal']])$(id).setAttribute('aria-pressed',String(next===name));
  $('kit-signal-panel').hidden=next!=='signal';document.querySelector('.kit-inspector').hidden=next==='signal';
  if(next==='assembled'&&!['enclosure','cover','camera','lidar'].includes(selected)){selected='enclosure';inspector();}
 }
 function select(id){if(!entries.has(id))return;selected=id;if(view==='assembled'&&['compute','power','controls'].includes(id))setView('exploded');else if(view==='signal')setView('exploded');inspector();}
 for(const [id,next] of [['kit-view-assembled','assembled'],['assemble-kit','exploded'],['kit-view-signal','signal']])$(id).addEventListener('click',()=>setView(next));
 for(const [i,stage] of content.signal_stages.entries()){
  const b=document.createElement('button');b.textContent=stage.label;b.dataset.signalStage=i;b.addEventListener('click',()=>{signalStage=i;signalTime=i*content.signal_seconds_per_stage;signalPlaying=false;signalUI();});$('kit-signal-steps').append(b);
 }
 function signalUI(){
  const stage=content.signal_stages[signalStage];$('kit-signal-equation').textContent=stage.equation;$('kit-signal-description').textContent=stage.description;
  for(const b of $('kit-signal-steps').children)b.setAttribute('aria-pressed',String(Number(b.dataset.signalStage)===signalStage));$('kit-pause').textContent=signalPlaying?'Pause':'Play';
 }
 $('kit-prev').addEventListener('click',()=>{signalStage=(signalStage+3)%4;signalTime=signalStage*content.signal_seconds_per_stage;signalPlaying=false;signalUI();});
 $('kit-next').addEventListener('click',()=>{signalStage=(signalStage+1)%4;signalTime=signalStage*content.signal_seconds_per_stage;signalPlaying=false;signalUI();});
 $('kit-pause').addEventListener('click',()=>{signalPlaying=!signalPlaying;signalUI();});
 $('kit-reset-view').addEventListener('click',()=>{yaw=-.18;pitch=.35;focusPart=false;frameKey='';});
 $('kit-focus-part').addEventListener('click',()=>{if(view!=='exploded')setView('exploded');focusPart=!focusPart;frameKey='';});
 const windowElement=$('kit-window');let drag=null;
 windowElement.addEventListener('pointerdown',event=>{if(event.target.closest('button'))return;drag={id:event.pointerId,x:event.clientX,y:event.clientY};windowElement.setPointerCapture(event.pointerId);});
 windowElement.addEventListener('pointermove',event=>{if(!drag||drag.id!==event.pointerId)return;yaw+=(event.clientX-drag.x)*.007;pitch=THREE.MathUtils.clamp(pitch+(event.clientY-drag.y)*.004,-.15,.8);drag.x=event.clientX;drag.y=event.clientY;frameKey='';});
 for(const type of ['pointerup','pointercancel'])windowElement.addEventListener(type,()=>{drag=null;});
 // Signal annotations follow component positions; they do not represent wiring.
 const signalGroup=new THREE.Group();base.root.add(signalGroup);const signalMaterial=new THREE.LineBasicMaterial({color:0x6fd9ae,transparent:true,opacity:.7,depthTest:false});
 const links=[['lidar','compute'],['camera','compute'],['compute','controls'],['power','compute']].map(([from,to])=>{const line=new THREE.Line(new THREE.BufferGeometry(),signalMaterial);signalGroup.add(line);const dot=new THREE.Mesh(new THREE.SphereGeometry(.045,10,8),new THREE.MeshBasicMaterial({color:0xadf2ce,depthTest:false}));signalGroup.add(dot);return {from,to,line,dot,curve:null};});
 const contextMeshes=base.root.children.filter(o=>o.isMesh);
 function opacity(root,alpha){root.visible=alpha>.005;root.traverse(o=>{if(!o.isMesh)return;if(!originalShadow.has(o))originalShadow.set(o,o.castShadow);o.castShadow=alpha>.99&&originalShadow.get(o);for(const m of Array.isArray(o.material)?o.material:[o.material]){if(!originalOpacity.has(m)){originalOpacity.set(m,m.opacity);originalTransparency.set(m,m.transparent);originalDepth.set(m,m.depthWrite);}m.opacity=originalOpacity.get(m)*alpha;const transparent=alpha<.999||originalTransparency.get(m);if(m.transparent!==transparent){m.transparent=transparent;m.needsUpdate=true;}m.depthWrite=alpha>.99&&originalDepth.get(m);}});}
 let lastAmount=-1,lastFocus=null,overlayKey='';
 function update(dt){
  baseUpdate(dt);base.root.rotation.y=yaw;focusAmount=reduced?(focusPart?1:0):THREE.MathUtils.damp(focusAmount,focusPart?1:0,8,dt);if(Math.abs(focusAmount-(focusPart?1:0))<.001)focusAmount=focusPart?1:0;$("kit-focus-part").setAttribute("aria-pressed",String(focusPart));$("kit-focus-part").textContent=focusPart?"Full assembly ↙":"Focus part ↗";
  if(view==='signal'&&signalPlaying){signalTime+=Math.min(dt,.1);const next=Math.floor(signalTime/content.signal_seconds_per_stage)%4;if(next!==signalStage){signalStage=next;signalUI();}}
  for(const [id,entry] of entries)opacity(entry.group,id===selected?1:1-focusAmount);for(const mesh of contextMeshes)opacity(mesh,1-focusAmount);
  const active=view==='signal'?content.signal_stages[signalStage].components:[hover||selected];if(lastFocus!==active[0]){baseFocus(active[0]);lastFocus=active[0];}
  signalGroup.visible=view==='signal';const amount=baseDiagnostics().amount;
  if(Math.abs(amount-lastAmount)>.001){
   for(const item of links){const a=entries.get(item.from).group.position.clone().add(new THREE.Vector3(0,.2,0)),b=entries.get(item.to).group.position.clone().add(new THREE.Vector3(0,.2,0)),mid=a.clone().lerp(b,.5);mid.y+=.5;item.curve=new THREE.QuadraticBezierCurve3(a,mid,b);item.line.geometry.dispose();item.line.geometry=new THREE.BufferGeometry().setFromPoints(item.curve.getPoints(24));}lastAmount=amount;
  }
  for(const [i,item] of links.entries())if(item.curve)item.dot.position.copy(item.curve.getPoint((signalTime*.4+i*.21)%1));
  $('kit-stage-label').textContent=view==='signal'?'03 / Local signal architecture':amount>.98?'02 / Exploded assembly':amount<.02?'01 / Assembled unit':'ASSEMBLY / Mechanical separation';
 }
 function present(camera,rect){
  const amount=baseDiagnostics().amount,key=[rect.left,rect.top,rect.width,rect.height,amount.toFixed(3),yaw.toFixed(3),pitch.toFixed(3),focusAmount.toFixed(3),selected].join('/');
  if(key!==frameKey){
   frameKey=key;
   base.root.updateMatrixWorld(true);
   const b=new THREE.Box3();for(const entry of entries.values()){const visible=entry.group.visible;entry.group.visible=true;b.union(visibleBounds(entry.group));entry.group.visible=visible;}
   const rotation=new THREE.Matrix4().makeRotationY(yaw);b.expandByPoint(new THREE.Vector3(-2.1,-.4,-1.6).applyMatrix4(rotation));b.expandByPoint(new THREE.Vector3(2.1,-.4,1.6).applyMatrix4(rotation));
   if(focusAmount>0){const part=visibleBounds(entries.get(selected).group).expandByScalar(.26);b.min.lerp(part.min,focusAmount);b.max.lerp(part.max,focusAmount);}
   const centre=b.getCenter(new THREE.Vector3()),points=boxCorners(b),direction=new THREE.Vector3(9,5.5+pitch*8,12).normalize();
   camera.aspect=innerWidth/innerHeight;camera.fov=32;camera.near=.05;camera.far=150;camera.setViewOffset(innerWidth,innerHeight,innerWidth/2-(rect.left+rect.width/2),innerHeight/2-(rect.top+rect.height*.48),innerWidth,innerHeight);
   const safe={left:rect.left+60,right:rect.right-60,top:rect.top+24,bottom:rect.bottom-40};
   const project=distance=>{camera.position.copy(centre).addScaledVector(direction,distance);camera.lookAt(centre);camera.updateMatrixWorld(true);camera.updateProjectionMatrix();const p=points.map(p=>p.clone().project(camera));return {left:Math.min(...p.map(p=>(p.x+1)*innerWidth/2)),right:Math.max(...p.map(p=>(p.x+1)*innerWidth/2)),top:Math.min(...p.map(p=>(1-p.y)*innerHeight/2)),bottom:Math.max(...p.map(p=>(1-p.y)*innerHeight/2))};};
   let lo=3,hi=80;for(let i=0;i<17;i++){const mid=(lo+hi)/2,p=project(mid);if(p.left>=safe.left&&p.right<=safe.right&&p.top>=safe.top&&p.bottom<=safe.bottom)hi=mid;else lo=mid;}
   frameAudit={safe,projected:project(hi),target:centre.toArray(),distance:hi};
  }
  const overlay=[frameKey,selected,view].join('/');if(overlay===overlayKey)return new THREE.Vector3(...frameAudit.target);overlayKey=overlay;
  base.root.updateMatrixWorld(true);svg.setAttribute('viewBox',`0 0 ${rect.width} ${rect.height}`);const projected=[];
  for(const [id,e] of entries){const label=labels.get(id),visible=(focusAmount>.5?id===selected:view!=='assembled'||['enclosure','cover','lidar','camera'].includes(id));label.hidden=!visible;if(!visible)continue;const a=e.group.localToWorld(new THREE.Vector3(0,e.spec.size[1]/2,0)).project(camera);projected.push({id,x:(a.x+1)*innerWidth/2-rect.left,y:(1-a.y)*innerHeight/2-rect.top,side:content.components[id].side});}
  let markup='';
  for(const side of ['left','right']){const items=projected.filter(p=>p.side===side).sort((a,b)=>a.y-b.y);let last=18;for(const p of items){const y=Math.max(last,Math.min(rect.height-62,p.y));last=y+29;const x=side==='left'?8:rect.width-90,end=side==='left'?x+76:x;const label=labels.get(p.id);label.style.left=x+'px';label.style.top=(y-9)+'px';label.classList.toggle('selected',p.id===selected);markup+=`<path class="${p.id===selected?'selected':''}" d="M${p.x},${p.y} L${side==='left'?end+14:end-14},${y} L${end},${y}"/><circle class="${p.id===selected?'selected':''}" cx="${p.x}" cy="${p.y}" r="2"/>`;}}
  svg.innerHTML=markup;
  return new THREE.Vector3(...frameAudit.target);
 }
 inspector();signalUI();setView('assembled');update(0);
 return Object.assign(base,{update,present,select,setView,invalidateFrame(){frameKey='';overlayKey='';},diagnostics(){return {...baseDiagnostics(),view,selected,focusPart,focusAmount,orbit:{yaw,pitch},signal:{stage:signalStage,time:signalTime,playing:signalPlaying,source:'illustrative local architecture'},framing:frameAudit};}});
}
