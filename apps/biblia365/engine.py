import os
import json
import math
import re
import numpy as np
from collections import namedtuple
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURAÇÕES GLOBAIS ---
WIDTH, HEIGHT = 1290, 2796
TEXT_WIDTH = WIDTH - 260
ANCHOR_MARGIN = 200

# Variantes escuras e dessaturadas das próprias cores da marca
# (darkBackgroundColor, primaryColor, secondaryColor em biblia365-config.js),
# com luminância baixa o bastante pra texto branco/dourado manter contraste
# AA+ em qualquer ponto do frame -- o fundo inteiro é zona segura, não só
# uma faixa atrás do texto.
DEEP_NAVY = (6, 11, 22)     # darkBackgroundColor, como está
DEEP_PLUM = (35, 21, 46)    # secondaryColor #6A5FA7, escurecida
DEEP_EMBER = (44, 23, 15)   # primaryColor #CB7835, escurecida

# Ajuste fino do layout de texto
TEXT_TOP_MARGIN = 160
HEADLINE_LINE_HEIGHT_RATIO = 1.08
SUBHEAD_LINE_HEIGHT_RATIO = 1.35
HEADLINE_SUBHEAD_GAP_RATIO = 0.32
DEVICE_Y_MAX = 800
DEVICE_Y_FALLBACK = 750
GRADIENT_ANGLE_DEG = 132

GOLD_HIGHLIGHT = (255, 197, 92)
TextStyle = namedtuple("TextStyle", "color shadow_alpha")
HEADLINE_STYLE = TextStyle(color=(253, 253, 253), shadow_alpha=90)
SUBHEAD_STYLE = TextStyle(color=(210, 210, 220), shadow_alpha=70)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(APP_ROOT, "fonts")
ASSETS_DIR = os.path.join(APP_ROOT, "assets")
BASE_OUTPUT_DIR = os.path.join(APP_ROOT, "output")

# MAPEAMENTO DE LOCALE PARA PASTA DE ASSETS
LOCALE_TO_FOLDER = {
    "pt-BR": "pt", "pt-PT": "pt",
    "en-US": "en", "en-GB": "en", "en-AU": "en", "en-CA": "en",
    "es-419": "es", "es-ES": "es", "es-MX": "es",
    "fr-FR": "fr", "fr-CA": "fr",
    "id": "id", "fil": "fil", "de-DE": "de", "sw": "sw", "vi": "vi",
    "it-IT": "it", "nl-NL": "nl", "sv-SE": "sv",
    "pl-PL": "pl", "uk-UA": "uk", "am": "am"
}

# COREOGRAFIA CINEMATOGRÁFICA (8 SLIDES)
SLIDE_CONFIGS = {
    0: {"scale": 0.86, "angle": 5,  "x_off": 0},    # Home
    1: {"scale": 0.86, "angle": -4, "x_off": 60},   # Salmo 91
    2: {"scale": 0.89, "angle": 0,  "x_off": 0},    # Leitura
    3: {"scale": 0.86, "angle": 6,  "x_off": -70},  # Áudio
    4: {"scale": 0.86, "angle": -5, "x_off": 50},   # Traduções
    5: {"scale": 0.86, "angle": 4,  "x_off": -40},  # Social
    6: {"scale": 0.89, "angle": 0,  "x_off": 0},    # Tema Dark/Light
    7: {"scale": 0.86, "angle": -3, "x_off": 30},   # slot extra (não usado nas 7 telas atuais)
    8: {"scale": 0.86, "angle": 0,  "x_off": 0},    # slot extra (não usado nas 7 telas atuais)
}

def get_fonts(locale=None):
    # Para amárico, usar Kefa III (especializada em Ge'ez)
    if locale == "am":
        f_bold = "/System/Library/Fonts/Supplemental/KefaIII.ttf"
        f_semi = "/System/Library/Fonts/Supplemental/KefaIII.ttf"
        if not os.path.exists(f_bold): f_bold = "/System/Library/Fonts/Supplemental/Arial.ttf"
        if not os.path.exists(f_semi): f_semi = "/System/Library/Fonts/Supplemental/Arial.ttf"
        return ImageFont.truetype(f_bold, 95), ImageFont.truetype(f_semi, 52)

    # Para outros idiomas, usar Montserrat (bold no título, regular no
    # subtítulo -- contraste de peso é o que separa manchete de apoio,
    # não precisa mais do glow pra isso)
    f_bold = os.path.join(FONTS_DIR, "montserrat_bold.ttf")
    f_reg = os.path.join(FONTS_DIR, "montserrat.ttf")
    if not os.path.exists(f_bold): f_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    if not os.path.exists(f_reg): f_reg = "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(f_bold, 108), ImageFont.truetype(f_reg, 52)

