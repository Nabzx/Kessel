/* Native laptop visual acceptance. Local Playwright is not published. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const out = process.env.KESSEL_QA_DIR || '/private/tmp/kessel-visual-acceptance';
const base = process.env.KESSEL_URL || 'http://127.0.0.1:8080/';
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--enable-gpu', '--use-gl=angle', '--use-angle=metal'] });
  const report = { date: new Date().toISOString(), browser: browser.version(), samples: [], checks: [], errors: [], httpErrors: [], scope: 'Visual presentation and authored journey. Recorded-demo behaviour deferred by maintainer.' };
  try {
    for (const scenario of [{ name: 'retina', width: 1440, height: 900, dpr: 2, reduced: false }, { name: 'compact-reduced', width: 1280, height: 800, dpr: 1, reduced: true }]) {
      const page = await browser.newPage({ viewport: { width: scenario.width, height: scenario.height }, deviceScaleFactor: scenario.dpr, reducedMotion: scenario.reduced ? 'reduce' : 'no-preference' });
      page.on('pageerror', error => report.errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') report.errors.push(message.text()); });
      page.on('response', response => { if (response.status() >= 400) report.httpErrors.push([response.status(), response.url()]); });
      const stage = expected => page.waitForFunction(s => document.getElementById('experience').dataset.stage === s, expected, { timeout: 60000 });
      const capture = async (name, warm = true) => {
        if (warm) await page.waitForTimeout(3200);
        const diagnostic = await page.evaluate(async () => (await import('./js/experience.js')).diagnostics());
        assert.ok(diagnostic.meanFps >= 30, `${scenario.name}/${name}: ${diagnostic.meanFps} fps`);
        assert.ok(diagnostic.pixelRatio <= 1.5);
        report.samples.push({ scenario: scenario.name, name, ...diagnostic });
        await page.screenshot({ path: path.join(out, `${scenario.name}-${name}.jpg`), type: 'jpeg', quality: 88 });
        console.log(scenario.name, name, diagnostic.meanFps.toFixed(1), 'fps', diagnostic.drawCalls, 'calls');
      };
      await page.goto(base); await page.locator('body.ready').waitFor();
      await capture('hero');
      assert.equal(await page.locator('#journey').isVisible(), false);
      const contrast = await page.locator('.welcome-wordmark').evaluate(el => getComputedStyle(el).filter);
      assert.ok(contrast.includes('invert(1)'), 'Wordmark must retain its light fill');
      const geometry = await page.evaluate(async () => {
        const { rockGeometry } = await import('./js/geology.js');
        const { createGlobe } = await import('./js/globe-stage.js');
        const THREE = await import('three'), data = await (await fetch('data/experience.json')).json();
        let triangles = 0;
        for (const [i, spec] of [data.mine.base, ...data.mine.pillars, ...data.mine.rims].entries()) {
          const g = rockGeometry(spec.size, 31071 + i, 1.3), p = g.attributes.position, edges = new Map();
          const key = j => [p.getX(j), p.getY(j), p.getZ(j)].map(v => v.toFixed(5)).join(',');
          for (let j = 0; j < p.count; j += 3) for (const [a,b] of [[j,j+1],[j+1,j+2],[j+2,j]]) {
            const k = [key(a),key(b)].sort().join('/'); edges.set(k,(edges.get(k)||0)+1);
          }
          if ([...edges.values()].some(n => n !== 2)) throw new Error('Uncapped or non-manifold cutaway');
          for (let j = 0; j < p.count; j++) for (const [axis,size] of spec.size.entries()) if (Math.abs(p.array[j*3+axis]) > size/2+.001) throw new Error('Rock intrudes beyond clearance bounds');
          triangles += p.count/3; g.dispose();
        }
        const scene = new THREE.Scene(), globe = createGlobe(scene,data);
        if (globe.normal(data.location.latitude,data.location.longitude).y >= 0) throw new Error('Rwanda moved into northern hemisphere');
        if (globe.normal(90,0).y < .99) throw new Error('North axis inverted');
        return { triangles, budget: data.visuals.budgets.rock_triangles_max };
      });
      assert.ok(geometry.triangles <= geometry.budget); report.checks.push({ scenario: scenario.name, closedShell: geometry });
      await page.locator('#start-experience').focus(); await page.keyboard.press('Enter'); await stage('select');
      for (let i=0;i<3;i++) await page.click('#environment-next'); await capture('selector');
      await page.click('#deploy-underground'); await stage('surface'); await capture('surface');
      await page.click('#enter-mine'); await stage('mine'); await capture('mine');
      const bounds = await page.locator('#operations').boundingBox(); assert.ok(bounds.x >= 0 && bounds.x+bounds.width <= scenario.width && bounds.y >= 0 && bounds.y+bounds.height <= scenario.height);
      assert.match(await page.locator('#local-status').innerText(), /No GPS/);
      if (!scenario.reduced) { await page.evaluate(async () => (await import('./js/experience.js')).setVisualEffects(false)); await capture('mine-effects-off');
        await page.evaluate(async () => (await import('./js/experience.js')).setVisualQuality('low')); await capture('mine-low-quality');
        const low=await page.evaluate(async () => (await import('./js/experience.js')).diagnostics()); assert.equal(low.shadowUpdate,"static");
        await page.evaluate(async () => (await import('./js/experience.js')).setVisualQuality('standard')); await page.evaluate(async () => (await import('./js/experience.js')).setVisualEffects(true)); }
      await page.click('#compare-trained'); await stage('trained'); await capture('trained');
      assert.match(await page.locator('#local-status').innerText(), /No GPS/);
      assert.match(await page.locator('#operations').innerText(), /Illustrative operating scenario/);
      await page.click('#show-before'); await stage('mine'); await page.click('#show-after'); await stage('trained');
      await page.click('#explore-world-model'); await stage('learning'); await page.selectOption('#learning-source','authored'); await page.waitForFunction(() => document.body.dataset.learningSource === 'authored'); await capture('world-model');
      await page.keyboard.press('Escape'); await stage('trained');
      await page.click('#scroll-product'); await page.waitForTimeout(1500); await capture('product');
      await page.locator('#kit-section').scrollIntoViewIfNeeded(); await page.waitForTimeout(800); await capture('kit');
      await page.click('#assemble-kit'); await page.waitForTimeout(1500); await capture('kit-assembled');
      await page.click('#caption-sources'); await page.locator('#sources-dialog[open]').waitFor(); assert.match(await page.locator('#sources-dialog').innerText(), /NASA \/ VTAD/); await page.keyboard.press('Escape');
      await page.click('#replay-experience'); await page.locator('body.ready').waitFor(); await stage('welcome');
      await page.close();
    }
    assert.deepEqual(report.errors, []); assert.deepEqual(report.httpErrors, []);
  } finally { fs.writeFileSync(path.join(out,'report.json'), JSON.stringify(report,null,2)+'\n'); await browser.close(); }
  console.log('PASS: native visual journey, closed cutaway, geography basis, laptop layout, source labels, keyboard and reduced motion');
})().catch(error => { console.error(error); process.exitCode=1; });
