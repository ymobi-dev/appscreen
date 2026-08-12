// EMET hero screenshot pipeline.
// Drives the yuzu.shot app headlessly, renders ASO heroes per locale from the
// real-app captures in assets/<assetSource>/<locale>/ and writes PNGs to
// output/<outputDevice>/<variant>/<locale>/. All knobs live in hero-config.cjs
// (env-overridable). The main index.html only loads the biblia365 automation,
// so this runner injects the EMET one afterwards -- it redefines
// window.generateHeroScreenshots with EMET's own font paths. Run with:
//   (cd appscreen && python3 -m http.server 8000)   # in another terminal
//   NODE_PATH=$(npm root -g) node apps/emet-assist/generate-hero.cjs
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const CFG = require('./hero-config.cjs');

const ROOT = path.join(__dirname, '..', '..');
const ASSETS = path.join(ROOT, 'apps/emet-assist/assets', CFG.assetSource);
// Output is namespaced per variant so original and new directions coexist.
const OUT = path.join(ROOT, 'apps/emet-assist/output', CFG.outputDevice, CFG.variant);

function loadSlides(locale) {
  const folder = CFG.assetFolders[locale] || locale;
  const files = fs.readdirSync(path.join(ASSETS, folder)).map((f) => f.normalize('NFC'));
  const names = CFG.slideFiles.map((f) => f.normalize('NFC'));
  // Headline text width after the app's 8% side padding (canvas is per platform).
  const availWidth = Math.floor(CFG.canvasW * (1 - 0.16));
  const baseSize = CFG.theme.headlineSize || 96;
  return (CFG.copy[locale] || []).map((c, i) => {
    const file = files.find((f) => f === names[i]);
    const entry = {
      title: c.h,
      subtitle: c.s,
      accent: CFG.accents[i % CFG.accents.length]
    };
    // Montserrat is a wide geometric sans (~0.58em avg advance): shrink long
    // headlines so each stays on a single line instead of wrapping into the
    // device. hSize is applied by the automation.
    if (entry.title.length * 0.58 * baseSize > availWidth) {
      entry.hSize = Math.max(64, Math.floor(availWidth / (entry.title.length * 0.58)));
    }
    if (file) {
      entry.imageDataUrl = 'data:image/png;base64,' +
        fs.readFileSync(path.join(ASSETS, folder, file)).toString('base64');
    }
    return entry;
  });
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(CFG.appUrl, { waitUntil: 'networkidle' });
  // index.html already loaded the biblia365 automation; EMET's redefines the
  // entry point (same state contract, EMET fonts). Run it after the app settles.
  await page.addScriptTag({ path: path.join(__dirname, 'emet-assist-automation.js') });
  await page.waitForFunction(() => typeof window.generateHeroScreenshots === 'function', { timeout: 30000 });

  for (const locale of CFG.locales) {
    const slides = loadSlides(locale);
    const count = await page.evaluate(
      ({ locale, slides, theme, outputDevice, device3D, frameColor }) =>
        window.generateHeroScreenshots({ locale, theme, slides, outputDevice, device3D, frameColor }),
      { locale, slides, theme: CFG.theme, outputDevice: CFG.outputDevice, device3D: CFG.device3D, frameColor: CFG.frameColor }
    );
    await page.waitForFunction(
      () => typeof phoneModelLoaded !== 'undefined' && phoneModelLoaded === true,
      { timeout: 30000 }
    );

    const dir = path.join(OUT, locale);
    fs.mkdirSync(dir, { recursive: true });
    for (let i = 0; i < count; i++) {
      await page.evaluate((idx) => { state.selectedIndex = idx; updateCanvas(); }, i);
      await page.waitForTimeout(700); // 3D re-render + screen texture upload
      const dataUrl = await page.evaluate(() => document.getElementById('preview-canvas').toDataURL('image/png'));
      fs.writeFileSync(path.join(dir, `hero-${i + 1}.png`), Buffer.from(dataUrl.split(',')[1], 'base64'));
    }
    console.log(`[${CFG.variant}] [${locale}] ${count} heroes -> ${dir}`);
  }
  await browser.close();
}

main().catch((e) => { console.error('FAILED:', e); process.exit(1); });
