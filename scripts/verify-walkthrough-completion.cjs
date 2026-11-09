/* Native Mac Chrome: finite training, resumed chapters, media and accepted kit. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=process.env.KESSEL_QA_DIR||'/private/tmp/kessel-chapter-qa',base=process.env.KESSEL_URL||'http://127.0.0.1:8080/';fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});
 const report={browser:browser.version(),date:new Date().toISOString(),profiles:[],errors:[]};
 try{
 for(const spec of [{name:'retina',width:1440,height:900,dpr:2,motion:'no-preference'},{name:'compact',width:1365,height:768,dpr:1,motion:'no-preference'},{name:'reduced',width:1280,height:800,dpr:1,motion:'reduce'}]){
  const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:spec.dpr,reducedMotion:spec.motion,recordVideo:process.env.KESSEL_QA_VIDEO==='1'&&spec.name==='retina'?{dir:out,size:{width:1280,height:800}}:undefined}),page=await context.newPage(),row={spec,frames:[],checks:[]};
  page.on('pageerror',e=>report.errors.push(e.message));page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text())});page.on('response',r=>{if(r.status()>=400)report.errors.push(r.status()+' '+r.url())});
  const diag=()=>page.evaluate(()=>window.audit());
  const shot=async name=>{await page.waitForFunction(()=>!document.getElementById('scene-curtain').classList.contains('covered')&&Number(getComputedStyle(document.getElementById('scene-curtain')).opacity)<.01);return page.screenshot({path:path.join(out,spec.name+'-'+name+'.jpg'),type:'jpeg',quality:87});};
  const chapter=async id=>{await page.click(`[data-scene="${id}"]`);await page.waitForFunction(id=>document.body.dataset.chapter===id&&!window.audit().chapterBusy,id,{timeout:45000});};
  const sample=async name=>{await page.waitForTimeout(3100);const d=await diag();row.frames.push({name,meanFps:d.meanFps,p95:d.p95FrameMs,p99:d.p99FrameMs,drawCalls:d.drawCalls,triangles:d.triangles,renderer:d.renderer});await shot(name);};
  await page.goto(base);await page.locator('body.ready').waitFor({timeout:45000});await page.evaluate(async()=>window.audit=(await import('./js/experience.js')).diagnostics);await sample('earth');
  assert.equal(await page.locator('[data-scene]').count(),7);await page.click('#start-experience');await page.waitForFunction(()=>window.audit().stage==='select');assert.equal((await diag()).environment,'underground');await shot('environments');
  // Film playback is checked after every output exists, including its poster.
  await page.click('#deploy-underground');await page.waitForFunction(()=>window.audit().stage==='surface'&&!window.audit().chapterBusy);await page.waitForTimeout(1000);await shot('surface');let film=(await diag()).surfaceFilm;assert.equal(film.failed,false);
  const button=page.locator('#enter-mine'),style=await button.evaluate(e=>({radius:parseFloat(getComputedStyle(e).borderRadius),colour:getComputedStyle(e).backgroundColor}));assert(style.radius>20);await button.hover();await page.waitForTimeout(250);assert.notEqual(await button.evaluate(e=>getComputedStyle(e).backgroundColor),style.colour);
  if(spec.motion==='reduce')assert.equal(film.paused,true);else{const t=film.time;await page.waitForTimeout(350);assert((await diag()).surfaceFilm.time>t);await page.click('#surface-motion');assert.equal((await diag()).surfaceFilm.paused,true);}
  const filmTime=(await diag()).surfaceFilm.time;
  await page.click('#enter-mine');await page.waitForFunction(()=>window.audit().stage==='mine'&&!window.audit().chapterBusy);await sample('mine');
  await page.click('#compare-trained');await page.waitForFunction(()=>window.audit().stage==='trained');await shot('trained');
  await page.click('#explore-world-model');await page.waitForFunction(()=>window.audit().stage==='learning'&&!window.audit().chapterBusy);
  assert.equal(await page.locator('#learning-source').count(),0);assert.equal(await page.locator('#product-world-model').count(),0);assert.equal((await diag()).learning.learnedPolicyResult,false);
  if(spec.motion==='reduce'){assert.equal((await diag()).learning.playing,false);await page.click('#pause-training');}
  await page.waitForTimeout(3000);await page.click('#pause-training');const paused=(await diag()).learning;
  await chapter('inside');assert.equal(await page.evaluate(()=>scrollY),0);await page.mouse.wheel(0,900);assert.equal(await page.evaluate(()=>scrollY),0);await shot('inside');
  for(let i=0;i<5;i++){
   await page.click(`[data-chapter="${i}"]`);await page.waitForFunction(()=>document.getElementById('technical-dialog').open);await page.waitForTimeout(400);await page.click('#technical-next');await page.keyboard.press('Escape');
   await page.click(`[data-chapter="${i}"]`);assert.match(await page.locator('#technical-counter').innerText(),/02/);await page.keyboard.press('Escape');
  }
  await chapter('training');let resumed=(await diag()).learning;assert.equal(resumed.elapsed,paused.elapsed);assert.equal(resumed.playing,false);
  await page.click('#pause-training');await page.waitForFunction(()=>window.audit().learning?.completed,null,{timeout:65000});const final=(await diag()).learning;
  assert.equal(final.jobs,3);assert.equal(final.sourceKg,1000);assert.equal(final.deliveredKg,2000);assert.equal(final.payloadKg,0);assert.equal(final.inflightKg,0);assert.match(await page.locator('#task-delivered').innerText(),/6.00/);assert.equal(final.playing,false);await sample('training-complete');
  const pose=final.pose;await page.waitForTimeout(300);assert.deepEqual((await diag()).learning.pose,pose);const f=final.frame;assert(f.projected.left>=f.safe.left-1&&f.projected.right<=f.safe.right+1&&f.projected.top>=f.safe.top-1&&f.projected.bottom<=f.safe.bottom+1);
  await page.click('#replay-training');await page.waitForTimeout(100);assert((await diag()).learning.elapsed<.5);await page.click('#pause-training');
  await chapter('mine');assert.equal((await diag()).comparison,true);assert.equal((await diag()).stage,'trained');await page.click('#scroll-product');await page.waitForFunction(()=>window.audit().chapter==='inside');
  await chapter('retrofit');assert.equal((await diag()).kit.assembled,true);await page.click('#assemble-kit');await page.waitForTimeout(spec.motion==='reduce'?200:3600);assert((await diag()).kit.amount>.98);await sample('retrofit-open');const amount=(await diag()).kit.amount;
  await chapter('surface');await page.waitForTimeout(250);assert.equal((await diag()).surfaceFilm.paused,true);assert(Math.abs((await diag()).surfaceFilm.time-filmTime)<.2);
  await chapter('retrofit');assert.equal((await diag()).kit.amount,amount);
  // Latest input wins, including a destination that still needs preparing.
  await page.evaluate(()=>{for(const id of ['earth','mine','training','environments'])document.querySelector(`[data-scene="${id}"]`).click();});await page.waitForFunction(()=>window.audit().chapter==='environments'&&!window.audit().chapterBusy);assert.equal((await diag()).scenes.mine,false);
  await page.locator('[data-scene="earth"]').focus();await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>document.activeElement.dataset.scene),'environments');await page.keyboard.press('End');assert.equal(await page.evaluate(()=>document.activeElement.dataset.scene),'retrofit');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollHeight>innerHeight),false);
  row.checks=['All seven direct chapters','Rounded green entry and larger product action','Paused film resumes','Baseline/trained state retained','Training pause and resume','Three jobs and 6 t endpoint','Replay resets','Five technical chapters resume','Kit assembly resumes','Latest navigation wins','Keyboard chapter rail','No document scrolling'];
  row.final=final;report.profiles.push(row);await context.close();console.log('PASS',spec.name);
 }
 // Explicit recovery: a missing training trace keeps the old chapter usable.
 const page=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});await page.route('**/data/training-demonstration.json',r=>r.fulfill({status:503,body:'Unavailable'}));await page.goto(base);await page.locator('body.ready').waitFor();await page.evaluate(async()=>window.audit=(await import('./js/experience.js')).diagnostics);await page.click('[data-scene="training"]');await page.waitForFunction(()=>!window.audit().chapterBusy);assert.equal((await page.evaluate(()=>window.audit())).stage,'welcome');await page.unroute('**/data/training-demonstration.json');await page.click('[data-scene="training"]');await page.waitForFunction(()=>window.audit().stage==='learning');await page.close();
 report.recovery=['Missing destination retains the current chapter','Retry prepares the destination'];
 }finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
 assert.deepEqual(report.errors,[]);assert(report.profiles.every(p=>p.frames.every(f=>f.meanFps>=55&&f.p95<=20)),JSON.stringify(report.profiles.map(p=>p.frames)));
 console.log('PASS: resumable chapters, finite three-job training, local film, contact audits, technical chapters and assembly');
})().catch(e=>{console.error(e);process.exitCode=1});
