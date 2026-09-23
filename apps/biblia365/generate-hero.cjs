// Bíblia 365 hero screenshot pipeline.
// Drives the real app headlessly, builds top-5-style ASO heroes per locale
// and writes PNGs to output/<outputDevice>/<locale>/. All knobs live in
// hero-config.cjs (env-overridable). Run with:
//   NODE_PATH=$(npm root -g) node apps/biblia365/generate-hero.cjs
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const CFG = require('./hero-config.cjs');

const ROOT = path.join(__dirname, '..', '..');
const ASSETS = path.join(ROOT, 'apps/biblia365/assets', CFG.assetSource);
const TRANSLATIONS = path.join(ROOT, 'apps/biblia365/biblia365-translations.json');
// Output is namespaced per variant so the original and new directions coexist.
const OUT = path.join(ROOT, 'apps/biblia365/output', CFG.outputDevice, CFG.variant);

// The app does not render `**bold**` markers from the translation files.
function stripMarkdown(s) {
  return (s || '').replace(/\*\*/g, '').replace(/\*/g, '');
}

function loadSlides(translations, locale) {
  const folder = CFG.assetFolders[locale] || locale;
  const files = fs.readdirSync(path.join(ASSETS, folder)).map((f) => f.normalize('NFC'));
  const names = CFG.slideFiles.map((f) => f.normalize('NFC'));
  // Headline text width after the app's 8% side padding (canvas is per platform).
  const availWidth = Math.floor(CFG.canvasW * (1 - 0.16));
  const baseSize = CFG.theme.headlineSize || 96;
  return (translations[locale]?.slides || []).map((slide, i) => {
    const file = files.find((f) => f === names[i]);
    const copy = CFG.copy[locale]?.[i];
    const title = copy ? copy.h : stripMarkdown(slide[0]);
    const entry = {
      title,
      subtitle: copy ? copy.s : stripMarkdown(slide[1]),
      accent: CFG.accents[i % CFG.accents.length]
    };
    // Montserrat is a wide geometric sans (~0.58em avg advance): shrink long
    // headlines so each stays on a single line instead of wrapping into the
    // device. hSize is applied by the automation.
    if (title.length * 0.58 * baseSize > availWidth) {
      entry.hSize = Math.max(64, Math.floor(availWidth / (title.length * 0.58)));
    }
    if (file) {
      entry.imageDataUrl = 'data:image/png;base64,' +
        fs.readFileSync(path.join(ASSETS, folder, file)).toString('base64');
    }
    return entry;
  });
}

async function main() {
  const translations = JSON.parse(fs.readFileSync(TRANSLATIONS, 'utf8'));
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(CFG.appUrl, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => typeof window.generateHeroScreenshots === 'function', { timeout: 30000 });

  for (const locale of CFG.locales) {
    const slides = loadSlides(translations, locale);
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
