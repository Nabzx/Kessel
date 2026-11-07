/* Real HTTP-cache migration and transition recovery. Playwright stays outside the site. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=process.env.KESSEL_QA_DIR||'/private/tmp/kessel-transition-evidence';
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const modules=fs.readdirSync(path.join(root,'js')).filter(f=>f.endsWith('.js')).map(f=>'/js/'+f);
const styles=['/css/experience.css','/css/recorded.css','/css/realism.css','/css/hud.css','/css/home.css'];
const version=html.match(/name="kessel-presentation" content="([^"]+)"/)[1];
let legacy=true,versioned=true,fault=false,dataRequests=0,requested=[];
const server=http.createServer((req,res)=>{
 const url=new URL(req.url,'http://localhost');
 if(url.pathname==='/__reset'){legacy=true;versioned=url.searchParams.get('versioned')!=='0';fault=false;dataRequests=0;requested=[];res.end('ok');return;}
 if(url.pathname==='/__upgrade'){legacy=false;fault=url.searchParams.get('fault')==='1';res.end('ok');return;}
 if(url.pathname==='/'){
  res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','text/html');
  if(legacy){res.end(`<body><script>Promise.all(${JSON.stringify([...modules,...styles,'/data/experience.json'])}.map(p=>fetch(p).then(r=>r.text()))).then(()=>document.body.dataset.primed='yes')</script>`);return;}
  let page=html;
  if(!versioned){const start=page.indexOf('<script type="importmap">'),end=page.indexOf('</script>',start),map=JSON.parse(page.slice(page.indexOf('{',start),page.lastIndexOf('}',end)+1));for(const key of Object.keys(map.imports))if(key.startsWith('./js/'))delete map.imports[key];page=page.slice(0,start)+'<script type="importmap">'+JSON.stringify(map)+'</script>'+page.slice(end+9);page=page.replaceAll('?v='+version,'');}
  res.end(page);return;
 }
 if(url.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}
 const file=path.join(root,url.pathname);
 if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
 if(url.pathname==='/data/experience.json'){
  dataRequests++;const d=JSON.parse(fs.readFileSync(file));if(legacy)delete d.visuals;if(fault)delete d.visuals.entrance;
  res.setHeader('Cache-Control','public, max-age=3600');res.setHeader('Content-Type','application/json');res.end(JSON.stringify(d));return;
 }
 if(modules.includes(url.pathname)||styles.includes(url.pathname)){
  requested.push(url.pathname+url.search);
  res.setHeader('Cache-Control','public, max-age=3600');res.setHeader('Content-Type',url.pathname.endsWith('.js')?'text/javascript':'text/css');
  if(legacy){res.end(url.pathname.endsWith('.js')?'window.staleModuleExecuted=(window.staleModuleExecuted||0)+1;export {};':'body{--stale-style:1}');return;}
 }
 if(!res.hasHeader('Content-Type'))res.setHeader('Content-Type',({'.js':'text/javascript','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp','.json':'application/json','.gltf':'model/gltf+json','.glb':'model/gltf-binary','.bin':'application/octet-stream','.woff2':'font/woff2','.svg':'image/svg+xml'})[path.extname(file)]||'application/octet-stream');
 try{res.end(fs.readFileSync(file));}catch{res.writeHead(404);res.end();}
});
(async()=>{
 fs.mkdirSync(out,{recursive:true});await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-gpu','--use-gl=angle','--use-angle=metal']});
 const report={date:new Date().toISOString(),version,browser:browser.version(),checks:[],errors:[]};
 try{
  for(const scenario of ['unversioned-control','warm-cache-upgrade','missing-entrance-recovery']){
   const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:2,reducedMotion:'reduce'}),page=await context.newPage();
   page.on('pageerror',e=>report.errors.push(e.message));page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});
   await page.request.get(base+'/__reset?versioned='+(scenario==='unversioned-control'?'0':'1'));
   await page.goto(base);await page.locator('body[data-primed=yes]').waitFor();
   await page.request.get(base+'/__upgrade?fault='+(scenario==='missing-entrance-recovery'?'1':'0'));await page.reload();
   if(scenario==='unversioned-control'){
    await page.waitForFunction(()=>window.staleModuleExecuted===1);assert.equal(await page.locator('body.ready').count(),0);
    report.checks.push({scenario,result:'Old cached entry module executes without versioned URLs'});await context.close();continue;
   }
   await page.locator('body.ready').waitFor();assert.ok(dataRequests>=2,'Scene data must bypass the primed old JSON');
   assert.ok(!await page.evaluate(()=>window.staleModuleExecuted),'Do not execute cached old modules');
   const start=async()=>{await page.click('#start-experience');for(let i=0;i<3;i++)await page.click('#environment-next');await page.click('#deploy-underground');await page.waitForFunction(()=>document.getElementById('experience').dataset.stage==='surface');};
   const diag=()=>page.evaluate(async()=>(await import('./js/experience.js')).diagnostics());
   await start();await page.click('#enter-mine');
   if(scenario==='missing-entrance-recovery'){
    await page.locator('#enter-mine').filter({hasText:'Reload experience'}).waitFor();assert.equal((await diag()).stage,'surface');assert.equal(await page.locator('#surface-panel').isVisible(),true);assert.equal(await page.locator('#enter-mine').isEnabled(),true);
    await page.screenshot({path:path.join(out,'recoverable-surface.jpg')});
    await page.request.get(base+'/__upgrade?fault=0');await page.click('#enter-mine');await page.locator('body.ready').waitFor();await start();await page.click('#enter-mine');
   }
   await page.waitForFunction(()=>document.getElementById('experience').dataset.stage==='mine');
   let d=await diag();assert.equal(d.scenes.surface,false);assert.equal(d.scenes.mine,true);assert.equal(d.presentation,version);
   await page.click('#compare-trained');await page.waitForFunction(()=>document.getElementById('experience').dataset.stage==='trained');
   await page.waitForTimeout(700);d=await diag();assert.equal(d.comparison,true);assert.equal(d.scenes.surface,false);assert.equal(d.scenes.mine,true);assert.match(await page.locator('#value-throughput').innerText(),/132/);
   await page.screenshot({path:path.join(out,scenario+'-trained.jpg')});
   await page.click('#show-before');await page.waitForFunction(()=>document.getElementById('experience').dataset.stage==='mine');await page.click('#show-after');await page.waitForFunction(()=>document.getElementById('experience').dataset.stage==='trained');
   const active=requested.slice(modules.length+styles.length).filter(p=>p.startsWith('/js/')||p.startsWith('/css/'));
   assert.ok(active.length>0&&active.every(p=>p.endsWith('?v='+version)),JSON.stringify(active));
   report.checks.push({scenario,result:'Surface → mine → trained, reversal and correct scene visibility',diagnostics:d,dataRequests,versionedRequests:active});console.log('PASS',scenario);
   await context.close();
  }
  assert.deepEqual(report.errors,[]);console.log('PASS: cache migration and recoverable transition preparation');
 }finally{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
