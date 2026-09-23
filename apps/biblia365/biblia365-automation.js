/**
 * Bíblia 365 Automation Script
 * Optimized for previewing results with actual images
 */

// Registers the app's own Montserrat fonts (bold/semibold/regular TTFs) so the
// canvas headline/subheadline match the exact typeface the app uses in-app.
async function loadAppFonts() {
    const faces = [
        ['Montserrat', 400, 'montserrat.ttf'],
        ['Montserrat', 600, 'montserrat_semibold.ttf'],
        ['Montserrat', 700, 'montserrat_bold.ttf']
    ];
    for (const [name, weight, file] of faces) {
        const weightStr = String(weight);
        // Only skip if *we* already registered this face: document.fonts.check()
        // also matches system-installed fonts, which would silently bypass our
        // bundled TTFs and render the app typeface from a different cut.
        const registered = [...document.fonts].some(
            (f) => f.family === name && String(f.weight) === weightStr && f.status === 'loaded'
        );
        if (registered) continue;
        try {
            const resp = await fetch('apps/biblia365/fonts/' + file);
            if (!resp.ok) continue;
            const ff = new FontFace(name, await resp.arrayBuffer(), { weight: weightStr });
            await ff.load();
            document.fonts.add(ff);
        } catch (e) {
            /* fall back to system sans if a weight fails */
        }
    }
}

let translations = {};

async function loadTranslations() {
    try {
        const response = await fetch('biblia365-translations.json');
        translations = await response.json();
        console.log('✅ Translations loaded');
    } catch (e) {
        console.error('Failed to load translations', e);
    }
}

const BIBLIA365_THEMES = {
    light: {
        bgGradient: [{ color: '#F5F1E8', position: 0 }, { color: '#E0DCC9', position: 100 }],
        headlineColor: '#1B1E1F',
        subheadlineColor: '#4F3D22',
        frameColor: '#1d1d1f'
    },
    dark: {
        bgGradient: [{ color: '#CB7835', position: 0 }, { color: '#6A5FA7', position: 100 }],
        headlineColor: '#ffffff',
        subheadlineColor: '#E8ECF6',
        frameColor: '#ffffff'
    }
};

async function generateGlobalScreenshots(themeName = 'dark') {
    if (Object.keys(translations).length === 0) await loadTranslations();
    
    if (typeof state === 'undefined') return;

    const theme = BIBLIA365_THEMES[themeName] || BIBLIA365_THEMES.dark;
    const languages = Object.keys(translations);
    
    state.screenshots = [];
    state.projectLanguages = languages;
    state.currentLanguage = 'pt-BR';
    
    for (let i = 0; i < 8; i++) {
        const newScreenshot = {
            id: Date.now() + i,
            settings: JSON.parse(JSON.stringify(state.defaults)),
            localizedImages: {}
        };

        newScreenshot.settings.background.gradient.stops = theme.bgGradient;
        newScreenshot.settings.text.headlineColor = theme.headlineColor;
        newScreenshot.settings.text.subheadlineColor = theme.subheadlineColor;
        newScreenshot.settings.screenshot.frame.color = theme.frameColor;
        newScreenshot.settings.text.subheadlineEnabled = true;
        newScreenshot.settings.screenshot.scale = 75;
        newScreenshot.settings.screenshot.y = 55;
        newScreenshot.settings.screenshot.cornerRadius = 32;
        newScreenshot.settings.screenshot.frame.enabled = true;

        languages.forEach(lang => {
            const slideData = translations[lang].slides[i];
            if (slideData) {
                newScreenshot.settings.text.headlines[lang] = slideData[0];
                newScreenshot.settings.text.subheadlines[lang] = slideData[1];
                
                // Se for o slide 1 e idioma PT-BR, vamos tentar carregar a imagem que acabamos de salvar
                if (i === 0 && lang === 'pt-BR') {
                    // Nota: O navegador precisa de permissão ou a imagem deve estar acessível via local server
                    // Para facilitar o seu teste agora, vou deixar o nome do arquivo configurado
                    newScreenshot.localizedImages[lang] = { 
                        src: 'img/biblia365/slide_1_pt-BR.png', 
                        name: 'home_final.png' 
                    };
                } else {
                    newScreenshot.localizedImages[lang] = { src: '', name: `slide_${i+1}_${lang}.png` };
                }
            }
        });

        state.screenshots.push(newScreenshot);
    }

    if (typeof renderSidebar === 'function') renderSidebar();
    if (typeof selectScreenshot === 'function') selectScreenshot(0);
    if (typeof updateCanvas === 'function') updateCanvas();
    
    console.log('🚀 Lote de visualização carregado!');
}

