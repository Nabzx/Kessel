import {loadExperiment,sampleEpisode} from './recorded-data.js';
const chapters=[
 {id:'perception',title:'What the machine sees.',eyebrow:'01 / Local observation',caption:'Recorded synthetic height crop',steps:['Range validity','Local geometry','Observation → action'],note:'A 5 × 5 height crop and validity mask from the recorded simulator. The projection is schematic, not a camera or LiDAR reconstruction.'},
 {id:'prediction',title:'Predict before contact.',eyebrow:'02 / Action-conditioned dynamics',caption:'Recorded learned forecast',steps:['Observe','Apply action','Compare the future'],note:'Raw learned dynamics and the reference simulator are separate. Ensemble spread is not calibrated confidence; physical violations remain visible.'},
 {id:'training',title:'Train. Evaluate. Compress.',eyebrow:'03 / Policy to edge',caption:'Retained CPU experiment',steps:['Policy checkpoints','Held-out evaluation','Actor export'],note:'Recorded CPU results. No learned complete delivery cycle was demonstrated. Distillation and quantisation are evaluated separately; Jetson deployment remains proposed.'},
 {id:'offline',title:'The link can disappear.',eyebrow:'04 / Local autonomy',caption:'Authored product architecture',steps:['Local sensing','External link unavailable','Local loop continues'],note:'Proposed sensing–policy–actuation architecture. This sequence illustrates separation from external communications; it is not a measured field deployment or a safety guarantee.'},
 {id:'fleet',title:'One deployment informs the next.',eyebrow:'05 / Fleet learning',caption:'Authored future fleet',steps:['Buffer observations','Synchronise when connected','Evaluate before release'],note:'Proposed feedback loop. Data collection, model evaluation and policy release are separate steps. No deployed fleet, customer or measured compounding gain is implied.'}
];
export function installChapters(){
 const section=document.getElementById('engineering-chapters');
 section.innerHTML='<div class="chapter-heading"><p class="section-label">Inside Kessel</p><h2>From observation<br>to onboard action.</h2></div><div class="chapter-links">'+chapters.map((c,i)=>`<button data-chapter="${i}"><span>0${i+1}</span><strong>${c.title}</strong><span>↗</span></button>`).join('')+'</div>';
 const dialog=document.getElementById('technical-dialog'),canvas=document.getElementById('technical-canvas'),ctx=canvas.getContext('2d');
 let index=0,step=0,running=false,elapsed=0,last=0,raf=0,request=0,bundle=null,trigger=null,engineering=null,reference=null;
 const saved=new Map();
 const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
 const $=id=>document.getElementById(id);
 const colour={ink:'#e8e8de',muted:'#829993',green:'#4ee29b',blue:'#8cc5d3',grid:'#18312f',red:'#db8978'};
 function label(text,x,y,c=colour.muted,size=12){ctx.fillStyle=c;ctx.font=`${size}px "JetBrains Mono",monospace`;ctx.fillText(text,x,y);}
 function line(a,b,c=colour.muted,w=1,dash=[]){ctx.strokeStyle=c;ctx.lineWidth=w;ctx.setLineDash(dash);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();ctx.setLineDash([]);}
 function node(x,y,w,h,title,subtitle,active=false){ctx.fillStyle=active?'#102a24':'#0b1718';ctx.fillRect(x,y,w,h);ctx.strokeStyle=active?colour.green:'#36504b';ctx.strokeRect(x+.5,y+.5,w,h);label(title,x+18,y+30,active?colour.ink:colour.muted,14);if(subtitle)label(subtitle,x+18,y+52,colour.muted,10);}
 function projection(x,z,h=0){return [380+x*38-z*24,310+x*15+z*12-h*65];}
 function dot(p,r,c){ctx.fillStyle=c;ctx.beginPath();ctx.arc(...p,r,0,Math.PI*2);ctx.fill();}
 function crop(frame){
   for(let i=-4;i<=7;i++){line(projection(i,-4),projection(i,7),colour.grid);line(projection(-4,i),projection(7,i),colour.grid);}
   const obs=frame.observation;
   for(let x=0;x<5;x++)for(let z=0;z<5;z++){
    const k=x*5+z,h=obs[15+k],valid=obs[40+k],p=projection(x-1,z-1,h);
    line(projection(x-1,z-1),p,valid?'#36564c':'#563d37');dot(p,valid?3:2,valid?colour.green:colour.red);
    if(valid&&step>0){line(p,[p[0]+13,p[1]+5],colour.green);line(p,[p[0]-8,p[1]+5],colour.green);}
   }
   label('LOCAL HEIGHT / METRES',64,72,colour.blue,11);label('25 samples · recorded mask',64,95,colour.muted,11);
   label('VALID',64,450,colour.green);label(`${obs.slice(40).filter(Boolean).length} / 25`,64,477,colour.ink,26);
   if(step===2){node(520,395,170,75,'π(oₜ) → aₜ','4 physical controls',true);line([480,400],[520,430],colour.green);}
 }
 function prediction(ep){
   const anchors=ep.records.filter(r=>r.predictions?.some(p=>p.prediction&&p.horizon_decisions===8));const anchor=anchors[Math.floor(anchors.length*.55)];
   if(!anchor){label('No retained forecast for this case',100,220);return;}
   const pred=anchor.predictions.find(p=>p.prediction&&p.horizon_decisions===[1,4,8][step])||anchor.predictions.find(p=>p.prediction),actual=ep.records[pred.reference_index];
   const origin=anchor.state,extent=Math.max(.08,...[actual.state,pred.prediction].flatMap(s=>[Math.abs(s[0]-origin[0]),Math.abs(s[1]-origin[1])]))*1.5,scale=155/extent;
   const screen=s=>[260+(s[0]-origin[0])*scale,270-(s[1]-origin[1])*scale];
   for(let i=0;i<9;i++)line([80,100+i*40],[700,100+i*40],colour.grid);
   dot(screen(origin),7,colour.blue);const future=screen(actual.state),learned=screen(pred.prediction);
   line(screen(origin),future,colour.ink,2,[6,5]);line(screen(origin),learned,colour.green,2);
   ctx.strokeStyle=colour.ink;ctx.strokeRect(future[0]-9,future[1]-9,18,18);ctx.strokeStyle=colour.green;ctx.beginPath();ctx.moveTo(learned[0],learned[1]-12);ctx.lineTo(learned[0]+12,learned[1]);ctx.lineTo(learned[0],learned[1]+12);ctx.lineTo(learned[0]-12,learned[1]);ctx.closePath();ctx.stroke();
   line(future,learned,colour.red,1);label(`RESIDUAL ${pred.residual.position_m.toFixed(4)} m`,64,470,colour.ink,20);
   label(`t ${anchor.t_s.toFixed(2)} → ${pred.target_t_s.toFixed(2)} s · +${pred.horizon_decisions} decision`,64,72,colour.blue,11);
   label('● Observed     □ Reference     ◇ Learned',64,105,colour.muted,11);label(`GRID ${(40/scale).toFixed(3)} m`,64,135,colour.muted,10);
   const invalid=Object.entries(pred.violations).some(([k,v])=>k==='mass_error_kg'?Math.abs(v)>1:!!v);
   label(invalid?'RAW FORECAST / PHYSICAL VIOLATION':'RAW FORECAST / UNFILTERED',64,505,invalid?colour.red:colour.muted,11);
   anchor.action?.forEach((v,i)=>{label(['ACCEL','STEER','BOOM','BUCKET'][i],550,160+i*44,colour.muted,10);line([550,177+i*44],[550+v*95,177+i*44],colour.green,3);});
 }
 function training(){
   const ep=bundle.episodes[Math.min(step,bundle.episodes.length-1)],curve=bundle.learning_curve,values=curve.map(r=>r.mean_step_reward),lo=Math.min(...values),hi=Math.max(...values);
   label('MEASURED PPO / CPU',64,70,colour.blue,11);ctx.strokeStyle=colour.green;ctx.lineWidth=1.5;ctx.beginPath();values.forEach((v,i)=>{const p=[64+i/(values.length-1)*610,270-(v-lo)/Math.max(.001,hi-lo)*120];i?ctx.lineTo(...p):ctx.moveTo(...p)});ctx.stroke();
   node(64,330,180,80,'Policy','observation → action',step===0);node(280,330,180,80,'Evaluate','held-out outcomes',step===1);node(496,330,180,80,'Export actor','ONNX / proposed edge',step===2);line([244,370],[280,370]);line([460,370],[496,370]);
   const c=ep.policy?.training_counters;label(`${c?.environment_steps?.toLocaleString('en-GB')||0} charged decisions`,64,105,colour.ink,20);
   label(`Checkpoint ${ep.name} · delivered ${ep.metrics.delivered_kg.toFixed(0)} kg`,64,455,colour.muted,12);
   label('VALIDATION BOUNDARY / NO LEARNED FULL CYCLE',64,490,colour.red,11);
   if(step===2&&engineering){const fp=engineering.variants.find(r=>r.variant==='onnx_teacher_fp32'),q=engineering.variants.find(r=>r.variant==='onnx_teacher_int8');label(`${(fp.file_bytes/1000).toFixed(1)} kB FP32 → ${(q.file_bytes/1000).toFixed(1)} kB INT8 / CPU`,64,520,colour.green,12);}
 }
 function offline(){
   node(75,180,180,85,'Sense','local observations',true);node(305,180,180,85,'Onboard policy','π(oₜ) → aₜ',true);node(535,180,180,85,'Actuate','existing controls',true);
   line([255,222],[305,222],colour.green,2);line([485,222],[535,222],colour.green,2);line([625,265],[625,340],colour.green);line([625,340],[165,340],colour.green);line([165,340],[165,265],colour.green);
   node(315,55,170,65,'External link',step===0?'available':'unavailable',step===0);line([395,120],[395,180],step===0?colour.muted:colour.red,1,[4,5]);
   if(step>0){line([385,140],[405,160],colour.red,2);line([405,140],[385,160],colour.red,2);}
   const t=reduced?0:elapsed*.16%1;dot([165+t*460,340],5,colour.green);
   if(reference){
    const ep=reference.episodes[0],sample=sampleEpisode(ep,Math.min(ep.records.at(-1).t_s,(step*4+elapsed)*3)),p=sample.pose;
    const x=115+(p[0]+3)*22,y=440-p[1]*15;
    ctx.save();ctx.translate(x,y);ctx.rotate(-p[2]);ctx.fillStyle=colour.ink;ctx.fillRect(-20,-9,40,18);ctx.fillStyle=colour.green;ctx.fillRect(21,-12,10,24);ctx.restore();
    label(`REFERENCE / ${sample.frame.t_s.toFixed(1)} s / ${(sample.frame.state[7]/1000).toFixed(2)} t`,75,505,colour.muted,11);
   }
   label(step===0?'LINK AVAILABLE':'LOCAL LOOP CONTINUES',75,390,colour.ink,20);
 }
 function fleet(){
   const names=['Loader A','Loader B','Loader C'];names.forEach((name,i)=>{node(65,90+i*115,170,72,name,step===0?'buffer locally':'sync when connected',true);line([235,126+i*115],[350,240],step>0?colour.green:colour.muted,1,step>0?[]:[3,6]);});
   node(350,195,170,85,'Model update','offline training',step===1);node(565,195,150,85,'Evaluate','release boundary',step===2);line([520,240],[565,240],colour.muted,1);
   label(step<2?'POLICY vₙ / LOCAL EXECUTION':'CANDIDATE vₙ₊₁ / EVALUATION FIRST',65,475,colour.ink,16);
   if(step===2)label('Underground → desert / glacier / deep sea / space',65,512,colour.muted,11);
 }
 function draw(){
   const rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,1.5);canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);ctx.setTransform(canvas.width/780,0,0,canvas.height/550,0,0);ctx.fillStyle='#071011';ctx.fillRect(0,0,780,550);
   if(!bundle){label('Preparing retained records…',64,260);return;}
   if(index===0)crop(bundle.episodes[0].records[Math.min(bundle.episodes[0].records.length-1,step*10)]);
   if(index===1)prediction(bundle.episodes[2]);if(index===2)training();if(index===3)offline();if(index===4)fleet();
 }
 function update(){const c=chapters[index];$('technical-eyebrow').textContent=c.eyebrow;$('technical-title').textContent=c.title;$('technical-source').textContent=c.caption;$('technical-step').textContent=c.steps[step];$('technical-note').textContent=c.note;$('technical-counter').textContent=`0${step+1} / 03`;$('technical-pause').textContent=running?'Pause':'Play';$('technical-next').textContent=step===2?'Next chapter →':'Continue →';draw();}
 function frame(now){if(!dialog.open)return;const dt=last?Math.min(.1,(now-last)/1000):0;last=now;if(running){elapsed+=dt;if(elapsed>=4){elapsed=0;if(step<2)step++;else {running=false;elapsed=4;}update();}if(index===3)draw();}raf=requestAnimationFrame(frame);}
 async function open(i,button){if(dialog.open)saved.set(index,{step,elapsed,running});index=i;const prior=saved.get(i);step=prior?.step||0;elapsed=prior?.elapsed||0;last=0;running=prior?prior.running:!reduced;trigger=button||trigger;const ticket=++request;if(!dialog.open)dialog.showModal();update();cancelAnimationFrame(raf);raf=requestAnimationFrame(frame);
  try{bundle=await loadExperiment();reference=reference||await loadExperiment(undefined,fetch,'reference-cycle-v1');engineering=engineering||await fetch('data/engineering.json').then(r=>{if(!r.ok)throw Error('Export comparison unavailable');return r.json()});if(ticket===request)update();}catch(e){$('technical-source').textContent='Records unavailable. Try again.';running=false;}
 }
 section.querySelectorAll('[data-chapter]').forEach(button=>button.addEventListener('click',()=>open(Number(button.dataset.chapter),button)));
 $('technical-close').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>{saved.set(index,{step,elapsed,running});++request;cancelAnimationFrame(raf);running=false;const active=document.activeElement;if(active===document.body||active===dialog||dialog.contains(active))trigger?.focus({preventScroll:true});});
 $('technical-next').addEventListener('click',()=>{elapsed=0;if(step<2){step++;running=false;update();}else open((index+1)%chapters.length);});$('technical-prev').addEventListener('click',()=>{elapsed=0;running=false;if(step>0){step--;update();}else open((index+chapters.length-1)%chapters.length);});$('technical-pause').addEventListener('click',()=>{running=!running;last=0;update();});
 window.addEventListener('resize',()=>{if(dialog.open)draw()});
 return {open,diagnostics:()=>({open:dialog.open,chapter:chapters[index].id,step,running,runId:bundle?.run_id})};
}
