// EMET hero screenshot pipeline config.
// Knobs are env-overridable so campaigns can be parameterized without code.
// Style is selected by VARIANT -- emet-mint is the app's own identity
// (deep forest green + electric mint, from core/designsystem/theme/Color.kt).
//   VARIANT=emet-mint node apps/emet-assist/generate-hero.cjs
const str = (v, d) => process.env[v] || d;

// Shared ASO copy layer (content, independent of style variant). Slide order
// matches the capture phases of the preview walk: home, scanner confirm sheet,
// basket, audit input, audit result, audit alert (register overcharged -> EMET
// flags it). The price-compare slide (scanner chips) is intentionally excluded
// from the Play graphics.
const copy = {
  'pt-BR': [
    { h: 'EMET', s: 'Seu escudo de preços no mercado.' },
    { h: 'Preço Certo, Já', s: 'Confirme o valor e evite pegadinha.' },
    { h: 'Cesta Sob Controle', s: 'Acompanhe o total enquanto você escolhe.' },
    { h: 'Confira Antes de Pagar', s: 'Digite o valor do caixa e compare na hora.' },
    { h: 'Tudo Certo no Caixa', s: 'Preços conferidos — economize com confiança.' },
    { h: 'Caixa Cobrou a Mais?', s: 'A EMET alerta na hora. Revise e não pague a mais.' }
  ],
  'en-US': [
    { h: 'EMET', s: 'Your price shield at the store.' },
    { h: 'Right Price, Right Now', s: 'Confirm the value and skip the trick.' },
    { h: 'Cart Under Control', s: 'Track the total while you shop.' },
    { h: 'Check Before You Pay', s: 'Type the register total and compare instantly.' },
    { h: 'All Checks Out', s: 'Prices verified — save with confidence.' },
    { h: 'Overcharged?', s: 'EMET flags it instantly. Review and pay less.' }
  ]
};

// Style variants: the app identity plus room for future A/B directions.
const VARIANTS = {
  // EMET identity: 5-stop deep-forest gradient, per-slide mint radial glow
  // behind the device (accent feeds the glow), white headline, mint sub.
  'emet-mint': {
    accents: ['#2E9872', '#91F6CA', '#34B386', '#7FE8BC', '#2E9872', '#4FC398'],
    theme: {
      bgStops: [
        { color: '#04211A', position: 0 }, { color: '#06382B', position: 35 },
        { color: '#0A5C41', position: 60 }, { color: '#06382B', position: 85 },
        { color: '#04211A', position: 100 }
      ],
      bgAngle: 160,
      glow: { x: 0.5, y: 0.62, radius: 0.62, opacity: 52, color: '#2E9872' },
      noise: true, noiseIntensity: 5,
      headlineSize: 92, headlineWeight: '700', headlineColor: '#ffffff',
      offsetY: 8, lineHeight: 118,
      subheadlineSize: 46, subheadlineWeight: '500', subheadlineColor: '#91F6CA', subheadlineOpacity: 95,
      scale: 70, x: 50, y: 84,
      rotation3D: { x: -6, y: -10, z: 0 },
      cornerRadius: 28
    }
  }
};

// Per-platform bundle: everything about a store lane in one place.
const PLATFORMS = {
  android: { outputDevice: 'android-phone', device3D: 'samsung', assetSource: 'android', frameColor: 'black', w: 1080, h: 1920 },
  ios: { outputDevice: 'iphone-6.9', device3D: 'iphone', assetSource: 'iphone', frameColor: 'natural', w: 1320, h: 2868 }
};

const platformName = str('PLATFORM', 'android');
const plat = PLATFORMS[platformName] || PLATFORMS.android;
const outDevice = str('OUTPUT_DEVICE', plat.outputDevice);
const canvasDims = { 'android-phone': { w: 1080, h: 1920 }, 'iphone-6.9': { w: 1320, h: 2868 } }[outDevice] || { w: 1080, h: 1920 };

const variantName = str('VARIANT', 'emet-mint');
if (!VARIANTS[variantName]) {
  console.error(`Unknown VARIANT "${variantName}". Available: ${Object.keys(VARIANTS).join(', ')}`);
  process.exit(1);
}
const active = VARIANTS[variantName];

// EMET uses the Android default sans (Roboto); Montserrat (bundled, geometric
// sans) is the closest free proxy and matches the biblia365 lane's type.
const fontStack = 'Montserrat';
active.theme.headlineFont = active.theme.headlineFont || fontStack;
active.theme.subheadlineFont = active.theme.subheadlineFont || fontStack;

module.exports = {
  appUrl: str('APP_URL', 'http://localhost:8000'),

  variant: variantName,
  variants: VARIANTS,

  platform: platformName,
  outputDevice: outDevice,
  device3D: str('DEVICE_3D', plat.device3D), // samsung | iphone
  assetSource: str('ASSET_SOURCE', plat.assetSource), // captures shown on the screen
  frameColor: str('FRAME_COLOR', plat.frameColor), // samsung presets | iphone presets
  canvasW: canvasDims.w,
  canvasH: canvasDims.h,

  // Scope: Android pt-BR first, then en-US. More locales via env later.
  locales: str('LOCALES', 'pt-BR,en-US').split(',').map(s => s.trim()).filter(Boolean),

  // Asset folders use short codes.
  assetFolders: { 'pt-BR': 'pt', 'en-US': 'en' },

  // Slide index -> asset filename (identical names in every locale folder).
  slideFiles: ['home.png', 'scanner_sheet.png', 'basket.png', 'audit_input.png', 'audit_result.png', 'audit_alert.png'],

  accents: active.accents,
  theme: active.theme,
  copy
};