/**
 * Hero screenshots (top-5 ASO): dark aurora background, headline on the top
 * third, 3D device bleeding off the bottom with a tilt and contact shadow.
 * Uses the SAME top-level structure createNewScreenshot builds (background/
 * screenshot/text keys) — the legacy generateGlobalScreenshots above writes
 * to a dead `settings` key the app never reads.
 */
async function generateHeroScreenshots(config) {
    if (typeof state === 'undefined') return 0;

    const locale = config.locale;
    const theme = config.theme || {};
    const slides = config.slides || [];

    state.screenshots = [];
    state.projectLanguages = [locale];
    state.currentLanguage = locale;
    if (config.outputDevice) state.outputDevice = config.outputDevice;

    // Ensure the app's own font is registered before rendering.
    await loadAppFonts();

    const loads = [];

    slides.forEach((slide, i) => {
        const text = JSON.parse(JSON.stringify(state.defaults.text));
        text.currentHeadlineLang = locale;
        text.headlineLanguages = [locale];
        text.headlines = { [locale]: slide.title || '' };
        text.currentSubheadlineLang = locale;
        text.subheadlineLanguages = [locale];
        text.subheadlines = { [locale]: slide.subtitle || '' };
        text.headlineEnabled = true;
        text.headlineSize = slide.hSize || theme.headlineSize || 118;
        text.headlineWeight = theme.headlineWeight || '700';
        text.headlineColor = theme.headlineColor || '#ffffff';
        if (theme.headlineFont) text.headlineFont = theme.headlineFont;
        if (theme.subheadlineFont) text.subheadlineFont = theme.subheadlineFont;
        text.position = theme.position || 'top';
        text.offsetY = theme.offsetY ?? 11;
        text.lineHeight = theme.lineHeight || 112;
        text.subheadlineEnabled = !!(slide.subtitle);
        text.subheadlineSize = theme.subheadlineSize || 46;
        text.subheadlineWeight = theme.subheadlineWeight || '400';
        text.subheadlineColor = theme.subheadlineColor || '#c9cfe0';
        text.subheadlineOpacity = theme.subheadlineOpacity ?? 85;

        const screenshot = JSON.parse(JSON.stringify(state.defaults.screenshot));
        screenshot.use3D = true;
        screenshot.device3D = config.device3D || theme.device3D || 'iphone';
        screenshot.scale = theme.scale ?? 82;
        screenshot.x = theme.x ?? 50;
        screenshot.y = theme.y ?? 58;
        screenshot.cornerRadius = theme.cornerRadius ?? 28;
        screenshot.rotation3D = { ...(theme.rotation3D || { x: -6, y: -10, z: 0 }) };
        screenshot.frame.enabled = false;
        if (config.frameColor || theme.frameColor) {
            screenshot.frameColor = config.frameColor || theme.frameColor;
        }

        const background = JSON.parse(JSON.stringify(state.defaults.background));
        background.type = 'gradient';
        if (theme.bgStops) {
            background.gradient.stops = theme.bgStops.map(s => ({ ...s }));
            // Legacy variants (accentInBgStops) inject the slide accent into the
            // aurora core; new variants feed it to the radial glow instead.
            if (theme.accentInBgStops && slide.accent && background.gradient.stops.length >= 5) {
                background.gradient.stops[2].color = slide.accent;
            }
        }
        if (theme.glow) {
            background.gradient.glow = { ...theme.glow, color: slide.accent || theme.glow.color };
        }
        if (theme.bgAngle) background.gradient.angle = theme.bgAngle;
        background.noise = !!theme.noise;
        if (theme.noiseIntensity) background.noiseIntensity = theme.noiseIntensity;

        const entry = {
            image: null,
            name: slide.name || 'Slide ' + (i + 1),
            deviceType: screenshot.device3D,
            localizedImages: {},
            background: background,
            screenshot: screenshot,
            text: text,
            elements: [],
            popouts: [],
            overrides: {}
        };

        if (slide.imageDataUrl) {
            loads.push(new Promise((resolve) => {
                const img = new Image();
                img.onload = () => {
                    entry.localizedImages[locale] = { image: img, src: slide.imageDataUrl, name: entry.name };
                    resolve();
                };
                img.onerror = () => resolve();
                img.src = slide.imageDataUrl;
            }));
        }
        state.screenshots.push(entry);
    });

    await Promise.all(loads);

    if (typeof renderSidebar === 'function') renderSidebar();
    if (typeof selectScreenshot === 'function') selectScreenshot(0);
    if (typeof updateSidePreviews === 'function') updateSidePreviews();
    if (typeof updateCanvas === 'function') updateCanvas();

    return state.screenshots.length;
}

window.generateHeroScreenshots = generateHeroScreenshots;
loadTranslations();
