// Central parameterization for the Bíblia 365 hero screenshot pipeline.
// Every knob is overridable via env vars so campaigns can be parameterized
// without touching code. Style is selected by VARIANT — each variant is a full
// theme + accent set, so the original working look can be regenerated
// side-by-side with new directions for A/B comparison.
//   VARIANT=aurora      VARIANT=navy-glow     (default) ...
// Run with:
//   NODE_PATH=$(npm root -g) VARIANT=aurora node apps/biblia365/generate-hero.cjs
const str = (v, d) => process.env[v] || d;

// Shared ASO copy layer (content, independent of style variant).
const copy = {
  'pt-BR': [
    { h: 'Bíblia 365', s: 'Leia a Bíblia inteira em um ano — 15 min por dia.' },
    { h: 'Um Plano Para Cada Momento', s: 'Jornadas devocionais prontas para nutrir sua fé.' },
    { h: 'Leia em 5 Minutos', s: 'Partes pequenas para ler sem sobrecarga.' },
    { h: 'Bíblia em Áudio', s: 'Ouça a Palavra narrada onde estiver.' },
    { h: 'Sua Versão Preferida', s: 'ACF, ARC e outras traduções fiéis ao original.' },
    { h: 'Família e Amigos', s: 'Compartilhe versículos com quem você ama.' },
    { h: 'Leia do Seu Jeito', s: 'Modo claro ou escuro, conforto em qualquer hora.' }
  ],
  'en-US': [
    { h: 'Bíblia 365', s: 'Read the whole Bible in a year — 15 min a day.' },
    { h: 'Devotional Journeys', s: 'Ready-made plans to nurture your faith daily.' },
    { h: 'Read in 5 Minutes', s: 'Chapters in small parts. All progress, no overwhelm.' },
    { h: 'Audio Bible', s: 'Hear the Word narrated wherever you are.' },
    { h: 'Your Preferred Version', s: 'ACF, ARC and other faithful translations.' },
    { h: 'Family & Friends', s: 'Share verses with the ones you love.' },
    { h: 'Light & Dark', s: 'Comfortable reading day or night.' }
  ]
};

// Style variants: the original working look plus new directions.
const VARIANTS = {
  // Original working look: 5-stop aurora gradient with a per-slide accent core
  // (accentInBgStops). Tight line height, cool subheadline, cold-gray text.
  aurora: {
    accents: ['#CB7835', '#6A5FA7', '#D98A4A', '#7B6FB8', '#C07A3A', '#5F4FA0', '#D98A4A'],
    theme: {
      bgStops: [
        { color: '#05070F', position: 0 }, { color: '#0B1330', position: 28 },
        { color: '#2A1E5C', position: 52 }, { color: '#0B1330', position: 76 },
        { color: '#05070F', position: 100 }
      ],
      bgAngle: 165,
      accentInBgStops: true,
      noise: true, noiseIntensity: 6,
      headlineSize: 100, headlineWeight: '700', headlineColor: '#ffffff',
      offsetY: 9, lineHeight: 104,
      subheadlineSize: 56, subheadlineWeight: '400', subheadlineColor: '#c9cfe0', subheadlineOpacity: 90,
      scale: 68, x: 50, y: 84,
      rotation3D: { x: -6, y: -10, z: 0 },
      cornerRadius: 28
    }
  },
  // New 2026 direction: subtle vertical navy base + warm radial glow behind the
  // device (accent feeds the glow), generous title->sub spacing, warm sub tone.
  // Sizes tuned for Montserrat (a wide geometric sans): headline auto-fits to
  // one line per slide (hSize from the runner); sub stays 1-2 lines.
  'navy-glow': {
    accents: ['#CB7835', '#D98A4A', '#C07A3A', '#E09A55', '#B56A2E', '#D08A3A', '#CB7835'],
    theme: {
      bgStops: [
        { color: '#0A0C16', position: 0 }, { color: '#111A30', position: 50 },
        { color: '#0B0E18', position: 100 }
      ],
      bgAngle: 90,
      glow: { x: 0.5, y: 0.64, radius: 0.6, opacity: 58, color: '#CB7835' },
      noise: true, noiseIntensity: 5,
      headlineSize: 96, headlineWeight: '700', headlineColor: '#ffffff',
      offsetY: 7, lineHeight: 126,
      subheadlineSize: 48, subheadlineWeight: '600', subheadlineColor: '#F0C989', subheadlineOpacity: 94,
      scale: 72, x: 50, y: 84,
      rotation3D: { x: -6, y: -10, z: 0 },
      cornerRadius: 28
    }
  }
};

