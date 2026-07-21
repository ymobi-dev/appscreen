#!/usr/bin/env python3
"""
Preview-only script for the app-screen text/scrim redesign proposal.
Reuses engine.py's device compositing untouched; only replaces the
text + scrim drawing logic. Not part of the production pipeline.
"""
import os
import json
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import engine as E

APP_ROOT = E.APP_ROOT
WIDTH, HEIGHT = E.WIDTH, E.HEIGHT
TEXT_WIDTH = E.TEXT_WIDTH


def expand_bold_spans(text):
    """wrap_text's tokenizer treats a whole **multi word** span as one
    unbreakable token, so a long fully-bolded headline (e.g. German
    "Hell- und Dunkelmodus") can't wrap and overflows the frame. Splitting
    each bold span into per-word **tags** keeps the gold color per word
    while letting normal word-wrap do its job."""
    return re.sub(r'\*\*([^*]+)\*\*', lambda m: ' '.join(f'**{w}**' for w in m.group(1).split()), text)


def get_fonts_after(locale=None):
    f_bold = os.path.join(E.FONTS_DIR, "montserrat_bold.ttf")
    f_reg = os.path.join(E.FONTS_DIR, "montserrat.ttf")
    return ImageFont.truetype(f_bold, 108), ImageFont.truetype(f_reg, 52)


# Deep, desaturated variants of the brand's own hues (biblia365-config.js:
# darkBackgroundColor, primaryColor, secondaryColor) mixed low enough in
# luminance that white/gold text keeps AA+ contrast everywhere in the
# frame -- no "safe zone" vs "rest of the image" split needed.
DEEP_NAVY = (6, 11, 22)     # darkBackgroundColor, as-is
DEEP_PLUM = (35, 21, 46)    # secondaryColor #6A5FA7, pulled dark
DEEP_EMBER = (44, 23, 15)   # primaryColor #CB7835, pulled dark


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def draw_brand_background(canvas, angle_deg=132):
    """One continuous diagonal gradient across three deep brand tones
    (navy -> plum -> ember). Every stop is dark enough on its own for
    AA+ text contrast, so the whole frame is a safe zone -- no seam,
    no separate transition band to get right."""
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


def draw_line_after(draw, line, font, y, width, color, shadow_alpha):
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
    for visible, is_hl, w in segments:
        fill = (255, 197, 92) if is_hl else color
        draw.text((x + 3, y + 3), visible, font=font, fill=(0, 0, 0, shadow_alpha))
        draw.text((x, y), visible, font=font, fill=fill)
        x += w + space_w


def process_after(locale, idx, headline, subheadline, input_path, output_path, total_slides, platform="ios"):
    canvas = Image.new('RGB', (WIDTH, HEIGHT))
    measure_draw = ImageDraw.Draw(canvas)
    f_h, f_s = get_fonts_after(locale)

    headline = expand_bold_spans(headline)
    subheadline = expand_bold_spans(subheadline)
    h_lines = E.wrap_text(headline, measure_draw, f_h, TEXT_WIDTH)
    s_lines = E.wrap_text(subheadline, measure_draw, f_s, TEXT_WIDTH)
    h_lh = int(f_h.size * 1.08)
    s_lh = int(f_s.size * 1.35)
    gap = int(f_h.size * 0.32)

    total_text_h = (len(h_lines) * h_lh) + (len(s_lines) * s_lh) + gap
    draw_brand_background(canvas)
    draw = ImageDraw.Draw(canvas)

    y_text = 160
    device_y = y_text + total_text_h + (E.ANCHOR_MARGIN // 2)
    if device_y > 800:
        device_y = 750

    curr_y = y_text
    for line in h_lines:
        draw_line_after(draw, line, f_h, curr_y, WIDTH, (253, 253, 253), 90)
        curr_y += h_lh
    curr_y += gap
    for line in s_lines:
        draw_line_after(draw, line, f_s, curr_y, WIDTH, (210, 210, 220), 70)
        curr_y += s_lh

    if os.path.exists(input_path):
        screen = Image.open(input_path).convert("RGBA")
        conf = E.SLIDE_CONFIGS.get(idx, E.SLIDE_CONFIGS[0])
        target_w = int(WIDTH * conf["scale"])
        aspect = screen.height / screen.width
        target_h = int(target_w * aspect)
        screen = screen.resize((target_w, target_h), Image.LANCZOS)

        if platform == "android":
            radius, border_col, light_col = 45, (42, 42, 45), (80, 80, 85)
        else:
            radius, border_col, light_col = 80, (210, 210, 215), (245, 245, 250)

        mask = Image.new('L', (target_w, target_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, target_w, target_h], radius=radius, fill=255)

        device_layer = Image.new("RGBA", (target_w + 100, target_h + 100), (0, 0, 0, 0))
        device_layer.paste(screen, (50, 50), mask)
        ImageDraw.Draw(device_layer).rounded_rectangle([50, 50, target_w + 50, target_h + 50], radius=radius, outline=border_col, width=22)
        ImageDraw.Draw(device_layer).rounded_rectangle([52, 52, target_w + 48, target_h + 48], radius=radius, outline=light_col, width=3)

        cam_x = (target_w + 100) // 2
        if platform == "android":
            ImageDraw.Draw(device_layer).ellipse([cam_x - 10, 80, cam_x + 10, 100], fill=(15, 15, 15))
        else:
            island_w, island_h = 135, 38
            ImageDraw.Draw(device_layer).rounded_rectangle([cam_x - (island_w // 2), 75, cam_x + (island_w // 2), 75 + island_h], radius=18, fill=(10, 10, 10))

        if conf["angle"] != 0:
            device_layer = device_layer.rotate(conf["angle"], resample=Image.BICUBIC, expand=True)

        canvas.paste(device_layer, ((WIDTH - device_layer.width) // 2 + conf["x_off"], device_y), device_layer)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, quality=100, subsampling=0)


# Mirrors engine.py's find_file possible_names exactly (kept in sync by
# hand -- this is a preview script, not the source of truth).
POSSIBLE_NAMES = [
    ["Home.png"],
    ["Lista de Devocionais.png", "Versiculo do Dia.png", "Versículo do Dia.png"],
    ["Leitura por Partes.png", "Devocional por Partes.png"],
    ["Bíblia em Áudio.png", "Bíblia em Áudio.png"],
    ["Biblia.png", "Bíblia.png"],
    ["Compartilhar Versiculo.png", "Compartilhar Versículo.png"],
    ["Tema Dark.png"],
    ["Lista de Devocionais.png", "Lista de Devocionais (novo).png"],
]


def find_file(platform, folder, slide_idx):
    if slide_idx >= len(POSSIBLE_NAMES):
        return None
    for name in POSSIBLE_NAMES[slide_idx]:
        p = os.path.join(E.ASSETS_DIR, platform, folder, name)
        if os.path.exists(p):
            return p
    return None


if __name__ == "__main__":
    trans = json.load(open(os.path.join(APP_ROOT, "biblia365-translations.json")))
    LOCALES = {"en-US": "en", "de-DE": "de"}
    for locale, folder in LOCALES.items():
        slides = trans[locale]["slides"]
        out_dir = os.path.join(APP_ROOT, "output", "preview_after", locale)
        for idx in range(len(slides)):
            input_path = find_file("ios", folder, idx)
            if not input_path:
                print(f"skip {locale} slide {idx+1}: asset not found")
                continue
            headline, subheadline = slides[idx]
            output_path = os.path.join(out_dir, f"slide_{idx+1}.png")
            process_after(locale, idx, headline, subheadline, input_path, output_path, len(slides), platform="ios")
            print("done", output_path)
