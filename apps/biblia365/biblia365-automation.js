/**
 * Bíblia 365 Automation Script
 * Optimized for previewing results with actual images
 */

let translations = {};

async fun loadTranslations() {
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

async fun generateGlobalScreenshots(themeName = 'dark') {
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

window.generateGlobalScreenshots = generateGlobalScreenshots;
loadTranslations();