def expand_bold_spans(text):
    """Um trecho **com várias palavras** é tokenizado como um bloco só pelo
    wrap_text, então um título todo em negrito e largo o bastante (ex.:
    "Hell- und Dunkelmodus" em alemão) não quebra linha e vaza pra fora do
    frame. Separar cada trecho em **tags** por palavra mantém a cor
    dourada em cada uma e deixa a quebra de linha normal funcionar."""
    return re.sub(r'\*\*([^*]+)\*\*', lambda m: ' '.join(f'**{w}**' for w in m.group(1).split()), text)

def wrap_text(text, draw, font, max_width):
    raw_tokens = re.findall(r'\*\*[^*]+\*\*|\S+', text)
    lines = []
    current = []
    current_w = 0
    space_w = draw.textlength(' ', font=font)
    for tok in raw_tokens:
        visible = tok.replace('**', '')
        tok_w = draw.textlength(visible, font=font)
        added = tok_w + (space_w if current else 0)
        if current and current_w + added > max_width:
            lines.append(' '.join(current))
            current = [tok]
            current_w = tok_w
        else:
            current.append(tok)
            current_w += added
    if current:
        lines.append(' '.join(current))
    return lines

def _draw_line_centered(draw, line, font, y, width, style):
    space_w = draw.textlength(' ', font=font)
    parts = re.findall(r'\*\*[^*]+\*\*|\S+', line)
    segments = []
    total_w = 0
    for i, part in enumerate(parts):
        is_hl = part.startswith('**') and part.endswith('**')
        visible = part.replace('**', '')
        w = draw.textlength(visible, font=font)
        segments.append((visible, is_hl, w))
        total_w += w
        if i < len(parts) - 1:
            total_w += space_w

    x = (width - total_w) / 2
    for visible, is_hl, w in segments:
        fill = GOLD_HIGHLIGHT if is_hl else style.color
        # Sombra suave única -- o contraste já vem do fundo (ver
        # draw_brand_background), não precisa mais do glow em 8 direções
        draw.text((x + 3, y + 3), visible, font=font, fill=(0, 0, 0, style.shadow_alpha))
        draw.text((x, y), visible, font=font, fill=fill)
        x += w + space_w

def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

def draw_brand_background(canvas, angle_deg=GRADIENT_ANGLE_DEG):
    """Um único gradiente diagonal contínuo entre 3 tons profundos da
    marca (navy -> ameixa -> âmbar). Cada stop já é escuro o bastante
    sozinho pra contraste AA+, então o frame inteiro é zona segura --
    sem costura, sem faixa de transição pra calcular."""
    xx, yy = np.meshgrid(np.arange(WIDTH), np.arange(HEIGHT))
    rad = math.radians(angle_deg)
    proj = xx * math.cos(rad) + yy * math.sin(rad)
    t = (proj - proj.min()) / (proj.max() - proj.min())
    t = smoothstep(t)

    out = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    half = t < 0.5
    t1 = np.clip(t / 0.5, 0, 1)
    t2 = np.clip((t - 0.5) / 0.5, 0, 1)
    for c in range(3):
        seg1 = DEEP_NAVY[c] + (DEEP_PLUM[c] - DEEP_NAVY[c]) * t1
        seg2 = DEEP_PLUM[c] + (DEEP_EMBER[c] - DEEP_PLUM[c]) * t2
        out[:, :, c] = np.where(half, seg1, seg2)

    img = Image.fromarray(out.astype(np.uint8), mode="RGB")
    canvas.paste(img, (0, 0))

def draw_text_block(canvas, headline, subheadline, f_h, f_s):
    """Desenha título + subtítulo centralizados e retorna a altura total
    do bloco, pra quem chamou posicionar o mockup do device logo abaixo."""
    draw = ImageDraw.Draw(canvas)
    headline = expand_bold_spans(headline)
    subheadline = expand_bold_spans(subheadline)
    h_lines = wrap_text(headline, draw, f_h, TEXT_WIDTH)
    s_lines = wrap_text(subheadline, draw, f_s, TEXT_WIDTH)
    h_lh = int(f_h.size * HEADLINE_LINE_HEIGHT_RATIO)
    s_lh = int(f_s.size * SUBHEAD_LINE_HEIGHT_RATIO)
    gap = int(f_h.size * HEADLINE_SUBHEAD_GAP_RATIO)

    curr_y = TEXT_TOP_MARGIN
    for line in h_lines:
        _draw_line_centered(draw, line, f_h, curr_y, WIDTH, HEADLINE_STYLE)
        curr_y += h_lh
    curr_y += gap
    for line in s_lines:
        _draw_line_centered(draw, line, f_s, curr_y, WIDTH, SUBHEAD_STYLE)
        curr_y += s_lh

    return (len(h_lines) * h_lh) + (len(s_lines) * s_lh) + gap

