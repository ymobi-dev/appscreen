// ymobidev og-card 3D phone renderer.
// Drives the real appscreen app headlessly and exports two transparent,
// alpha-cropped phone PNGs for the ymobidev.com og-image card: one Android
// (Samsung Galaxy S25 Ultra) and one iPhone (15 Pro Max). Reuses the biblia365
// automation hook (window.generateHeroScreenshots) to build the screenshot
// entry, then renderThreeJSForScreenshot to draw only the 3D device + contact
// shadow on a transparent canvas (no card background/text).
//
// Run with:
//   NODE_PATH=$(npm root -g) node apps/ymobidev/generate-og.cjs
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const APP_URL = 'http://localhost:8000';
const OUT_DIR = path.join(__dirname, 'output');

// App captures used on the og-card fan: Android phone shows the Alefly mobile
// site preview (a real web app running in a browser), iPhone shows Desafios da
// Bíblia Kids (its iOS capture — more colorful than the Bíblia 365 screen).
const SITE_IMAGES = '/Users/yuripacheco/Projetos/ymobidev-site/public/assets/images';
const BIBLIA_ASSETS = '/Users/yuripacheco/Projetos/appscreen/apps/biblia365/assets';

const RENDERS = [
  {
    name: 'phone-android',
    device3D: 'samsung',
    outputDevice: 'android-phone',
    frameColor: 'black',
    canvas: { w: 1080, h: 1920 },
    rotation3D: { x: -3, y: -14, z: 0 },
    image: path.join(SITE_IMAGES, 'preview-alefly-mobile.webp'),
  },
  {
    name: 'phone-iphone',
    device3D: 'iphone',
    outputDevice: 'iphone-6.9',
    frameColor: 'natural',
    canvas: { w: 1320, h: 2868 },
    rotation3D: { x: -3, y: 14, z: 0 },
    image: path.join(BIBLIA_ASSETS, 'iphone/pt/Home.png'),
  },
];

// Phone centered, fully visible, subtle 3D tilt. Title/subtitle stay empty —
// only the device is drawn (renderThreeJSForScreenshot bypasses the canvas
// background/text composite).
const THEME = {
  scale: 55,
  x: 50,
  y: 50,
  cornerRadius: 28,
};

async function renderPhone(browser, render) {
  const page = await browser.newPage();
  await page.goto(APP_URL, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => typeof window.generateHeroScreenshots === 'function', { timeout: 30000 });

  const mime = render.image.endsWith('.png') ? 'image/png' : 'image/webp';
  const imageDataUrl =
    `data:${mime};base64,` + fs.readFileSync(render.image).toString('base64');

  await page.evaluate(
    ({ theme, slides, outputDevice, device3D, frameColor }) =>
      window.generateHeroScreenshots({ locale: 'pt-BR', theme, slides, outputDevice, device3D, frameColor }),
    {
      theme: { ...THEME, rotation3D: render.rotation3D },
      slides: [{ name: 'phone', title: '', subtitle: '', imageDataUrl }],
      outputDevice: render.outputDevice,
      device3D: render.device3D,
      frameColor: render.frameColor,
    }
  );

  // selectScreenshot(0) -> switchPhoneModel(device3D); wait for the GLB load.
  await page.waitForFunction(
    () => typeof phoneModelLoaded !== 'undefined' && phoneModelLoaded === true,
    { timeout: 30000 }
  );

  const res = await page.evaluate(({ w, h }) => {
    const c = document.createElement('canvas');
    c.width = w;
    c.height = h;

    // No baked contact shadow. appscreen's drawPhoneContactShadow paints an
    // amber pool + dark core tuned for dark store backgrounds; on the card's
    // light gradient it reads muddy, and the core projects wide of the tilted
    // body (its pixels land inside a tight alpha>200 crop, polluting the PNG
    // corners and making a CSS drop-shadow look square). Neutralize it so the
    // PNG is a clean device silhouette — the card grounds the phone with its
    // own drop-shadow, which then follows the rounded body.
    const origShadow = window.drawPhoneContactShadow;
    window.drawPhoneContactShadow = () => {};
    renderThreeJSForScreenshot(c, w, h, 0);
    window.drawPhoneContactShadow = origShadow;

    // Crop by the phone's alpha (includes the soft antialiased edge so the
    // rounded corners survive), with a small pad.
    const ctx = c.getContext('2d');
    const img = ctx.getImageData(0, 0, w, h);
    const d = img.data;
    let minX = w, minY = h, maxX = -1, maxY = -1;
    const threshold = 10;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        if (d[(y * w + x) * 4 + 3] > threshold) {
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }
    if (maxX < 0) return { ok: false };
    const pad = 4;
    minX = Math.max(0, minX - pad);
    minY = Math.max(0, minY - pad);
    maxX = Math.min(w - 1, maxX + pad);
    maxY = Math.min(h - 1, maxY + pad);
    const cw = maxX - minX + 1;
    const ch = maxY - minY + 1;
    const out = document.createElement('canvas');
    out.width = cw;
    out.height = ch;
    out.getContext('2d').drawImage(c, minX, minY, cw, ch, 0, 0, cw, ch);
    return { ok: true, dataUrl: out.toDataURL('image/png'), w: cw, h: ch };
  }, render.canvas);

  await page.close();
  return res;
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  for (const render of RENDERS) {
    const res = await renderPhone(browser, render);
    if (!res || !res.ok) throw new Error(`${render.name}: nothing rendered`);
    const outPath = path.join(OUT_DIR, `${render.name}.png`);
    fs.writeFileSync(outPath, Buffer.from(res.dataUrl.split(',')[1], 'base64'));
    console.log(`${render.name}: ${res.w}x${res.h}px (aspect ${(res.w / res.h).toFixed(3)}) -> ${outPath}`);
  }
  await browser.close();
}

main().catch((e) => { console.error('FAILED:', e); process.exit(1); });
