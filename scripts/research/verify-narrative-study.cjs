/* Native Chrome research checks. No default walkthrough changes or human comprehension claim. */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const base=process.env.KESSEL_URL||'http://127.0.0.1:8080/';
const out=path.resolve(__dirname,'../../docs/phase-11/narrative-study/evidence');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});
 const report={browser:browser.version(),created:new Date().toISOString(),profiles:[],errors:[],baseline:{}};
 try{
  const baseline=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  baseline.on('pageerror',e=>report.errors.push(e.message));await baseline.goto(base);await baseline.locator('body.ready').waitFor({timeout:60000});
  await baseline.evaluate(async()=>{window.audit=(await import('./js/experience.js')).diagnostics;await document.fonts.ready;});
  for(const id of ['earth','environments','surface','training']){
   await baseline.click(`[data-scene="${id}"]`);await baseline.waitForFunction(id=>window.audit().chapter===id&&!window.audit().chapterBusy,id,{timeout:60000});await baseline.waitForTimeout(600);
   await baseline.screenshot({path:path.join(out,id+'.jpg'),type:'jpeg',quality:86});
   report.baseline[id]={diagnostics:await baseline.evaluate(()=>window.audit()),headings:await baseline.locator('h1:visible').allTextContents()};
  }
  await baseline.close();
  for(const spec of [{name:'laptop',width:1440,height:900,motion:'no-preference'},{name:'compact',width:1365,height:768,motion:'reduce'},{name:'narrow',width:390,height:844,motion:'reduce'}]){
   const page=await browser.newPage({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:1,reducedMotion:spec.motion}),entry={spec,frames:[],checks:[]};
   page.on('pageerror',e=>report.errors.push(e.message));page.on('response',r=>{if(r.status()>=400)report.errors.push(`${r.status()} ${r.url()}`);});
   await page.goto(base+'docs/phase-11/narrative-study/');await page.waitForFunction(()=>document.body.dataset.ready==='true',{},{timeout:60000});await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(300);
   const diag=()=>page.evaluate(()=>window.narrativeStudy.diagnostics());
   assert.equal((await diag()).playing,false);assert.equal((await diag()).step,'task');
   for(const step of ['task','observe','predict','learn','retrofit']){
    await page.evaluate(s=>window.narrativeStudy.step(s),step);await page.waitForTimeout(150);
    let d=await diag();assert.equal(d.step,step);assert.equal(d.lens,'job');
    if(spec.width>700){
     const frames=await page.evaluate(()=>window.narrativeStudy.auditFrames()),s=d.fit.safe;
     assert(frames.every(f=>f.left>=s.left-1&&f.right<=s.right+1&&f.top>=s.top-1&&f.bottom<=s.bottom+1),`pose clipped: ${spec.name}/${step}`);
     entry.frames.push({step,checkedPoses:frames.length,fit:d.fit,source:d.source});
     assert(await page.locator('#story').evaluate(e=>e.scrollHeight<=e.clientHeight+1),`primary story scrolls: ${spec.name}/${step}`);
    }
    if(step==='learn'){assert.match(await page.locator('#source').innerText(),/New recording/);assert.match(await page.locator('#story-copy').innerText(),/No delivery/);assert.equal((await diag()).source,'curriculum-followup-v1');}
    if(step==='predict'){assert.equal(await page.locator('#seek').isDisabled(),true);assert.match(await page.locator('#forecast-readout').innerText(),/Magnified/);if(spec.width>700){const anchor=(await diag()).elapsed;await page.selectOption('#horizon','1');assert.equal((await diag()).elapsed,anchor);await page.selectOption('#horizon','4');}}
    if(spec.name==='laptop')await page.screenshot({path:path.join(out,'proposed-'+step+'.jpg'),type:'jpeg',quality:88});
   }
   await page.evaluate(()=>window.narrativeStudy.step('observe'));
   if(spec.width>700){const pose=(await diag()).pose;await page.click('[data-lens="contact"]');assert.deepEqual((await diag()).pose,pose);assert.match(await page.locator('#detail-note').innerText(),/exclude the receiver/);if(spec.name==='laptop')await page.screenshot({path:path.join(out,'contact-detail.jpg'),type:'jpeg',quality:88});}
   await page.evaluate(()=>window.narrativeStudy.step('task'));const before=(await diag()).elapsed;await page.click('#play');await page.waitForTimeout(350);await page.click('#play');assert((await diag()).elapsed>before);
   const held=(await diag()).elapsed;await page.waitForTimeout(150);assert.equal((await diag()).elapsed,held);
   await page.click('[data-route="context"]');assert.equal(await page.locator('#steps button').count(),8);assert.equal((await diag()).step,'earth');await page.click('[data-route="mine"]');assert.equal(await page.locator('#steps button').count(),5);
   await page.locator('#next').focus();await page.keyboard.press('Enter');assert.equal((await diag()).step,'observe');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   if(spec.name!=='laptop')await page.screenshot({path:path.join(out,spec.name+'.jpg'),type:'jpeg',quality:88});
   entry.checks=['Paused initial entry','Five core beats','Explicit different-run hand-off','Frozen forecast anchor','Actual recording play/pause','Both route alternatives','Keyboard activation','No horizontal overflow'];entry.diagnostics=await diag();report.profiles.push(entry);await page.close();
  }
  const failed=await browser.newPage();await failed.route('**/data/experiments/reference-v1.json',r=>r.fulfill({status:503,body:'Unavailable'}));await failed.goto(base+'docs/phase-11/narrative-study/');await failed.locator('#error:visible').waitFor();assert(await failed.locator('#retry').isVisible());await failed.unroute('**/data/experiments/reference-v1.json');await failed.click('#retry');await failed.waitForFunction(()=>document.body.dataset.ready==='true',{},{timeout:60000});report.recovery=['Missing record shows a useful failure','Retry reloads valid source data'];await failed.close();
 }finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();}
 assert.deepEqual(report.errors,[]);console.log('PASS: narrative route comparison, recorded-source boundaries, full-episode camera framing and controls');
})().catch(error=>{console.error(error);process.exitCode=1;});
