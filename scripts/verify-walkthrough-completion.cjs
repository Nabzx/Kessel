/* Native Chrome regression for the observed occlusion, guided endpoint and chapters. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=process.env.KESSEL_QA_DIR||'/private/tmp/kessel-completion-qa',base=process.env.KESSEL_URL||'http://127.0.0.1:8080/';fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});
 const report={browser:browser.version(),date:new Date().toISOString(),errors:[],profiles:[]};
 try{for(const spec of [{name:'retina',width:1440,height:900,dpr:2,motion:'no-preference'},{name:'compact',width:1365,height:768,dpr:1,motion:'no-preference'},{name:'reduced',width:1280,height:800,dpr:1,motion:'reduce'}]){
  const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:spec.dpr,reducedMotion:spec.motion,recordVideo:process.env.KESSEL_QA_VIDEO==='1'&&spec.name==='retina'?{dir:out,size:{width:1280,height:800}}:undefined});const page=await context.newPage(),row={spec,frames:[],sources:[]};
  page.on('pageerror',e=>report.errors.push(e.message));page.on('response',r=>{if(r.status()>=400)report.errors.push(r.status()+' '+r.url())});page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text())});
  const diag=()=>page.evaluate(()=>window.audit());
  const stage=s=>page.waitForFunction(s=>window.audit().stage===s,s,{timeout:60000});
  const shot=async name=>{await page.waitForTimeout(350);await page.screenshot({path:path.join(out,spec.name+'-'+name+'.jpg'),quality:88});};
  const sample=async name=>{await page.waitForTimeout(5500);const d=await diag();row.frames.push({name,meanFps:d.meanFps,p95:d.p95FrameMs,p99:d.p99FrameMs,drawCalls:d.drawCalls,triangles:d.triangles,renderer:d.renderer});await shot(name);};
  await page.goto(base);await page.locator('body.ready').waitFor({timeout:45000});await page.evaluate(async()=>window.audit=(await import('./js/experience.js')).diagnostics);await sample('home');
  await page.click('#start-experience');await stage('select');await shot('selector');await page.click('#deploy-underground');await stage('surface');await sample('surface');
  await page.click('#enter-mine');await stage('mine');await sample('mine');assert.equal((await diag()).scenes.surface,false);
  await page.click('#compare-trained');await stage('trained');await shot('trained');await page.click('#explore-world-model');await stage('learning');assert.equal(await page.evaluate(()=>document.body.dataset.learningSource),'reference');
  if(spec.motion==='reduce')await page.click('#pause-training');
  await page.waitForFunction(()=>window.audit().learning.paused&&window.audit().learning.material?.deliveredKg>2000,null,{timeout:25000});await sample('guided-complete');
  for(const source of ['recorded_synthetic','reference','curriculum']){
   await page.selectOption('#learning-source',source);await page.waitForFunction(s=>document.body.dataset.learningSource===s,source,{timeout:45000});
   await page.locator('#replay-inspector').evaluate(e=>e.open=true);await page.locator('.replay-details').evaluate(e=>e.open=true);
   for(let k=0;k<3;k++){
    await page.locator(`[data-checkpoint="${k}"]`).click();
    for(const fraction of [0,.25,.5,.75,1]){
     await page.locator('#replay-scrub').evaluate((e,f)=>{e.value=Number(e.max)*f;e.dispatchEvent(new Event('input',{bubbles:true}));},fraction);
     await page.waitForTimeout(25);const d=await diag(),f=d.learning.framing;
     assert.ok(f.projected.left>=f.safe.left-1&&f.projected.right<=f.safe.right+1&&f.projected.top>=f.safe.top-1&&f.projected.bottom<=f.safe.bottom+1,JSON.stringify(f));assert.ok(d.learning.bucketMouthErrorM<1e-6);assert.ok(Math.abs(d.learning.material.residualKg)<1e-6);
    }
   }
   await page.locator('#replay-inspector').evaluate(e=>e.open=false);await page.locator('.replay-details').evaluate(e=>e.open=false);await shot(source);row.sources.push({source,learning:(await diag()).learning});
  }
  await page.locator('#replay-inspector').evaluate(e=>e.open=true);await page.click('#forecast-tab');for(const horizon of ['1','2','4','8']){await page.selectOption('#forecast-horizon',horizon);await page.click('#inspect-forecast');await page.waitForTimeout(80);assert.equal((await diag()).learning.horizon,Number(horizon));}await shot('forecast');
  await page.selectOption('#learning-source','authored');await page.waitForFunction(()=>document.body.dataset.learningSource==='authored');await page.waitForTimeout(150);assert.match(await page.locator('#task-summary').innerText(),/Authored/);
  await page.click('#exit-world-model');await stage('trained');await page.click('#scroll-product');await page.locator('[data-chapter="0"]').scrollIntoViewIfNeeded();
  for(let i=0;i<5;i++){
   await page.click(`[data-chapter="${i}"]`);await page.waitForFunction(()=>document.getElementById('technical-dialog').open&&document.getElementById('technical-source').textContent!=='Records unavailable. Try again.');await page.waitForTimeout(600);await shot('chapter-'+i);await page.click('#technical-next');await page.click('#technical-next');await page.keyboard.press('Escape');assert.equal(await page.locator('#technical-dialog').evaluate(e=>e.open),false);
  }
  await page.locator('#assemble-kit').scrollIntoViewIfNeeded();await page.waitForFunction(()=>window.audit().kitActive&&window.audit().kit);await sample('kit-assembled');assert.equal((await diag()).kit.assembled,true);await page.click('#assemble-kit');await page.waitForTimeout(spec.motion==='reduce'?150:3600);await sample('kit-open');assert.ok((await diag()).kit.amount>.98);
  assert.ok(row.frames.every(f=>f.meanFps>=55&&f.p95<=20),JSON.stringify(row.frames));
  report.profiles.push(row);await context.close();console.log('PASS',spec.name);
 }
 const recovery=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});
 recovery.on('pageerror',e=>report.errors.push(e.message));
 await recovery.route('**/assets/materials/surface-sky.webp',r=>r.abort());
 await recovery.goto(base);await recovery.locator('body.ready').waitFor();await recovery.evaluate(async()=>window.audit=(await import('./js/experience.js')).diagnostics);
 const rs=s=>recovery.waitForFunction(s=>window.audit().stage===s,s,{timeout:60000});
 await recovery.click('#start-experience');await rs('select');await recovery.click('#deploy-underground');await recovery.keyboard.press('Escape');await rs('select');assert.equal(await recovery.locator('#flight-label').isVisible(),false);
 await recovery.click('#deploy-underground');await rs('surface');await recovery.click('#enter-mine');await rs('mine');await recovery.click('#compare-trained');await rs('trained');
 await recovery.route('**/data/experiments/reference-v1.json',r=>r.abort());await recovery.click('#explore-world-model');await recovery.locator('#experiment-error').waitFor({state:'visible'});assert.equal((await recovery.evaluate(()=>window.audit())).stage,'trained');
 await recovery.unroute('**/data/experiments/reference-v1.json');await recovery.click('#retry-recorded');await rs('learning');assert.equal(await recovery.evaluate(()=>document.body.dataset.learningSource),'reference');
 await recovery.locator('#replay-inspector').evaluate(e=>e.open=true);await recovery.locator('.replay-details').evaluate(e=>e.open=true);await recovery.locator('[data-checkpoint="2"]').click();await recovery.locator('#replay-scrub').evaluate(e=>{e.value=e.max;e.dispatchEvent(new Event('input',{bubbles:true}))});await recovery.waitForTimeout(100);assert.match(await recovery.locator('#checkpoint-outcome').innerText(),/Stuck/);
 await recovery.selectOption('#learning-source','recorded_synthetic');await recovery.selectOption('#learning-source','curriculum');await recovery.waitForFunction(()=>document.body.dataset.learningSource==='curriculum');assert.equal((await recovery.evaluate(()=>window.audit())).learning.runId,'curriculum-followup-v1');
 report.recovery=['Cancelled arrival restores selection','Missing sky keeps the authored atmosphere','Missing reference stays an explicit error','Retry restores reference','Failed reference remains failed','Latest source selection wins'];await recovery.close();
 }finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
 assert.deepEqual(report.errors,[]);console.log('PASS: guided delivery, full visual envelope, ledger, all sources, forecasts, chapters and assembly');
})().catch(e=>{console.error(e);process.exitCode=1});
