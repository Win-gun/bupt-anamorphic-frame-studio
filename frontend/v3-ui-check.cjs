const { chromium } = require("@playwright/test");
const fs = require("fs"),
  path = require("path");
(async () => {
  const base = process.env.BASE_URL || "http://127.0.0.1:8003",
    out = path.resolve(__dirname, "../examples/v3");
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
      channel: "chrome",
      headless: true,
      args: ["--enable-unsafe-swiftshader"],
    }),
    page = await browser.newPage({ viewport: { width: 1600, height: 1000 } }),
    errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const req = page.request,
    original = await (await req.get(base + "/api/settings")).json();
  let checks = {};
  try {
    await page.goto(base);
    await page.getByText("极光悬浮").waitFor();
    checks.default = await page.locator(".template.selected").innerText();
    checks.creativeHidesScreen =
      (await page.getByText("左屏 px").count()) === 0;
    await page.getByRole("button", { name: "Blue Hour · 灰蓝晨雾" }).click();
    checks.palette = await page
      .locator(".palette-list button.selected")
      .innerText();
    await page.locator("summary").filter({ hasText: "Legacy" }).click();
    await page.getByRole("button", { name: "影院画框" }).click();
    checks.legacy = (await page.getByLabel("材质").count()) === 1;
    await page.getByRole("button", { name: "创作模式 · 切换" }).click();
    checks.proShowsScreen = (await page.getByText("左屏 px").count()) === 1;
    await page.getByRole("button", { name: "保存配置" }).click();
    await page.waitForTimeout(300);
    checks.saved =
      (await (await req.get(base + "/api/settings")).json()).frame.template ===
      "cinema";
    await page.getByRole("button", { name: "重置默认" }).click();
    await page.waitForTimeout(300);
    checks.reset = (
      await page.locator(".template.selected").innerText()
    ).includes("极光");
    await page
      .locator('input[type=file][accept="image/*"]')
      .first()
      .setInputFiles(
        path.resolve(__dirname, "../examples/v2/jiqi-qiuyun/original.png"),
      );
    await page.getByRole("button", { name: "快速预览" }).click();
    await page.locator(".downloads a").first().waitFor({ timeout: 240000 });
    await page.getByRole("button", { name: "最佳观看模拟" }).click();
    await page.locator(".viewport img").waitFor();
    checks.alpha = await page
      .locator(".viewport img")
      .evaluate((i) => i.complete && i.naturalWidth > 0);
    await page.getByRole("button", { name: "LED 裁切预览" }).click();
    await page.locator(".viewport img").waitFor();
    checks.crop = await page
      .getByText("裁切预览，并非实际播放尺寸")
      .isVisible();
    await page.getByRole("button", { name: "交互 3D" }).click();
    const canvas = page.locator(".orbit canvas");
    await canvas.waitFor();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(out, "ui-orbit.png") });
    const before = await canvas.screenshot();
    let box = await canvas.boundingBox();
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.55, {
      steps: 8,
    });
    await page.mouse.up();
    await page.mouse.wheel(0, -200);
    await page.waitForTimeout(600);
    const after = await canvas.screenshot();
    checks.orbitChanges = !before.equals(after);
    await page.getByRole("button", { name: "重置视角" }).click();
    await page.waitForTimeout(600);
    const reset = await canvas.screenshot();
    fs.writeFileSync(path.join(out, "ui-orbit-before.png"), before);
    fs.writeFileSync(path.join(out, "ui-orbit-reset.png"), reset);
    checks.resetMeanPixelDelta = await page.evaluate(
      async ([a, b]) => {
        const load = (s) =>
          new Promise((r) => {
            const i = new Image();
            i.onload = () => r(i);
            i.src = "data:image/png;base64," + s;
          });
        const [x, y] = await Promise.all([load(a), load(b)]);
        const c = document.createElement("canvas");
        c.width = x.width;
        c.height = x.height;
        const ctx = c.getContext("2d");
        ctx.drawImage(x, 0, 0);
        const p = ctx.getImageData(0, 0, c.width, c.height).data;
        ctx.drawImage(y, 0, 0);
        const q = ctx.getImageData(0, 0, c.width, c.height).data;
        let d = 0;
        for (let i = 0; i < p.length; i++) d += Math.abs(p[i] - q[i]);
        return d / p.length;
      },
      [before.toString("base64"), reset.toString("base64")],
    );
    checks.resetRestores = checks.resetMeanPixelDelta < 1;
    await page.getByRole("button", { name: "现场照片合成" }).click();
    await page
      .locator(".photo-tools input[type=file]")
      .setInputFiles({
        name: "synthetic-not-site.svg",
        mimeType: "image/svg+xml",
        buffer: Buffer.from(
          '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><rect width="800" height="500" fill="#778899"/><text x="50" y="80" fill="white">SYNTHETIC TEST FIXTURE — NOT A SITE PHOTO</text></svg>',
        ),
      });
    checks.photoLabel = await page
      .getByText("手动配准预览 · 未现场校准")
      .isVisible();
    checks.photoOverlay = (await page.locator(".photo-overlay").count()) === 1;
    await page.locator(".photo-tools input[type=range]").first().fill("35");
    await page.screenshot({ path: path.join(out, "ui-photo-synthetic.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    checks.noOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    );
    await page.screenshot({
      path: path.join(out, "ui-mobile.png"),
      fullPage: true,
    });
    checks.errors = errors;
    fs.writeFileSync(
      path.join(out, "ui-check.json"),
      JSON.stringify(checks, null, 2),
    );
    console.log(JSON.stringify(checks, null, 2));
    if (
      Object.entries(checks).some(([k, v]) => typeof v === "boolean" && !v) ||
      errors.length
    )
      process.exitCode = 1;
  } finally {
    await req.put(base + "/api/settings", { data: original });
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
