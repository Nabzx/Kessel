/* Laptop layout and instrument tabs. Local Playwright is not a runtime dependency. */
const{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=process.env.KESSEL_QA_DIR||'/private/tmp/kessel-hud-evidence';
(async()=>{fs.mkdirSync(out,{recursive:true});const b=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});const report={date:new Date().toISOString(),browser:b.version(),checks:[],errors:[],httpErrors:[]};
try{for(const size of [{width:1280,height:800,dpr:1},{width:1440,height:900,dpr:2}]){
const p=await b.newPage({viewport:{width:size.width,height:size.height},deviceScaleFactor:size.dpr,reducedMotion:'reduce'});
p.on('pageerror',e=>report.errors.push(e.message));p.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});p.on('response',r=>{if(r.status()>=400)report.httpErrors.push(r.url());});
const stage=s=>p.waitForFunction(s=>document.getElementById('experience').dataset.stage===s,s,{timeout:60000});
const within=async(child,parent)=>{const a=await p.locator(child).boundingBox(),b=await p.locator(parent).boundingBox();assert.ok(a&&b,child);assert.ok(a.x>=b.x-1&&a.y>=b.y-1&&a.x+a.width<=b.x+b.width+1&&a.y+a.height<=b.y+b.height+1,`${child} must stay inside ${parent}: ${JSON.stringify({a,b})}`);};
const capture=async name=>{await p.waitForTimeout(700);await p.screenshot({path:path.join(out,size.width+'-'+name+'.jpg'),type:'jpeg',quality:88});};
await p.goto(process.env.KESSEL_URL||'http://127.0.0.1:8080/');await p.locator('body.ready').waitFor();await p.click('#start-experience');await p.click('#deploy-underground');await stage('surface');await p.click('#enter-mine');await stage('mine');await capture('mine');
const font=await p.locator('.metric>span:first-child').first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize));assert.ok(font>=10);await within('#compare-trained','#operations');
await p.click('#compare-trained');await stage('trained');await within('#explore-world-model','#operations');await within('#scroll-product','#operations');await capture('trained');
assert.match(await p.locator('#local-status').innerText(),/No GPS/);assert.match(await p.locator('#operations').innerText(),/Illustrative operating scenario/);
await p.click('#explore-world-model');await stage('learning');await within('#replay-training','.learning-panel');await within('#pause-training','.learning-panel');await within('#replay-pace','.learning-panel');await within('#checkpoint-outcome','.learning-panel');await capture('policy');
const before=await p.evaluate(async()=>(await import('./js/experience.js')).diagnostics().learning);
await p.locator('#policy-tab').focus();await p.keyboard.press('ArrowRight');assert.equal(await p.locator('#forecast-tab').getAttribute('aria-selected'),'true');assert.equal(await p.locator('#forecast-instruments').isVisible(),true);assert.equal(await p.locator('#policy-instruments').isVisible(),false);
await within('#forecast-horizon','#forecast-instruments');await within('#pause-training','.learning-panel');await capture('forecast');
const after=await p.evaluate(async()=>(await import('./js/experience.js')).diagnostics().learning);assert.equal(after.simulatedTime,before.simulatedTime,'Instrument tabs must not seek the recorded clock');assert.equal(after.checkpoint,before.checkpoint);
await p.keyboard.press('Home');assert.equal(await p.locator('#policy-tab').getAttribute('aria-selected'),'true');
await p.selectOption('#learning-source','authored');await p.waitForFunction(()=>document.body.dataset.learningSource==='authored');assert.equal(await p.locator('.instrument-tabs').isVisible(),false);assert.equal(await p.locator('#policy-instruments').isVisible(),true);await within('#pause-training','.learning-panel');await capture('concept');
await p.selectOption('#learning-source','recorded_synthetic');await p.waitForFunction(()=>document.body.dataset.learningSource==='recorded_synthetic');assert.equal(await p.locator('#policy-tab').getAttribute('aria-selected'),'true');
const overflow=await p.locator('.learning-panel').evaluate(e=>({scrollWidth:e.scrollWidth,clientWidth:e.clientWidth}));assert.ok(overflow.scrollWidth<=overflow.clientWidth+1);
await p.keyboard.press('Escape');await stage('trained');await p.waitForTimeout(3200);const d=await p.evaluate(async()=>(await import('./js/experience.js')).diagnostics());assert.equal(d.scenes.surface,false);assert.equal(d.scenes.mine,true);assert.ok(d.meanFps>=30);report.checks.push({size,font,overflow,diagnostics:d});await p.close();console.log('PASS HUD',size.width,size.height);
}assert.deepEqual(report.errors,[]);assert.deepEqual(report.httpErrors,[]);}finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await b.close();}
console.log('PASS: laptop HUD, source-aware instrument tabs, keyboard access, unchanged replay time and scene visibility');})().catch(e=>{console.error(e);process.exitCode=1;});
