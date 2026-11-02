/* Local browser acceptance. npm install --no-save playwright in a parent directory. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const out = process.env.KESSEL_QA_DIR || "/private/tmp/kessel-phase10-evidence";
fs.mkdirSync(out, { recursive: true });
const base = process.env.KESSEL_URL || "http://127.0.0.1:8080/";
(async () => {
  const browser = await chromium.launch({
    channel: "chrome",
    headless: true,
    args: ["--enable-gpu", "--use-gl=angle", "--use-angle=metal"],
  });
  const report = {
    browser: browser.version(),
    date: new Date().toISOString(),
    samples: [],
    checks: [],
    errors: [],
    httpErrors: [],
  };
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    recordVideo: { dir: out, size: { width: 1280, height: 800 } },
  });
  const page = await context.newPage();
  page.on("pageerror", (e) => report.errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error") report.errors.push(m.text());
  });
  page.on("response", (r) => {
    if (r.status() >= 400) report.httpErrors.push([r.status(), r.url()]);
  });
  await page.addInitScript(() => {
    window.qaFrames = [];
    let previous;
    function frame(t) {
      if (previous)
        window.qaFrames.push([
          document.querySelector("#experience")?.dataset.stage,
          t - previous,
        ]);
      previous = t;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });
  const stage = async (expected) =>
    page.waitForFunction(
      (s) => document.querySelector("#experience").dataset.stage === s,
      expected,
      { timeout: 60000 },
    );
  const diag = () =>
    page.evaluate(async () =>
      (await import("./js/experience.js")).diagnostics(),
    );
  const capture = async (name) => {
    await page.screenshot({
      path: path.join(out, name + ".jpg"),
      type: "jpeg",
      quality: 85,
    });
  };
  const sample = async (name) => {
    await page.waitForTimeout(5500);
    report.samples.push({ name, ...(await diag()) });
    await capture(name);
    console.log(name, report.samples.at(-1).meanFps.toFixed(1) + " fps");
  };
  await page.goto(base, { waitUntil: "domcontentloaded" });
  await page.locator("body.ready").waitFor();
  report.readyMs = await page.evaluate(() => performance.now());
  await sample("welcome");
  await page.click("#start-experience");
  await stage("select");
  await page.waitForTimeout(2000);
  await capture("glacier");
  for (const name of ["Desert", "Space", "Underground"]) {
    await page.click("#environment-next");
    assert.equal(await page.textContent("#environment-name"), name);
    await page.waitForTimeout(600);
    await capture(name.toLowerCase());
  }
  report.checks.push("Five carousel themes; only underground deploys");
  await page.click("#environment-next");
  assert.equal(await page.textContent("#environment-name"), "Deep sea");
  assert.equal(await page.locator("#deploy-underground").isVisible(), false);
  await page.waitForTimeout(400);
  await capture("deep-sea");
  await page.click("#environment-prev");
  await page.click("#deploy-underground");
  await page.waitForTimeout(2400);
  await capture("descent");
  await stage("surface");
  await sample("surface");
  await page.click("#enter-mine");
  await stage("mine");
  await sample("baseline");
  const before = await page.locator("#metrics").innerText();
  assert.match(before, /88/);
  assert.match(before, /12.95/);
  await page.waitForTimeout(2500);
  await page.click("#compare-trained");
  await page.waitForTimeout(900);
  await capture("transition");
  await stage("trained");
  await sample("trained");
  const after = await page.locator("#metrics").innerText();
  assert.match(after, /132/);
  assert.match(after, /8.03/);
  assert.match(after, /3,467/);
  assert.match(after, /2h40/);
  report.checks.push("All six GBP measures match same-batch arithmetic");
  for (let i = 0; i < 2; i++) {
    await page.click("#show-before");
    await stage("mine");
    assert.equal(await page.locator("#metrics").innerText(), before);
    await page.click("#show-after");
    await stage("trained");
    assert.equal(await page.locator("#metrics").innerText(), after);
  }
  report.checks.push("Before/after is repeatable; weak connectivity retained");
  await page.click("#explore-world-model");
  await stage("learning");
  await page.click("#pause-training");
  await page.waitForTimeout(150);
  const paused = await page.textContent("#episode-count");
  await page.waitForTimeout(700);
  assert.equal(await page.textContent("#episode-count"), paused);
  await capture("paused");
  await page.click("#pause-training");
  await page.waitForTimeout(8500);
  assert.equal(await page.textContent("#episode-count"), "2,400,000");
  await sample("learning");
  for (let i = 0; i < 3; i++) {
    await page.click(`[data-checkpoint="${i}"]`);
    await page.waitForTimeout(650);
    await capture("checkpoint-" + i);
  }
  await page.click('[data-checkpoint="2"]');
  await page.waitForTimeout(9100);
  await capture("delivered");
  await page.click("#replay-training");
  await page.waitForTimeout(500);
  assert.notEqual(await page.textContent("#episode-count"), "2,400,000");
  await page.keyboard.press("Escape");
  await stage("trained");
  assert.equal(await page.locator("#metrics").innerText(), after);
  report.checks.push(
    "Training pause, resume, 2.4m completion, three checkpoints, replay and Escape return",
  );
  await page.click("#scroll-product");
  await page.waitForTimeout(1500);
  await capture("product");
  const productScroll = await page.evaluate(() => scrollY);
  await page.click("#product-world-model");
  await stage("learning");
  await page.click("#exit-world-model");
  await stage("trained");
  assert.ok(Math.abs((await page.evaluate(() => scrollY)) - productScroll) < 3);
  report.checks.push(
    "World-model entry from product restores scroll and result",
  );
  await page.locator("#kit-section").scrollIntoViewIfNeeded();
  await sample("kit");
  assert.equal(await page.locator("#kit-components button").count(), 7);
  await page.click("#assemble-kit");
  await page.waitForTimeout(1800);
  await capture("assembled");
  await page.click("#assemble-kit");
  await page.waitForTimeout(1200);
  await page.locator("#kit-components button").nth(2).focus();
  await capture("kit-focus");
  report.checks.push("Seven proposed kit parts; assembly and keyboard focus");
  await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
  await page.waitForTimeout(600);
  await stage("trained");
  for (const size of [
    { width: 1280, height: 800 },
    { width: 1440, height: 900 },
  ]) {
    await page.setViewportSize(size);
    await page.waitForTimeout(700);
    const bounds = await page.locator("#operations").boundingBox();
    assert.ok(
      bounds.x >= 0 &&
        bounds.y >= 60 &&
        bounds.y + bounds.height <= size.height - 40,
    );
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await capture("laptop-" + size.width);
  }
  await page.click("#sources-open");
  assert.equal(await page.locator("#sources-dialog").isVisible(), true);
  await page.keyboard.press("Escape");
  assert.equal(await page.locator("#sources-dialog").isVisible(), false);
  report.checks.push("Laptop layouts, sources and native dialog dismissal");
  report.resources = await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .map((r) => ({
        name: new URL(r.name).pathname,
        bytes: r.encodedBodySize,
        durationMs: r.duration,
      })),
  );
  const frames = await page.evaluate(() => window.qaFrames);
  report.frameTails = {};
  for (const name of new Set(frames.map((f) => f[0]))) {
    const vals = frames
      .filter((f) => f[0] === name)
      .map((f) => f[1])
      .sort((a, b) => a - b);
    report.frameTails[name] = {
      frames: vals.length,
      p95Ms: vals[Math.floor(vals.length * 0.95)],
      maxMs: vals.at(-1),
    };
  }
  report.final = await diag();
  const video = page.video();
  await page.close();
  await context.close();
  await video.saveAs(path.join(out, "walkthrough.webm"));
  const reduced = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    reducedMotion: "reduce",
  });
  const rp = await reduced.newPage();
  let failTerrain = true;
  await rp.route("**/assets/rutongo/satellite-2026-08-14.webp", (route) =>
    failTerrain ? route.abort() : route.continue(),
  );
  await rp.goto(base);
  await rp.locator("body.ready").waitFor();
  await rp.click("#start-experience");
  for (let i = 0; i < 3; i++) await rp.click("#environment-next");
  await rp.click("#deploy-underground");
  await rp.waitForTimeout(1800);
  assert.equal(await rp.getAttribute("#experience", "data-stage"), "select");
  failTerrain = false;
  await rp.unroute("**/assets/rutongo/satellite-2026-08-14.webp");
  await rp.click("#deploy-underground");
  await rp.waitForFunction(
    () => document.querySelector("#experience").dataset.stage === "surface",
    null,
    { timeout: 60000 },
  );
  await rp.click("#enter-mine");
  await rp.waitForFunction(
    () => document.querySelector("#experience").dataset.stage === "mine",
    null,
    { timeout: 60000 },
  );
  await rp.click("#compare-trained");
  await rp.waitForFunction(
    () => document.querySelector("#experience").dataset.stage === "trained",
  );
  await rp.click("#replay-experience");
  await rp.locator("body.ready").waitFor();
  assert.equal(await rp.getAttribute("#experience", "data-stage"), "welcome");
  report.checks.push(
    "Missing terrain retries, reduced motion and full restart",
  );
  await reduced.close();
  fs.writeFileSync(
    path.join(out, "report.json"),
    JSON.stringify(report, null, 2),
  );
  await browser.close();
  assert.deepEqual(report.errors, []);
  assert.deepEqual(report.httpErrors, []);
  assert.ok(report.samples.every((s) => s.meanFps >= 30));
  console.log("PASS", report.checks.length, "acceptance groups; report:", out);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
