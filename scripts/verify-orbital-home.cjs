/* Real laptop walkthrough; renderer identity and visual captures accompany assertions. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),{createHash}=require('node:crypto');
const root=path.resolve(__dirname,'..'),out=process.env.KESSEL_QA_DIR||'/private/tmp/kessel-orbital-home',base=process.env.KESSEL_URL||'http://127.0.0.1:8080/';fs.mkdirSync(out,{recursive:true});
const data=JSON.parse(fs.readFileSync(path.join(root,'data/experience.json')));
const version=fs.readFileSync(path.join(root,'index.html'),'utf8').match(/name="kessel-presentation" content="([^"]+)"/)[1];
const sources=['index.html','js/experience.js','js/globe-stage.js','js/environment-scenes.js','css/orbital-home.css','data/experience.json'];
const report={date:new Date().toISOString(),sourceCommit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),sourceFiles:Object.fromEntries(sources.map(n=>[n,createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')])),checks:[],errors:[],profiles:[]};
async function frames(page,ms=3000){return page.evaluate(ms=>new Promise(resolve=>{let last,start;const times=[];function sample(t){if(last)times.push(t-last);last=t;start??=t;if(t-start<ms)requestAnimationFrame(sample);else{const sorted=[...times].sort((a,b)=>a-b);resolve({frames:times.length,meanFps:1000/(times.reduce((a,b)=>a+b,0)/times.length),p95Ms:sorted[Math.floor(sorted.length*.95)],p99Ms:sorted[Math.floor(sorted.length*.99)],maxMs:sorted.at(-1)});}}requestAnimationFrame(sample);}),ms);}
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});report.browser=browser.version();
 try{
  for(const spec of [{name:'retina',width:1440,height:900,dpr:2,motion:'no-preference'},{name:'compact',width:1365,height:768,dpr:1,motion:'no-preference'},{name:'reduced',width:1280,height:800,dpr:1,motion:'reduce'}]){
   const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:spec.dpr,reducedMotion:spec.motion,recordVideo:spec.name==='retina'?{dir:path.join(out,'video'),size:{width:960,height:600}}:undefined});
   const page=await context.newPage(),requests=[];page.on('pageerror',e=>report.errors.push(e.message));page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});page.on('request',r=>requests.push(r.url()));
   await page.addInitScript(()=>{window.coldHomeFrames=[];let previous;function sample(t){if(previous&&!document.body.classList.contains('ready'))window.coldHomeFrames.push(t-previous);previous=t;requestAnimationFrame(sample);}requestAnimationFrame(sample);});
   const diag=()=>page.evaluate(()=>window.homeDiagnostics());
   const stage=s=>page.waitForFunction(s=>document.querySelector('#experience').dataset.stage===s,s,{timeout:60000});
   const capture=name=>page.screenshot({path:path.join(out,`${spec.name}-${name}.jpg`),type:'jpeg',quality:88});
   const background=id=>page.waitForFunction(id=>{const d=window.homeDiagnostics();return d.environment===id&&d.environmentBackground.displayed===id&&!d.environmentBackground.pending;},id,{timeout:30000});
   await page.goto(base);await page.locator('body.ready').waitFor({timeout:45000});const readyMs=await page.evaluate(()=>performance.now());await page.evaluate(async()=>{window.homeDiagnostics=(await import('./js/experience.js')).diagnostics;});
   await page.waitForFunction(()=>!window.homeDiagnostics().camera.moving);await page.waitForTimeout(350);const hero=await frames(page),initial=await diag();
   assert.ok(readyMs<4000,`Local ready time ${readyMs} ms`);
   const orbitalBounds=await page.evaluate(async()=>{const THREE=await import('three'),d=window.homeDiagnostics(),camera=new THREE.PerspectiveCamera(d.camera.fov,innerWidth/innerHeight,.1,200);camera.position.fromArray(d.camera.position);camera.lookAt(0,0,0);camera.updateMatrixWorld();return d.globe.spacecraft.map(craft=>({kind:craft.kind,corners:craft.bounds.min.flatMap((_,unused)=>unused===0?[0,1,2,3,4,5,6,7].map(k=>{const p=new THREE.Vector3(...[0,1,2].map(axis=>craft.bounds[(k&(1<<axis))?'max':'min'][axis])).project(camera);return [p.x,p.y];}):[])}));});
   for(const craft of orbitalBounds)for(const [x,y] of craft.corners)assert.ok(Math.abs(x)<.98&&Math.abs(y)<.98,JSON.stringify(craft));
   assert.equal(initial.presentation.startsWith(version),true);assert.ok(initial.globe.layers.day&&initial.globe.layers.night&&initial.globe.layers.clouds&&initial.globe.layers.station&&initial.globe.layers.satellite);
   assert.equal(await page.locator('.permanent-caption').count(),0);assert.ok(initial.renderer.includes('Apple M1'));assert.ok(hero.meanFps>=55,JSON.stringify(hero));
   const layout=await page.evaluate(()=>{const ids=['.welcome-wordmark','.home-signature','#start-experience'];return ids.map(id=>{const r=document.querySelector(id).getBoundingClientRect();return{id,x:r.x,y:r.y,width:r.width,height:r.height};});});
   for(const r of layout)assert.ok(r.y>=0&&r.y+r.height<=spec.height&&r.x>=0&&r.x+r.width<=spec.width,JSON.stringify(r));
   assert.ok(layout[0].y+layout[0].height<=layout[1].y+2);assert.ok(layout[1].y+layout[1].height<layout[2].y);
   await capture('hero');
   await page.click('#start-experience');await stage('select');await background('underground');await page.waitForFunction(()=>!window.homeDiagnostics().homeHandoff&&!window.homeDiagnostics().camera.moving);
   assert.equal(await page.locator('#deploy-underground').isVisible(),true);assert.equal(await page.textContent('#environment-count'),'01 / 05');
   for(const item of data.environments){
    await background(item.id);await page.waitForFunction(()=>!window.homeDiagnostics().earthSettling);
    assert.equal(await page.locator('#deploy-underground').isVisible(),item.available);
    const d=await diag();assert.deepEqual(d.globe.sunDirection,initial.globe.sunDirection);
    assert.equal(d.globe.spacecraft.some(s=>s.visible),false);assert.ok(d.selectorViewport.width<=300&&d.selectorViewport.height<=290);
    const geometry=await page.evaluate(async item=>{const THREE=await import('three'),d=window.homeDiagnostics(),pin=d.globe.pins.find(p=>p.id===item.id);if(!pin)return null;const a=item.latitude*Math.PI/180,b=item.longitude*Math.PI/180,normal=new THREE.Vector3(Math.cos(a)*Math.cos(b),Math.sin(a),-Math.cos(a)*Math.sin(b));const expected=normal.clone().multiplyScalar(2.43).applyAxisAngle(new THREE.Vector3(0,1,0),d.globe.earthRotation).applyAxisAngle(new THREE.Vector3(0,0,1),23.44*Math.PI/180).add(new THREE.Vector3(...d.globe.rootPosition));return{normal:normal.distanceTo(new THREE.Vector3(...pin.normal)),world:expected.distanceTo(new THREE.Vector3(...pin.world))};},item);
    if(geometry){assert.ok(geometry.normal<1e-8&&geometry.world<1e-8,JSON.stringify(geometry));}
    const title=await page.locator('.environment-title').boundingBox(),panel=await page.locator('#orbit-panel').boundingBox(),controls=await page.locator('.carousel-navigation').boundingBox();assert.ok(title.x+title.width<panel.x-12);assert.ok(controls.y+controls.height<=spec.height-35);
    if(spec.name==='retina'||item.id==='underground')await capture(item.id);
    await page.click('#environment-next');
   }
   await background('underground');
   await page.evaluate(()=>{for(let i=0;i<4;i++)document.querySelector('#environment-next').click();for(let i=0;i<3;i++)document.querySelector('#environment-prev').click();});await background('glacier');await page.locator('#environment-prev').focus();await page.keyboard.press('Enter');await background('underground');
   await page.waitForTimeout(1000);const selection=await frames(page),before=await diag();assert.ok(selection.meanFps>=55,JSON.stringify(selection));
   const angle=before.globe.earthRotation;await page.waitForTimeout(250);const after=await diag();if(spec.motion==='reduce')assert.equal(after.globe.earthRotation,angle);else assert.ok(after.globe.earthRotation!==angle);
   await page.click('#sources-open');assert.equal(await page.locator('#environment-sources a').count(),5);await page.keyboard.press('Escape');
   await page.click('#deploy-underground');await stage('surface');await page.waitForTimeout(spec.motion==='reduce'?30:550);assert.equal(await page.locator('#scene-curtain').evaluate(e=>getComputedStyle(e).opacity),'0');await capture('surface');
   await page.click('#enter-mine');await stage('mine');assert.equal((await diag()).scenes.surface,false);await capture('mine');await page.click('#compare-trained');await stage('trained');await capture('trained');
   if(spec.name==='retina'){
    await page.click('#explore-world-model');await stage('learning');assert.equal(await page.evaluate(()=>document.body.dataset.learningSource),'authored');await capture('training');await page.click('#exit-world-model');await stage('trained');await page.click('#scroll-product');await page.waitForFunction(()=>window.homeDiagnostics().stage==='inside');await page.click('[data-scene="retrofit"]');await page.waitForFunction(()=>window.homeDiagnostics().kitActive);await page.waitForTimeout(1600);await capture('kit');
   }
   const cold=await page.evaluate(()=>window.coldHomeFrames);report.profiles.push({spec,readyMs,coldMaxFrameMs:Math.max(...cold),hero,selection,diagnostics:initial,layout,requests:requests.length});report.checks.push(`${spec.name}: composition, all backgrounds, default/order, coordinates, rapid input, keyboard, Sources and mine hand-off`);
   assert.ok(requests.every(url=>url.startsWith(base)||url.startsWith(`blob:${new URL(base).origin}/`)),'Local assets only');await context.close();console.log('PASS',spec.name,JSON.stringify({readyMs,hero,selection}));
  }
  // A second real composition is retained for visual judgement, not treated as approved.
  const study=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});await study.goto(base+'?home-study=instrument');await study.locator('body.ready').waitFor();await study.waitForTimeout(250);await study.screenshot({path:path.join(out,'instrument-direction.jpg'),type:'jpeg',quality:88});await study.close();
  const fallback=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});fallback.on('pageerror',e=>report.errors.push(e.message));await fallback.route('**/assets/authored/observation-satellite*.glb*',r=>r.abort());await fallback.route('**/assets/earth-clouds.jpg',r=>r.abort());await fallback.route('**/assets/environments/underground-scene.webp',r=>r.abort());await fallback.goto(base);await fallback.locator('body.ready').waitFor();await fallback.evaluate(async()=>{window.homeDiagnostics=(await import('./js/experience.js')).diagnostics;});await fallback.click('#start-experience');await fallback.waitForFunction(()=>window.homeDiagnostics().environmentBackground.state==='fallback');assert.equal(await fallback.locator('#deploy-underground').isEnabled(),true);await fallback.screenshot({path:path.join(out,'fallback.jpg'),type:'jpeg',quality:88});await fallback.close();report.checks.push('Optional spacecraft/cloud/large-photo failure keeps the experience usable with explicit image fallback');
  assert.deepEqual(report.errors,[]);
 }finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
