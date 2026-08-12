/**
 * EMET Assist hero automation.
 * Mirrors apps/biblia365/biblia365-automation.js (same top-level structure the
 * main app reads: background/screenshot/text), but loads EMET's own fonts and
 * renders slides purely from the runner's copy -- no translations file.
 */
async function loadAppFonts() {
    const faces = [
        ['Montserrat', 400, 'montserrat.ttf'],
        ['Montserrat', 600, 'montserrat_semibold.ttf'],
        ['Montserrat', 700, 'montserrat_bold.ttf']
    ];
    for (const [name, weight, file] of faces) {
        const weightStr = String(weight);
        const registered = [...document.fonts].some(
            (f) => f.family === name && String(f.weight) === weightStr && f.status === 'loaded'
        );
        if (registered) continue;
        try {
            const resp = await fetch('apps/emet-assist/fonts/' + file);
            if (!resp.ok) continue;
            const ff = new FontFace(name, await resp.arrayBuffer(), { weight: weightStr });
            await ff.load();
            document.fonts.add(ff);
        } catch (e) {
            /* fall back to system sans if a weight fails */
        }
    }
}

/**
 * Hero screenshots (Play Store): dark green/mint gradient, headline on the top
 * third, 3D device bleeding off the bottom with a tilt and contact shadow.
 * Uses the SAME structure the main app's createNewScreenshot builds, so
 * updateCanvas renders it with zero app changes.
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
