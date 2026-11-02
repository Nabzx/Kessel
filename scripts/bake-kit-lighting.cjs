/* Rebuild the original Kessel CubeUV reflection asset with the local server running. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const browser = await chromium.launch({
    channel: "chrome",
    headless: true,
    args: ["--enable-gpu", "--use-gl=angle", "--use-angle=metal"],
  });
  const page = await browser.newPage();
  await page.goto(process.env.KESSEL_URL || "http://127.0.0.1:8080/");
  const result = await page.evaluate(async () => {
    const T = await import("three");
    const renderer = new T.WebGLRenderer({ antialias: false });
    const faces = Array.from({ length: 6 }, (_, index) => {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 128;
      const context = canvas.getContext("2d");
      context.fillStyle =
        index === 2 ? "#b9c6c6" : index === 3 ? "#24292a" : "#556166";
      context.fillRect(0, 0, 128, 128);
      const gradient = context.createLinearGradient(0, 0, 128, 128);
      gradient.addColorStop(0, "#ecebe0");
      gradient.addColorStop(0.3, "#8a9b9d");
      gradient.addColorStop(1, "#263136");
      context.fillStyle = gradient;
      context.fillRect(12, 9, 104, 35);
      context.fillStyle = "#d8dfdc";
      context.fillRect(index % 2 ? 90 : 12, 52, 10, 60);
      return canvas;
    });
    const cube = new T.CubeTexture(faces);
    cube.colorSpace = T.SRGBColorSpace;
    cube.needsUpdate = true;
    const generator = new T.PMREMGenerator(renderer),
      target = generator.fromCubemap(cube);
    const values = new Uint16Array(target.width * target.height * 4);
    renderer.readRenderTargetPixels(
      target,
      0,
      0,
      target.width,
      target.height,
      values,
    );
    const bytes = new Uint8Array(values.buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 16384)
      binary += String.fromCharCode(...bytes.subarray(i, i + 16384));
    const result = {
      width: target.width,
      height: target.height,
      base64: btoa(binary),
    };
    target.dispose();
    cube.dispose();
    generator.dispose();
    renderer.dispose();
    return result;
  });
  const file = path.join(__dirname, "../assets/lighting/kit-studio.bin");
  fs.writeFileSync(file, Buffer.from(result.base64, "base64"));
  console.log(file, result.width, result.height);
  await browser.close();
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
