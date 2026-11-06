/* Native Chrome acceptance for the recorded experiment adapter. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { createHash } = require("node:crypto");
const base = process.env.KESSEL_URL || "http://127.0.0.1:8080/";
const out = process.env.KESSEL_RECORDED_QA || "/private/tmp/kessel-recorded-qa";
fs.mkdirSync(out, { recursive: true });
(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--enable-gpu", "--use-gl=angle", "--use-angle=metal", "--js-flags=--expose-gc"] });
  const report = { browser: browser.version(), date: new Date().toISOString(), sourceCommit: execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim(), workingTreeChanges: execFileSync("git", ["diff", "--name-only"], { encoding: "utf8" }).trim().split("\n").filter(Boolean), sourceFiles: Object.fromEntries(["js/recorded-stage.js", "js/recorded-data.js", "js/experience.js", "index.html", "css/recorded.css"].map((name) => [name, createHash("sha256").update(fs.readFileSync(path.join(__dirname, "..", name))).digest("hex")])), checks: [], errors: [], samples: [] };
  try {
    const memory = await browser.newPage();await memory.goto(base + "data/experiments/index.json");
    report.parsedBundleMemory = await memory.evaluate(async (origin) => {
      const { loadExperiment } = await import(origin + "js/recorded-data.js");
      globalThis.gc?.();const before = performance.memory?.usedJSHeapSize ?? null;
      globalThis.recordedMemoryProbe = await loadExperiment(origin + "data/experiments/index.json", (url) => fetch(url.startsWith("http") ? url : origin + url));
      globalThis.gc?.();const after = performance.memory?.usedJSHeapSize ?? null;
      return { beforeBytes: before, afterBytes: after, deltaBytes: before !== null ? after - before : null, gcAvailable: typeof globalThis.gc === "function", scope: "Chrome decoded/validated bundle retained in a minimal same-origin catalogue page; one sample, not peak process memory" };
    }, base);
    await memory.close();
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
    const page = await context.newPage();const requests = [];
    page.on("pageerror", (e) => report.errors.push(e.message));
    page.on("request", (r) => requests.push(r.url()));
    const stage = (wanted) => page.waitForFunction((s) => document.querySelector("#experience").dataset.stage === s, wanted, { timeout: 60000 });
    const diagnostics = () => page.evaluate(async () => (await import("./js/experience.js")).diagnostics());
    async function mine(p) {
      await p.goto(base);await p.locator("body.ready").waitFor();await p.click("#start-experience");
      await p.waitForFunction(() => document.querySelector("#experience").dataset.stage === "select");
      for (let i = 0; i < 3; i++) await p.click("#environment-next");
      await p.click("#deploy-underground");await p.waitForFunction(() => document.querySelector("#experience").dataset.stage === "surface", null, { timeout: 60000 });
      await p.click("#enter-mine");await p.waitForFunction(() => document.querySelector("#experience").dataset.stage === "mine");
      await p.click("#compare-trained");await p.waitForFunction(() => document.querySelector("#experience").dataset.stage === "trained");
    }
    await mine(page);assert.equal(requests.some((url) => url.endsWith("loader-v1.json")), false);
    const metrics = await page.locator("#metrics").innerText();
    await page.click("#explore-world-model");await stage("learning");
    await page.waitForFunction(() => document.body.dataset.learningSource === "recorded_synthetic");
    assert.match(await page.textContent("#learning-source-label"), /Recorded synthetic/);
    assert.match(await page.textContent("#caption-detail"), /Mine figures illustrative/);
    await page.click("#pause-training");let paused = (await diagnostics()).learning;
    if (!paused.paused) { await page.click("#pause-training");paused = (await diagnostics()).learning; }
    await page.waitForTimeout(350);assert.equal((await diagnostics()).learning.simulatedTime, paused.simulatedTime);
    await page.click('[data-checkpoint="2"]');assert.equal(await page.textContent("#episode-count"), "1,479");
    assert.equal(await page.textContent("#reward-curve-label"), "Training mean reward");
    assert.equal(await page.textContent("#reward-heading"), "Step reward");
    const expectedReward = JSON.parse(fs.readFileSync(path.join(__dirname, "../data/experiments/loader-v1.json"))).learning_curve.at(-1).mean_step_reward.toFixed(4);
    assert.equal(await page.textContent("#reward-value"), expectedReward);
    for (const horizon of ["1", "2", "4", "8"]) { await page.selectOption("#forecast-horizon", horizon);assert.equal((await diagnostics()).learning.horizon, Number(horizon)); }
    await page.selectOption("#forecast-horizon", "1");
    await page.locator("#replay-scrub").evaluate((e) => { e.value = "2";e.dispatchEvent(new Event("input", { bubbles: true })); });
    assert.equal((await diagnostics()).learning.paused, true);
    await page.screenshot({ path: path.join(out, "recorded-inspection.jpg"), type: "jpeg", quality: 88 });
    await page.waitForTimeout(5500);report.samples.push({ name: "recorded-inspection", ...(await diagnostics()) });
    assert.ok(report.samples.at(-1).meanFps >= 30);
    assert.ok(report.samples.at(-1).learning.bucketMouthErrorM < 1e-7);
    await page.evaluate(async () => { window.recordedDiagnostics = (await import("./js/experience.js")).diagnostics; });
    await page.click("#replay-training");const replayStarted = Date.now();
    await page.waitForFunction(() => { const s = window.recordedDiagnostics().learning;return s?.checkpoint === 2 && s.paused && s.frame === 39; }, null, { timeout: 22000 });
    report.sequenceWallSeconds = (Date.now() - replayStarted) / 1000;
    assert.ok(report.sequenceWallSeconds >= 10 && report.sequenceWallSeconds < 16, `sequence took ${report.sequenceWallSeconds}s`);
    assert.equal(await page.textContent("#action-value"), "No next action");assert.match(await page.textContent("#checkpoint-outcome"), /Delivered 0 kg/);
    report.samples.push({ name: "recorded-sequence", ...(await diagnostics()) });
    await page.screenshot({ path: path.join(out, "recorded-terminal.jpg"), type: "jpeg", quality: 88 });
    await page.selectOption("#learning-source", "authored");await page.waitForFunction(() => document.body.dataset.learningSource === "authored");
    assert.match(await page.textContent("#caption-detail"), /Illustrative training/);assert.equal(await page.locator(".prediction-inspector").isVisible(), false);
    await page.selectOption("#learning-source", "recorded_synthetic");await page.waitForFunction(() => document.body.dataset.learningSource === "recorded_synthetic");
    await page.keyboard.press("Escape");await stage("trained");assert.equal(await page.locator("#metrics").innerText(), metrics);
    assert.equal(await page.evaluate(() => document.activeElement.id), "explore-world-model");
    await page.click("#scroll-product");await page.locator("#product-world-model").scrollIntoViewIfNeeded();const scroll = await page.evaluate(() => scrollY);
    await page.click("#product-world-model");await stage("learning");await page.click("#exit-world-model");await stage("trained");
    assert.ok(Math.abs(await page.evaluate(() => scrollY) - scroll) < 3);assert.equal(await page.evaluate(() => document.activeElement.id), "product-world-model");
    assert.ok(requests.every((url) => url.startsWith(base)));
    report.checks.push("Progressive integrity-checked loading", "Actual checkpoint counters/curve/action units", "Pause, scrub, pacing, four forecast horizons and terminal hold", "Twelve-second single-clock sequence without invented success", "Explicit source switching", "Mine comparison and product scroll/focus restored", "Local assets only");
    await context.close();
    const reduced = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: "reduce" });
    const rp = await reduced.newPage();rp.on("pageerror", (e) => report.errors.push(e.message));await mine(rp);await rp.click("#explore-world-model");
    await rp.waitForFunction(() => document.querySelector("#experience").dataset.stage === "learning");
    const reducedState = await rp.evaluate(async () => (await import("./js/experience.js")).diagnostics().learning);assert.equal(reducedState.paused, true);
    await rp.screenshot({ path: path.join(out, "recorded-reduced-1280.jpg"), type: "jpeg", quality: 88 });
    await reduced.close();
    const failure = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: "reduce" });
    const fp = await failure.newPage();fp.on("pageerror", (e) => report.errors.push(e.message));
    await fp.route("**/data/experiments/loader-v1.json", async (route) => { const original = await route.fetch(), body = await original.body();body[20] ^= 1;await route.fulfill({ response: original, body }); });
    await mine(fp);await fp.click("#explore-world-model");await fp.locator("#experiment-error").waitFor({ state: "visible" });
    assert.equal(await fp.getAttribute("#experience", "data-stage"), "trained");assert.match(await fp.textContent("#experiment-error-message"), /checksum/);
    await fp.click("#use-concept-replay");await fp.waitForFunction(() => document.querySelector("#experience").dataset.stage === "learning");
    assert.equal(await fp.evaluate(() => document.body.dataset.learningSource), "authored");assert.match(await fp.textContent("#caption-detail"), /Illustrative/);
    await failure.close();report.checks.push("Reduced motion starts paused", "Corrupt bundle remains an error until explicit concept selection");
    assert.deepEqual(report.errors, []);
    fs.writeFileSync(path.join(out, "report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
})().catch((e) => { console.error(e);process.exitCode = 1; });
