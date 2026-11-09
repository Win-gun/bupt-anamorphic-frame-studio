const { chromium } = require("@playwright/test");
const path = require("path"),
  fs = require("fs");
(async () => {
  const base = process.env.BASE_URL || "http://127.0.0.1:8000";
  const out = path.resolve(__dirname, "../examples/v2");
  const browser = await chromium.launch({
    channel: "chrome",
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(base);
  await page.getByRole("heading", { name: "调整参数" }).waitFor();
  const defaultConfig = await (
    await page.request.get(base + "/api/settings")
  ).json();
  try {
    await page
      .locator('input[type=file][accept="image/*"]')
      .setInputFiles(path.join(out, "poster-16x9.png"));
    await page.getByRole("button", { name: "原始画作" }).click();
    await page.locator(".viewport img").waitFor();
    if (
      !(await page
        .locator(".viewport img")
        .evaluate((i) => i.complete && i.naturalWidth > 0))
    )
      throw Error("local original failed");
    await page.getByRole("button", { name: "快速预览" }).click();
    await page.locator(".downloads a").first().waitFor({ timeout: 240000 });
    await page.locator(".viewport img").waitFor();
    if (
      !(await page
        .locator(".viewport img")
        .evaluate((i) => i.complete && i.naturalWidth > 0))
    )
      throw Error("preview not loaded");
    await page.locator(".compare summary").click();
    if ((await page.locator(".compare img").count()) !== 2)
      throw Error("compare missing");
    const modelResponse = page.waitForResponse((r) => r.url().endsWith(".glb"));
    await page.getByRole("button", { name: "交互 3D" }).click();
    await page.locator(".orbit canvas").waitFor();
    const glbResponse = await modelResponse;
    if (!glbResponse.ok())
      throw Error("GLB request failed " + glbResponse.status());
    await page.waitForTimeout(3000);
    if (await page.getByText("无法加载导出的 3D 模型").count())
      throw Error("GLB load failed");
    const canvas = page.locator(".orbit canvas");
    const before = await canvas.screenshot();
    const box = await canvas.boundingBox();
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.55, {
      steps: 8,
    });
    await page.mouse.up();
    await page.mouse.wheel(0, -200);
    await page.waitForTimeout(800);
    const after = await canvas.screenshot();
    if (before.equals(after)) throw Error("orbit did not change image");
    await page.screenshot({
      path: path.join(out, "ui-desktop.png"),
      fullPage: true,
    });
    const material = page.getByLabel("材质");
    await material.selectOption("black_titanium");
    await page.getByRole("button", { name: "保存配置" }).click();
    await page.waitForTimeout(500);
    if (
      (await (await page.request.get(base + "/api/settings")).json()).frame
        .material !== "black_titanium"
    )
      throw Error("save failed");
    await page.getByRole("button", { name: "重置默认" }).click();
    await page.waitForTimeout(500);
    if (
      (await (await page.request.get(base + "/api/settings")).json()).frame
        .material !== "gold"
    )
      throw Error("reset failed");
    const changed = structuredClone(defaultConfig);
    changed.frame.material = "glass";
    await page
      .locator('input[accept="application/json,.json"]')
      .setInputFiles({
        name: "test.json",
        mimeType: "application/json",
        buffer: Buffer.from(JSON.stringify(changed)),
      });
    await page.waitForTimeout(500);
    if ((await material.inputValue()) !== "glass") throw Error("import failed");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({
      path: path.join(out, "ui-mobile.png"),
      fullPage: true,
    });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    );
    const result = {
      original: true,
      quickPreview: true,
      comparison: true,
      orbitCanvas: true,
      glbHTTP: glbResponse.status(),
      orbitChanged: !before.equals(after),
      settingsSave: true,
      settingsReset: true,
      configImport: true,
      errors,
      overflow,
    };
    fs.writeFileSync(
      path.join(out, "ui-check.json"),
      JSON.stringify(result, null, 2),
    );
    if (errors.length || overflow) throw Error(JSON.stringify(result));
    console.log(JSON.stringify(result));
  } finally {
    await page.request.put(base + "/api/settings", { data: defaultConfig });
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
