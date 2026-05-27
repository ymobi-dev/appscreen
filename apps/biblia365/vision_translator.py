import os
import json
from PIL import Image, ImageDraw, ImageFont

# Dados extraídos do codebase e analisados pelo agente
TRANSLATIONS = {
    "pt-BR": {
        "hello": "Olá",
        "journey": "Sua jornada de leitura",
        "sequential": "Leitura sequencial",
        "genesis": "De Gênesis ao Apocalipse",
        "annual": "Progresso anual",
        "where": "Onde você parou",
        "continue": "Continuar leitura",
        "verse": "Versículo do dia"
    },
    "en-US": {
        "hello": "Hello",
        "journey": "Your reading journey",
        "sequential": "Sequential reading",
        "genesis": "From Genesis to Revelation",
        "annual": "Annual progress",
        "where": "Where you stopped",
        "continue": "Continue reading",
        "verse": "Verse of the day"
    }
}

# Coordenadas aproximadas (Normalizadas para 0.0 - 1.0 baseadas no print 1080x2400 do Android)
COORDS = {
    "hello": {"x": 0.12, "y": 0.17, "size": 90, "bold": True},
    "journey": {"x": 0.12, "y": 0.22, "size": 45, "bold": False},
    "sequential": {"x": 0.22, "y": 0.31, "size": 48, "bold": True},
    "genesis": {"x": 0.22, "y": 0.35, "size": 38, "bold": False},
    "annual": {"x": 0.10, "y": 0.40, "size": 36, "bold": False},
    "where": {"x": 0.10, "y": 0.49, "size": 42, "bold": True},
    "continue": {"x": 0.50, "y": 0.81, "size": 42, "bold": True, "center": True},
    "verse": {"x": 0.22, "y": 0.93, "size": 42, "bold": True}
}

def translate_ui(input_path, output_path, lang_to):
    img = Image.open(input_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    # Fontes (usando as mesmas do app que copiamos antes)
    font_path_bold = "/Users/yuripacheco/Projetos/appscreen/apps/biblia365/fonts/montserrat_bold.ttf"
    font_path_reg = "/Users/yuripacheco/Projetos/appscreen/apps/biblia365/fonts/montserrat.ttf"
    
    for key, data in COORDS.items():
        text_pt = TRANSLATIONS["pt-BR"][key]
        text_en = TRANSLATIONS[lang_to][key]
        
        # 1. "Apagar" o texto original (Criando uma máscara com a cor do fundo)
        # Em um sistema real, usaríamos Inpainting, aqui vamos sobrepor com patch de cor
        # ou apenas desenhar por cima se o fundo for sólido o suficiente
        x, y = int(data["x"] * w), int(data["y"] * h)
        font_size = int(data["size"] * (w / 1080))
        font = ImageFont.truetype(font_path_bold if data["bold"] else font_path_reg, font_size)
        
        # Cor do texto no app (Geralmente #1B1E1F ou variações de cinza)
        text_color = (27, 30, 31, 255)
        
        # Centralização se necessário
        draw_x = x
        if data.get("center"):
            tw = draw.textlength(text_en, font=font)
            draw_x = x - (tw / 2)
            
        # Para este teste, vamos apenas desenhar o texto traduzido em cima
        # (Em produção, o app mudaria o locale e tiraríamos o print real)
        draw.text((draw_x, y), text_en, font=font, fill=text_color)
        
    img.save(output_path)
    print(f"✅ UI Traduzida (POC): {output_path}")

if __name__ == "__main__":
    input_p = "/Users/yuripacheco/Projetos/appscreen/apps/biblia365/assets/slide_1_pt-BR.png"
    output_p = "/Users/yuripacheco/Projetos/appscreen/output_validation/translated_test_en.png"
    if os.path.exists(input_p):
        translate_ui(input_p, output_p, "en-US")
        os.system(f"open {output_p}")