def process_screenshot(locale, idx, headline, subheadline, input_path, output_path, platform="android"):
    canvas = Image.new('RGB', (WIDTH, HEIGHT))
    draw_brand_background(canvas)

    f_h, f_s = get_fonts(locale)
    total_text_h = draw_text_block(canvas, headline, subheadline, f_h, f_s)

    device_y = TEXT_TOP_MARGIN + total_text_h + (ANCHOR_MARGIN // 2)
    if device_y > DEVICE_Y_MAX: device_y = DEVICE_Y_FALLBACK

    if os.path.exists(input_path):
        screen = Image.open(input_path).convert("RGBA")
        conf = SLIDE_CONFIGS.get(idx, SLIDE_CONFIGS[0])
        target_w = int(WIDTH * conf["scale"])
        aspect = screen.height / screen.width
        target_h = int(target_w * aspect)
        screen = screen.resize((target_w, target_h), Image.LANCZOS)
        
        # MOLDURAS REAIS (IDENTIDADE APPLE VS GOOGLE)
        if platform == "android":
            radius = 45
            border_col = (42,42,45) # Titanium Dark
            light_col = (80,80,85)
        else:
            radius = 80 # iPhone REAL arredondado
            border_col = (210, 210, 215) # Silver Titanium
            light_col = (245, 245, 250)

        mask = Image.new('L', (target_w, target_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, target_w, target_h], radius=radius, fill=255)
        
        device_layer = Image.new("RGBA", (target_w + 100, target_h + 100), (0,0,0,0))
        device_layer.paste(screen, (50, 50), mask)
        
        ImageDraw.Draw(device_layer).rounded_rectangle([50, 50, target_w+50, target_h+50], radius=radius, outline=border_col, width=22)
        ImageDraw.Draw(device_layer).rounded_rectangle([52, 52, target_w+48, target_h+48], radius=radius, outline=light_col, width=3)
        
        cam_x = (target_w + 100) // 2
        if platform == "android":
            ImageDraw.Draw(device_layer).ellipse([cam_x-10, 80, cam_x+10, 100], fill=(15,15,15))
        else:
            # Dynamic Island REAL para iPhone
            island_w, island_h = 135, 38
            ImageDraw.Draw(device_layer).rounded_rectangle([cam_x-(island_w//2), 75, cam_x+(island_w//2), 75+island_h], radius=18, fill=(10,10,10))
        
        if conf["angle"] != 0:
            device_layer = device_layer.rotate(conf["angle"], resample=Image.BICUBIC, expand=True)
        
        canvas.paste(device_layer, ((WIDTH-device_layer.width)//2 + conf["x_off"], device_y), device_layer)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, quality=100, subsampling=0)

def run_factory(target_platform=None, target_locale=None):
    trans_path = os.path.join(APP_ROOT, "biblia365-translations.json")
    with open(trans_path, 'r') as f:
        translations = json.load(f)

    def find_file(platform, folder, slide_idx):
        possible_names = [
            ["Home.png"],
            ["Lista de Devocionais.png", "Versiculo do Dia.png", "Versículo do Dia.png"],
            ["Leitura por Partes.png", "Devocional por Partes.png"],
            ["Bíblia em Áudio.png", "Bíblia em Áudio.png"],
            ["Biblia.png", "Bíblia.png"],
            ["Compartilhar Versiculo.png", "Compartilhar Versículo.png"],
            ["Tema Dark.png"],
            ["Lista de Devocionais.png", "Lista de Devocionais (novo).png"]
        ]
        if slide_idx >= len(possible_names): return None
        for name in possible_names[slide_idx]:
            p = os.path.join(ASSETS_DIR, platform, folder, name)
            if os.path.exists(p): return p
        return None

    print(f"🚀 Fábrica Bíblia 365 (Filtro: {target_platform or 'Todas'} / {target_locale or 'Todos'})...")
    
    platforms = [target_platform] if target_platform else ["android", "ios"]
    
    for platform in platforms:
        platform_asset_dir = os.path.join(ASSETS_DIR, platform)
        if not os.path.exists(platform_asset_dir): continue
        
        print(f"\n📱 Plataforma: {platform.upper()}")
        for locale, folder_name in LOCALE_TO_FOLDER.items():
            if target_locale and locale != target_locale: continue
            if locale not in translations: continue
            if not os.path.exists(os.path.join(platform_asset_dir, folder_name)): continue

            print(f"  📦 Locale: {locale}")
            slides = translations[locale]['slides']
            for i, slide_text in enumerate(slides):
                input_path = find_file(platform, folder_name, i)
                if input_path:
                    output_path = os.path.join(BASE_OUTPUT_DIR, platform, locale, f"slide_{i+1}.png")
                    process_screenshot(locale, i, slide_text[0], slide_text[1], input_path, output_path, platform=platform)
    
    print(f"\n🎉 Processamento concluído!")
    if target_platform and target_locale:
        os.system(f"open {BASE_OUTPUT_DIR}/{target_platform}/{target_locale}/slide_1.png")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["android", "ios", "all"], default="android")
    parser.add_argument("--locale", default="pt-BR")
    args = parser.parse_args()

    target_platform = None if args.platform == "all" else args.platform
    target_locale = None if args.locale == "all" else args.locale
    run_factory(target_platform=target_platform, target_locale=target_locale)
