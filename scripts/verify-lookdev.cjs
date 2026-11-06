/* Native browser evidence for the isolated Phase 11 material study. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const out = process.env.KESSEL_QA_DIR || "/private/tmp/kessel-lookdev-evidence";
const url = process.env.KESSEL_URL || "http://127.0.0.1:8094/docs/phase-11/lookdev/";
fs.mkdirSync(out, { recursive:true });
(async () => {
  const browser = await chromium.launch({channel:"chrome",headless:true,args:["--enable-gpu","--use-gl=angle","--use-angle=metal"]});
  const report = {date:new Date().toISOString(),browser:browser.version(),url,samples:[],errors:[],httpErrors:[],checks:[]};
  try {
    const page = await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:2});
    page.on("pageerror",(error)=>report.errors.push(error.message));
    page.on("response",(response)=>{if(response.status()>=400)report.httpErrors.push([response.status(),response.url()]);});
    await page.goto(url,{waitUntil:"domcontentloaded"});
    await page.locator("body.ready").waitFor({timeout:45000});
    const snapshot = async (name) => {
      await page.waitForTimeout(4300);
      const data = await page.evaluate(()=>window.studyDiagnostics());
      report.samples.push({name,...data});
      await page.screenshot({path:path.join(out,name+".jpg"),type:"jpeg",quality:88});
      assert.equal(data.sourceMode,"visual_reference");
      assert.ok(data.meanFps>=30,`${name}: ${data.meanFps} fps`);
      assert.ok(data.pixelRatio<=1.5);
      console.log(name,data.meanFps.toFixed(1)+" fps");
    };
    await page.click("#pause");
    assert.equal(await page.getAttribute("#pause","aria-pressed"),"true");
    await snapshot("rock-face-overhead");
    await page.click('[data-material="dark_rock_02"]');
    await snapshot("dark-rock-overhead");
    await page.click('[data-material="baseline"]');
    await snapshot("baseline-overhead");
    assert.equal(await page.textContent("#resolution"),"512 px");
    await page.click('[data-material="rock_face_03"]');
    await page.click("#inspect");
    await snapshot("rock-face-close");
    assert.equal((await page.evaluate(()=>window.studyDiagnostics())).transition,false);
    await page.click('[data-material="dark_rock_02"]');
    await snapshot("dark-rock-close");
    await page.click('[data-light="mine"]');
    await snapshot("mine-lighting");
    report.checks.push("Three materials, matched comparison repeat, two lighting modes and continuous camera move");
    await page.click('[data-view="scan"]');
    await page.waitForFunction(()=>window.studyDiagnostics().view==="scan");
    await snapshot("scan-reference");
    assert.equal((await page.evaluate(()=>window.studyDiagnostics())).physicalUnits,null);
    assert.equal(await page.locator('[data-material="baseline"]').isDisabled(),true);
    assert.match(await page.textContent("#scene-caption"),/Slovenia/);
    report.checks.push("Verified scan buffer; unknown units retained; untextured reference and source credit");
    await page.click('[data-view="cutaway"]');
    await page.waitForFunction(()=>window.studyDiagnostics().view==="cutaway");
    assert.equal(await page.getAttribute('[data-material="dark_rock_02"]',"aria-pressed"),"true");
    await page.click("#sources-open");
    assert.equal(await page.locator("#sources-dialog").isVisible(),true);
    await page.keyboard.press("Escape");
    assert.equal(await page.locator("#sources-dialog").isVisible(),false);
    for (const viewport of [{width:1280,height:800},{width:1440,height:900}]) {
      await page.setViewportSize(viewport); await page.waitForTimeout(350);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    }
    report.checks.push("View restoration, keyboard dialog dismissal and laptop layout");
    const reduced = await browser.newPage({viewport:{width:1280,height:800},reducedMotion:"reduce"});
    await reduced.goto(url);
    await reduced.locator("body.ready").waitFor({timeout:45000});
    assert.equal((await reduced.evaluate(()=>window.studyDiagnostics())).paused,true);
    await reduced.click("#inspect");
    await reduced.waitForTimeout(100);
    assert.equal((await reduced.evaluate(()=>window.studyDiagnostics())).transition,false);
    report.checks.push("Reduced motion starts paused and camera changes settle immediately");
    await reduced.close();
    assert.deepEqual(report.errors,[]); assert.deepEqual(report.httpErrors,[]);
    console.log("PASS",report.checks.length,"look-development groups");
  } finally {
    fs.writeFileSync(path.join(out,"report.json"),JSON.stringify(report,null,2));
    await browser.close();
  }
})().catch((error)=>{console.error(error);process.exitCode=1;});
