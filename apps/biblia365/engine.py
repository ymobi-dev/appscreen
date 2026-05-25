import os
import json
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- CONFIGURAÇÕES GLOBAIS ---
WIDTH, HEIGHT = 1290, 2796
TEXT_WIDTH = WIDTH - 260
ANCHOR_MARGIN = 200 

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
    "id": "id", "fil": "fil", "de-DE": "de", "sw": "sw", "vi": "vi"
}

# COREOGRAFIA CINEMATOGRÁFICA (8 SLIDES)
SLIDE_CONFIGS = {
    0: {"scale": 0.86, "angle": 5,  "x_off": 0},    # Home
    1: {"scale": 0.86, "angle": -4, "x_off": 60},   # Salmo 91
    2: {"scale": 0.89, "angle": 0,  "x_off": 0},    # Leitura
    3: {"scale": 0.86, "angle": 6,  "x_off": -70},  # Áudio
    4: {"scale": 0.86, "angle": -5, "x_off": 50},   # Traduções
    5: {"scale": 0.86, "angle": 4,  "x_off": -40},  # Social
    6: {"scale": 0.89, "angle": 0,  "x_off": 0},    # Favoritos
    7: {"scale": 0.86, "angle": -3, "x_off": 30},   # Tema Dark/Light
}

def get_fonts():
    f_bold = os.path.join(FONTS_DIR, "montserrat_bold.ttf")
    f_semi = os.path.join(FONTS_DIR, "montserrat_semibold.ttf")
    if not os.path.exists(f_bold): f_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    if not os.path.exists(f_semi): f_semi = "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(f_bold, 110), ImageFont.truetype(f_semi, 58)

def wrap_text(text, draw, font, max_width):
    raw_tokens = os.path.join(APP_ROOT, "engine.py") # ignore, just internal ref
    import re
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

def _draw_line_centered(draw, line, font, y, width):
    import re
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
    for i, (visible, is_hl, w) in enumerate(segments):
        # Cores e Glows do usuário (Dourado para Destaque)
        color = (255, 200, 80) if is_hl else (253, 253, 253)
        glow_color = (255, 220, 130, 220) if is_hl else (255, 255, 255, 140)
        shadow_color = (0, 0, 0, 115) if is_hl else (0, 0, 0, 65)
        radius = 3 if is_hl else 2

        # Sombra
        draw.text((x + 4, y + 4), visible, font=font, fill=shadow_color)
        # Glow
        for off_x in (-radius, 0, radius):
            for off_y in (-radius, 0, radius):
                if off_x == 0 and off_y == 0: continue
                draw.text((x + off_x, y + off_y), visible, font=font, fill=glow_color)
        # Texto principal
        draw.text((x, y), visible, font=font, fill=color)

        x += w + (space_w if i < len(segments) - 1 else 0)

def create_vignette(width, height):
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i in range(int(height * 0.35)):
        alpha = int(140 * (1 - (i / (height * 0.35))))
        draw.line([(0, i), (width, i)], fill=(0, 0, 0, alpha))
    return overlay

def process_screenshot(locale, idx, headline, subheadline, input_path, output_path, total_slides, platform="android"):
    canvas = Image.new('RGB', (WIDTH, HEIGHT))
    
    # 1. Panorama Background
    bg_path = os.path.join(ASSETS_DIR, "background.png")
    if os.path.exists(bg_path):
        full_bg = Image.open(bg_path)
        bg_w, bg_h = full_bg.size
        target_full_w = int(HEIGHT * (bg_w / bg_h))
        full_bg_resized = full_bg.resize((target_full_w, HEIGHT), Image.LANCZOS)
        step = (target_full_w - WIDTH) // (total_slides - 1) if total_slides > 1 else 0
        left = idx * step
        canvas.paste(full_bg_resized.crop((left, 0, left + WIDTH, HEIGHT)), (0, 0))
    
    vignette = create_vignette(WIDTH, HEIGHT)
    canvas.paste(vignette, (0, 0), vignette)

    draw = ImageDraw.Draw(canvas)
    f_h, f_s = get_fonts()
    
    h_lines = wrap_text(headline, draw, f_h, TEXT_WIDTH)
    s_lines = wrap_text(subheadline, draw, f_s, TEXT_WIDTH)
    h_lh, s_lh, gap = 130, 75, 40
    total_text_h = (len(h_lines) * h_lh) + (len(s_lines) * s_lh) + gap
    
    y_text = ANCHOR_MARGIN
    device_y = y_text + total_text_h + (ANCHOR_MARGIN // 2)
    if device_y > 800: device_y = 750

    curr_y = y_text
    for line in h_lines:
        _draw_line_centered(draw, line, f_h, curr_y, WIDTH)
        curr_y += h_lh
    curr_y += gap
    for line in s_lines:
        _draw_line_centered(draw, line, f_s, curr_y, WIDTH)
        curr_y += s_lh

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
            ["Versiculo do Dia.png", "Versículo do Dia.png"],
            ["Leitura por Partes.png"],
            ["Bíblia em Áudio.png", "Bíblia em Áudio.png"],
            ["Biblia.png", "Bíblia.png"],
            ["Compartilhar Versiculo.png", "Compartilhar Versículo.png"],
            ["Favoritos.png"],
            ["Tema Dark.png"]
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
                    process_screenshot(locale, i, slide_text[0], slide_text[1], input_path, output_path, len(slides), platform=platform)
    
    print(f"\n🎉 Processamento concluído!")
    if target_platform and target_locale:
        os.system(f"open {BASE_OUTPUT_DIR}/{target_platform}/{target_locale}/slide_1.png")

if __name__ == "__main__":
    # Rodar apenas pt-BR do iPhone conforme solicitado
    run_factory(target_platform="ios", target_locale="pt-BR")
