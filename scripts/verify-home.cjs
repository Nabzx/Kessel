/* Native laptop acceptance. Playwright and Chrome are QA tools, never site dependencies. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=process.env.KESSEL_QA_DIR||'/private/tmp/kessel-home-evidence';
const base=process.env.KESSEL_URL||'http://127.0.0.1:8080/';
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/experience.json')));
const summary=frames=>{const sorted=[...frames].sort((a,b)=>a-b);return {frames:frames.length,meanFps:1000/(frames.reduce((a,b)=>a+b,0)/frames.length),p95Ms:sorted[Math.floor(sorted.length*.95)],p99Ms:sorted[Math.floor(sorted.length*.99)]};};
(async()=>{
 fs.mkdirSync(out,{recursive:true});const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});
 const report={date:new Date().toISOString(),browser:browser.version(),checks:[],errors:[],httpErrors:[]};
 try{
  for(const spec of [{name:'normal',width:1440,height:900,dpr:2,motion:'no-preference'},{name:'reduced',width:1280,height:800,dpr:1,motion:'reduce'}]){
   const p=await browser.newPage({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:spec.dpr,reducedMotion:spec.motion});
   p.on('pageerror',e=>report.errors.push(e.message));p.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});p.on('response',r=>{if(r.status()>=400)report.httpErrors.push(r.url());});
   await p.addInitScript(()=>{window.homeFrames=[];let last;const begin=performance.now();function sample(t){if(last&&t-begin<5500)window.homeFrames.push(t-last);last=t;requestAnimationFrame(sample);}requestAnimationFrame(sample);});
   const diag=()=>p.evaluate(async()=>(await import('./js/experience.js')).diagnostics());
   const stage=s=>p.waitForFunction(s=>document.getElementById('experience').dataset.stage===s,s,{timeout:60000});
   const within=async(child,parent)=>{const a=await p.locator(child).boundingBox(),b=await p.locator(parent).boundingBox();assert.ok(a&&b,child);assert.ok(a.x>=b.x-1&&a.y>=b.y-1&&a.x+a.width<=b.x+b.width+1&&a.y+a.height<=b.y+b.height+1,`${child} outside ${parent}: ${JSON.stringify({a,b})}`);};
   const screenshot=async name=>p.screenshot({path:path.join(out,spec.name+'-'+name+'.jpg'),type:'jpeg',quality:88});
   await p.goto(base);await p.locator('body.ready').waitFor();await p.evaluate(async()=>{window.homeDiagnostics=(await import('./js/experience.js')).diagnostics;});const initial=await diag();assert.ok(initial.globe.layers.day&&initial.globe.layers.night&&initial.globe.layers.clouds);
   await p.waitForTimeout(5600);const firstUse=summary(await p.evaluate(()=>window.homeFrames));await screenshot('hero');
   await p.click('#start-experience');await stage('select');await p.waitForFunction(()=>!window.homeDiagnostics().camera.moving);
   for(const item of data.environments){
    await p.waitForFunction(id=>document.getElementById('environment-image').getAttribute('src').includes(id),item.id);
    await p.waitForFunction(()=>{const image=document.getElementById('environment-image');return image.complete&&image.naturalWidth===768;});
    await p.waitForFunction(()=>!window.homeDiagnostics().earthSettling);
    await within('.environment-title h1','#selector');await within('#environment-status','#selector');await within('.carousel-navigation','#selector');
    assert.equal(await p.locator('#deploy-underground').isVisible(),item.available);if(item.available)await within('#deploy-underground','#selector');
    const d=await diag();assert.deepEqual(d.globe.sunDirection,initial.globe.sunDirection,'Root translation must not move the terminator');
    const check=await p.evaluate(async item=>{
     const THREE=await import('three'),d=(await import('./js/experience.js')).diagnostics(),pin=d.globe.pins.find(p=>p.id===item.id);if(!pin)return null;
     const lat=item.latitude*Math.PI/180,lon=item.longitude*Math.PI/180;
     const expected=new THREE.Vector3(Math.cos(lat)*Math.cos(lon),Math.sin(lat),-Math.cos(lat)*Math.sin(lon));
     const normalError=expected.distanceTo(new THREE.Vector3(...pin.normal));expected.multiplyScalar(2.43).applyAxisAngle(new THREE.Vector3(0,1,0),d.globe.earthRotation).applyAxisAngle(new THREE.Vector3(0,0,1),23.44*Math.PI/180).add(new THREE.Vector3(1.45,0,0));
     const worldError=expected.distanceTo(new THREE.Vector3(...pin.world)),camera=new THREE.PerspectiveCamera(d.camera.fov,innerWidth/innerHeight,.1,100);camera.position.fromArray(d.camera.position);camera.lookAt(0,0,0);camera.updateMatrixWorld();const projected=expected.clone().project(camera),label=document.getElementById('globe-label');
     const labelError=label.hidden?0:Math.hypot(parseFloat(label.style.left)-(projected.x*.5+.5)*innerWidth,parseFloat(label.style.top)-(-projected.y*.5+.5)*innerHeight);
     return {normalError,worldError,labelError,hidden:label.hidden};
    },item);
    if(check){assert.ok(check.normalError<1e-8&&check.worldError<1e-8&&check.labelError<1,JSON.stringify(check));}
    await screenshot(item.id);report.checks.push({scenario:spec.name,environment:item.id,geography:check});await p.click('#environment-next');
   }
   // Rapid input must leave image, marker and camera on the final selection.
   await p.locator('#environment-next').focus();await p.keyboard.press('ArrowRight');await p.keyboard.press('ArrowRight');await p.keyboard.press('ArrowRight');
   assert.equal((await diag()).environment,'underground');await p.waitForFunction(()=>!window.homeDiagnostics().earthSettling);await p.waitForTimeout(3500);
   const steady=await diag();assert.ok(steady.meanFps>=30);assert.ok(steady.pixelRatio<=1.5);assert.equal(steady.camera.moving,false);
   if(spec.motion==='reduce'){assert.ok(Math.abs(Math.sin(steady.globe.earthRotation+(30.059167+90)*Math.PI/180))<1e-6);}else{const angle=steady.globe.earthRotation;await p.waitForTimeout(200);assert.ok((await diag()).globe.earthRotation>angle,'Rotation resumes after selection settles');}
   await p.click('#sources-open');assert.match(await p.locator('#environment-sources').innerText(),/not Rutongo/);assert.equal(await p.locator('#environment-sources a').count(),5);await p.keyboard.press('Escape');
   await p.click('#deploy-underground');await stage('surface');await p.click('#enter-mine');await stage('mine');assert.deepEqual((await diag()).scenes,{earth:false,surface:false,mine:true,kit:false});await p.click('#compare-trained');await stage('trained');assert.equal((await diag()).comparison,true);await screenshot('trained');
   report.checks.push({scenario:spec.name,firstUse,steady,journey:'Earth → surface → mine → trained'});console.log('PASS',spec.name,JSON.stringify({firstUse,steadyFps:steady.meanFps}));await p.close();
  }
  const p=await browser.newPage({viewport:{width:1280,height:800}});p.on('pageerror',e=>report.errors.push(e.message));await p.goto(base);await p.locator('body.ready').waitFor();await p.evaluate(async()=>{window.homeDiagnostics=(await import('./js/experience.js')).diagnostics;});await p.click('#start-experience');await p.waitForFunction(()=>!window.homeDiagnostics().camera.moving);const interrupted=await p.evaluate(async()=>(await import('./js/experience.js')).diagnostics());assert.equal(interrupted.stage,'select');assert.deepEqual(interrupted.camera.position,[0,0,12.8]);await p.close();report.checks.push({scenario:'start interrupts arrival',result:'One camera reaches the selector destination'});
  const fallback=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});fallback.on('pageerror',e=>report.errors.push(e.message));await fallback.route('**/assets/environments/glacier.webp',r=>r.abort());await fallback.route('**/'+data.assets.globe.clouds,r=>r.abort());await fallback.goto(base);await fallback.locator('body.ready').waitFor();await fallback.click('#start-experience');await fallback.locator('#environment-credit').filter({hasText:'Preview unavailable'}).waitFor();assert.equal(await fallback.locator('#environment-icon').isVisible(),true);assert.equal(await fallback.locator('#environment-image').isVisible(),false);await fallback.click('#environment-next');await fallback.waitForFunction(()=>document.getElementById('environment-image').naturalWidth===768);assert.equal(await fallback.locator('#environment-icon').isVisible(),false);await fallback.close();report.checks.push({scenario:'missing optional cloud and photo',result:'Home remains usable, vector fallback and next photograph recover'});
  assert.deepEqual(report.errors,[]);assert.deepEqual(report.httpErrors,[]);
 }finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
 console.log('PASS: home, five environments, geographic labels, sources, motion, fallbacks and mine hand-off');
})().catch(e=>{console.error(e);process.exitCode=1;});