// Per-platform bundle: everything about a store lane in one place, so switching
// platforms is a single env var (PLATFORM=ios) instead of five.
const PLATFORMS = {
  android: { outputDevice: 'android-phone', device3D: 'samsung', assetSource: 'android', frameColor: 'black', w: 1080, h: 1920 },
  ios: { outputDevice: 'iphone-6.9', device3D: 'iphone', assetSource: 'iphone', frameColor: 'natural', w: 1320, h: 2868 }
};

const platformName = str('PLATFORM', 'android');
const plat = PLATFORMS[platformName] || PLATFORMS.android;
// Individual knobs can still be overridden per-run; otherwise they follow the platform.
const outDevice = str('OUTPUT_DEVICE', plat.outputDevice);
const canvasDims = { 'android-phone': { w: 1080, h: 1920 }, 'iphone-6.9': { w: 1320, h: 2868 } }[outDevice] || { w: 1080, h: 1920 };

const variantName = str('VARIANT', 'navy-glow');
if (!VARIANTS[variantName]) {
  console.error(`Unknown VARIANT "${variantName}". Available: ${Object.keys(VARIANTS).join(', ')}`);
  process.exit(1);
}
const active = VARIANTS[variantName];

// The app's exact typeface is Montserrat (TTFs bundled in apps/biblia365/fonts,
// loaded by the automation via FontFace). Same on both store lanes.
const fontStack = 'Montserrat';
active.theme.headlineFont = active.theme.headlineFont || fontStack;
active.theme.subheadlineFont = active.theme.subheadlineFont || fontStack;

module.exports = {
  appUrl: str('APP_URL', 'http://localhost:8000'),

  // Selected style variant (output is namespaced per variant so both coexist).
  variant: variantName,
  variants: VARIANTS,

  // Platform bundle: PLATFORM=android (default) or PLATFORM=ios. Overridable per knob.
  platform: platformName,
  outputDevice: outDevice,
  device3D: str('DEVICE_3D', plat.device3D), // samsung | iphone
  assetSource: str('ASSET_SOURCE', plat.assetSource), // captures shown on the screen
  frameColor: str('FRAME_COLOR', plat.frameColor), // samsung presets | iphone: natural/blue/white/black/desert/deep-purple/gold/red
  canvasW: canvasDims.w,
  canvasH: canvasDims.h,

  // Scope: Android pt-BR first, then iOS pt-BR. More locales via env later.
  locales: str('LOCALES', 'pt-BR').split(',').map(s => s.trim()).filter(Boolean),

  // Asset folders use short codes; translations use locale keys.
  assetFolders: {
    'pt-BR': 'pt', 'pt-PT': 'pt', 'en-US': 'en', 'es-419': 'es', 'fr-FR': 'fr',
    'de-DE': 'de', 'it-IT': 'it', 'nl-NL': 'nl', 'sv-SE': 'sv', 'pl-PL': 'pl',
    'uk-UA': 'uk', 'id': 'id', 'fil': 'fil', 'sw': 'sw', 'vi': 'vi', 'am': 'am'
  },

  // Slide index -> asset filename (identical names in every locale folder).
  slideFiles: ['Home.png', 'Lista de Devocionais.png', 'Devocional por Partes.png',
    'Bíblia em Áudio.png', 'Biblia.png', 'Compartilhar Versiculo.png', 'Tema Dark.png'],

  // Resolved from the active variant.
  accents: active.accents,
  theme: active.theme,
  copy
};
