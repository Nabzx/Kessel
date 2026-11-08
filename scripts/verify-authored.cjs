/* Verify that the actual presentation adopts authored assets and survives loss. */
const{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=process.env.KESSEL_QA_DIR||'/private/tmp/kessel-authored-evidence';
(async()=>{fs.mkdirSync(out,{recursive:true});const b=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});const report={date:new Date().toISOString(),browser:b.version(),checks:[],errors:[],httpErrors:[]};try{
 for(const fallback of [false,true]){
  const p=await b.newPage({viewport:{width:1440,height:900},deviceScaleFactor:2,reducedMotion:'reduce'});
  p.on('pageerror',e=>report.errors.push(e.message));if(!fallback){p.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});p.on('response',r=>{if(r.status()>=400)report.httpErrors.push(r.url());});}
  await p.addInitScript(()=>{window.assetFrames=[];let last;function tick(t){if(last)window.assetFrames.push([document.getElementById('experience')?.dataset.stage,t-last]);last=t;requestAnimationFrame(tick);}requestAnimationFrame(tick);});
  if(fallback)await p.route('**/assets/authored/geology.glb',r=>r.abort());
  const stage=s=>p.waitForFunction(s=>document.getElementById('experience').dataset.stage===s,s,{timeout:60000});const diag=()=>p.evaluate(()=>window.assetDiagnostics());
  await p.goto(process.env.KESSEL_URL||'http://127.0.0.1:8080/');await p.locator('body.ready').waitFor();await p.evaluate(async()=>{window.assetDiagnostics=(await import('./js/experience.js')).diagnostics;});await p.click('#start-experience');await p.click('#deploy-underground');await stage('surface');
  await p.waitForFunction(()=>window.assetDiagnostics().authoredAssets.includes('assets/authored/portal-yard.glb'));if(!fallback)await p.screenshot({path:path.join(out,'surface.jpg')});
  await p.click('#enter-mine');await stage('mine');await p.waitForTimeout(2000);let d=await diag();assert.equal(d.authoredAssets.includes('assets/authored/geology.glb'),!fallback);
  if(!fallback){for(const name of ['hauler-close','hauler-overview','excavator','ore-pile'])assert.ok(d.authoredAssets.includes('assets/authored/'+name+'.glb'),name);await p.screenshot({path:path.join(out,'mine.jpg')});}
  await p.click('#compare-trained');await stage('trained');
  if(!fallback){await p.click('#explore-world-model');await stage('learning');await p.waitForFunction(()=>window.assetDiagnostics().authoredAssets.includes('assets/authored/reference-loader.glb'));await p.click('#geometry-guide');const before=await diag();await p.waitForTimeout(200);assert.equal((await diag()).learning.simulatedTime,before.learning.simulatedTime);assert.ok(before.learning.bucketMouthErrorM<1e-8);await p.screenshot({path:path.join(out,'reference-rig.jpg')});await p.keyboard.press('Escape');await stage('trained');
   await p.locator('#kit-window').scrollIntoViewIfNeeded();await p.waitForFunction(()=>window.assetDiagnostics().kitActive&&window.assetDiagnostics().authoredAssets.includes('assets/authored/retrofit-kit.glb'),null,{timeout:60000});await p.waitForTimeout(3500);d=await diag();assert.ok(d.meanFps>=30);await p.screenshot({path:path.join(out,'kit.jpg')});report.checks.push({scenario:'all authored assets adopted, paused geometry, proposed kit',diagnostics:d});
  }else report.checks.push({scenario:'missing authored geology',result:'original closed cutaway remains usable through trained comparison'});
  if(!fallback){const frames=await p.evaluate(()=>window.assetFrames);report.frameTimes=Object.fromEntries([...new Set(frames.map(r=>r[0]))].filter(Boolean).map(stage=>{const values=frames.filter(r=>r[0]===stage).map(r=>r[1]).sort((a,b)=>a-b);return [stage,{frames:values.length,meanFps:1000/(values.reduce((a,b)=>a+b,0)/values.length),p95Ms:values[Math.floor(values.length*.95)],p99Ms:values[Math.floor(values.length*.99)]}];}));report.resourceTiming=await p.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/assets/authored/')).map(r=>({file:r.name.split('/').at(-1),bytes:r.encodedBodySize,durationMs:r.duration})));}
  await p.close();console.log('PASS authored',fallback?'fallback':'complete');
 }
 assert.deepEqual(report.errors,[]);assert.deepEqual(report.httpErrors,[]);
}finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await b.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
