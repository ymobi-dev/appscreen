/**
 * Bíblia 365 Custom Configuration for App Store Screenshot Generator
 */

const BIBLIA365_CONFIG = {
    primaryColor: '#CB7835',
    secondaryColor: '#6A5FA7',
    tertiaryColor: '#B08A3C',
    backgroundColor: '#F5F1E8',
    darkBackgroundColor: '#060B16',
    
    locales: [
        { code: 'pt-BR', flag: '🇧🇷', name: 'Português (Brasil)' },
        { code: 'pt-PT', flag: '🇵🇹', name: 'Português (Portugal)' },
        { code: 'en-US', flag: '🇺🇸', name: 'English (US)' },
        { code: 'en-GB', flag: '🇬🇧', name: 'English (UK)' },
        { code: 'en-AU', flag: '🇦🇺', name: 'English (AU)' },
        { code: 'en-CA', flag: '🇨🇦', name: 'English (CA)' },
        { code: 'es-419', flag: '🌎', name: 'Español (LatAm)' },
        { code: 'es-ES', flag: '🇪🇸', name: 'Español (España)' },
        { code: 'fr-FR', flag: '🇫🇷', name: 'Français (France)' },
        { code: 'fr-CA', flag: '🇨🇦', name: 'Français (Canada)' },
        { code: 'id', flag: '🇮🇩', name: 'Indonesian' },
        { code: 'fil', flag: '🇵🇭', name: 'Filipino' },
        { code: 'de-DE', flag: '🇩🇪', name: 'Deutsch' },
        { code: 'sw', flag: '🇰🇪', name: 'Kiswahili' },
        { code: 'vi', flag: '🇻🇳', name: 'Tiếng Việt' }
    ],

    captions: {
        'pt-BR': [
            { title: 'Bíblia 365', subtitle: 'Leia a Bíblia diariamente em pequenas partes' },
            { title: 'Leitura por Partes', subtitle: 'Capítulos divididos em 5-10 minutos' },
            { title: 'Progresso Visual', subtitle: 'Sinta sua evolução com chips coloridos' },
            { title: 'Bíblia Offline', subtitle: 'Toda a Palavra de Deus sem internet' },
            { title: 'Áudio Completo', subtitle: 'Escute enquanto trabalha ou dirige' }
        ],
        'en-US': [
            { title: 'Bible 365', subtitle: 'Read the Bible daily in small sections' },
            { title: 'Read in Parts', subtitle: 'Chapters broken into 5-10 minute segments' },
            { title: 'Visual Progress', subtitle: 'See your evolution with color-coded chips' },
            { title: 'Offline Bible', subtitle: 'The whole Word of God without internet' },
            { title: 'Complete Audio', subtitle: 'Listen while you work or drive' }
        ]
    }
};

function applyBiblia365Theme() {
    if (typeof state === 'undefined') return;

    // Update state defaults
    state.defaults.background.gradient.stops = [
        { color: '#CB7835', position: 0 },
        { color: '#6A5FA7', position: 100 }
    ];
    state.defaults.background.angle = 135;
    
    // Update project languages
    state.projectLanguages = BIBLIA365_CONFIG.locales.map(l => l.code);
    
    // Refresh UI if hase functions
    if (typeof updateLanguageMenu === 'function') updateLanguageMenu();
    if (typeof renderSidebar === 'function') renderSidebar();
    
    console.log('✨ Bíblia 365 Theme Applied');
}

// Export for use in app.js
window.BIBLIA365_CONFIG = BIBLIA365_CONFIG;
window.applyBiblia365Theme = applyBiblia365Theme;
