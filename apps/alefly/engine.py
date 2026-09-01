import os
import glob
import json
import math
import re
import argparse
import numpy as np
from collections import namedtuple
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURAÇÕES GLOBAIS DE CANVAS ---
# conf["x_off"]/conf["scale"] in SLIDE_CONFIGS were tuned against this width -
# every platform's x_off scales relative to it, so it must stay the iOS width
# even though other platforms render on their own canvas.
REFERENCE_WIDTH = WIDTH = 1290
HEIGHT = 2796
# Google Play's promotion eligibility requires portrait phone screenshots at
# TRUE 9:16 (not just under the general 2:1 upload ceiling) - the iOS canvas
# above is 2796/1290 = 2.17:1 and fails that. 1290x2292 (~1.7767) only
# approximates 16:9 (1.7778) and the Play Console eligibility checker kept
# flagging it, so this uses an EXACT 16:9 ratio instead (1287 = 9*143,
# 2288 = 16*143 - integer multiples, ratio is bit-exact, not just close).
ANDROID_WIDTH, ANDROID_HEIGHT = 1287, 2288
ANCHOR_MARGIN = 200

TEXT_TOP_MARGIN = 160
HEADLINE_LINE_HEIGHT_RATIO = 1.08
SUBHEAD_LINE_HEIGHT_RATIO = 1.35
HEADLINE_SUBHEAD_GAP_RATIO = 0.32
DEVICE_Y_MAX = 800
DEVICE_Y_FALLBACK = 750
# Android's canvas is ~8% shorter than iOS's (2560 vs 2796) - reusing the iOS
# thresholds left too little bottom margin for the device mockup, so it needs
# its own values scaled down.
DEVICE_Y_MAX_ANDROID = 670
DEVICE_Y_FALLBACK_ANDROID = 626
GRADIENT_ANGLE_DEG = 135

GOLD_HIGHLIGHT = (255, 215, 0)
TextStyle = namedtuple("TextStyle", "color shadow_alpha")
HEADLINE_STYLE = TextStyle(color=(255, 255, 255), shadow_alpha=90)
SUBHEAD_STYLE = TextStyle(color=(220, 225, 235), shadow_alpha=70)

# Caminhos base
ALEFLY_STORE_ASSETS = "/Users/yuripacheco/Projetos/alefly/store-assets"
APPSCREEN_ROOT = "/Users/yuripacheco/Projetos/appscreen"
FONTS_DIR = os.path.join(APPSCREEN_ROOT, "apps", "biblia365", "fonts")

# TENANTS ATIVOS NAS LOJAS E SUAS CONFIGURAÇÕES DE DESIGN
TENANT_CONFIGS = {
    "flamengo": {
        "name": "Quiz para Fãs do Fla",
        "colors": [(26, 0, 0), (122, 0, 0), (26, 26, 26)],
        "highlight_color": (255, 70, 70),
        "slides": [
            ("Desafie seus conhecimentos **de Futebol**", "O quiz definitivo para a torcida apaixonada"),
            ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
            ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e tempo em cada partida"),
            ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
        ]
    },
    "botafogo": {
        "name": "Quiz para Fãs do Botafogo",
        "colors": [(13, 11, 6), (30, 26, 16), (10, 10, 10)],
        "highlight_color": (232, 232, 232),
        "slides": [
            ("Testes sobre a história do **Glorioso**", "O quiz feito para a torcida botafoguense"),
            ("Configure seu **Modo de Jogo**", "Escolha o número de perguntas e ative dicas extras"),
            ("Métricas de **Pontuação e Tempo**", "Evolua sua precisão a cada nova rodada"),
            ("Crie sua **Streak Diária**", "Desafie-se diariamente e acompanhe sua evolução")
        ]
    },
    "fluminense": {
        "name": "Quiz para Fãs do Fluminense",
        "colors": [(13, 4, 5), (74, 14, 26), (10, 5, 5)],
        "highlight_color": (0, 168, 107),
        "slides": [
            ("Tudo sobre o **Tricolor das Laranjeiras**", "O quiz feito para os torcedores do Fluminense"),
            ("Personalize a **Sua Rodada**", "Perguntas com ou sem dicas no seu ritmo"),
            ("Resumo com **Aproveitamento Completo**", "Acompanhe acertos, tempo e pontuação total"),
            ("Mantenha seu **Ritmo de Estudos**", "Construa sua sequência diária de partidas")
        ]
    },
    "vasco": {
        "name": "Quiz para Fãs do Vasco",
        "colors": [(10, 10, 10), (26, 26, 26), (5, 5, 5)],
        "highlight_color": (224, 224, 224),
        "slides": [
            ("História Respeitada do **Gigante da Colina**", "Testes desafiadores para os vascaínos"),
            ("Escolha o **Tamanho do Desafio**", "Partidas personalizadas de 5 a 20 perguntas"),
            ("Estatísticas e **Score em Tempo Real**", "Analise seu tempo e precisão nas respostas"),
            ("Fortaleça sua **Sequência Diária**", "Jogue todos os dias para acumular pontos de Streak")
        ]
    },
    "worldcup": {
        "name": "Quiz para fãs da Copa",
        "colors": [(8, 21, 40), (21, 57, 97), (6, 15, 30)],
        "highlight_color": (46, 204, 113),
        "slides": [
            ("O Maior Quiz **de Futebol Mundial**", "Reviva todas as edições do maior torneio da Terra"),
            ("Monte o **Seu Desafio**", "Jogue rodadas rápidas ou longas com opção de dicas"),
            ("Métricas de **Pontuação e Desempenho**", "Acompanhe seu nível de conhecimento em cada jogo"),
            ("Crie uma **Sequência Campeã**", "Treine diariamente para manter seu Streak ativo")
        ]
    },
    "bible": {
        "name": "Quiz da Bíblia",
        "colors": [(8, 21, 40), (22, 46, 84), (6, 15, 30)],
        "highlight_color": (201, 149, 44),
        "slides": [
            ("Aprenda a **Palavra de Deus** jogando", "Perguntas e respostas sobre o Antigo e Novo Testamento"),
            ("Ajuste as **Configurações da Rodada**", "Escolha de 5 a 20 perguntas com auxílio de dicas"),
            ("Resumo com **Tempo e Acertos**", "Acompanhe seu progresso e aproveitamento bíblico"),
            ("Hábito Diário de **Estudo Bíblico**", "Mantenha sua sequência diária ativada todos os dias")
        ]
    },
    "geography-world": {
        "name": "Quiz Geografia Mundial",
        "colors": [(15, 43, 31), (27, 67, 50), (10, 30, 20)],
        "highlight_color": (82, 183, 136),
        "slides": [
            ("Explore o Mundo com **Desafios Geográficos**", "Bandeiras, capitais, mapas e curiosidades dos países"),
            ("Partidas **Rápidas e Personalizadas**", "Defina a quantidade de questões e nível de ajuda"),
            ("Análise de **Aproveitamento Mundial**", "Veja seu tempo médio e total de acertos por quiz"),
            ("Construa sua **Streak de Conhecimento**", "Pratique diariamente para manter sua sequência viva")
        ]
    },
    "enem-matematica": {
        "name": "ENEM Matemática: Questões",
        "colors": [(3, 30, 20), (5, 50, 30), (2, 20, 15)],
        "highlight_color": (0, 229, 117),
        "slides": [
            ("Domine a prova de **Matemática do ENEM**", "Questões oficiais com gabarito comentado e dicas"),
            ("Simulados **100% Personalizados**", "Treine rodadas de 5, 10, 15 ou 20 questões no seu ritmo"),
            ("Estatísticas e **Tempo de Resposta**", "Acompanhe seu aproveitamento e média de tempo por questão"),
            ("Construa sua **Sequência de Estudos**", "Pratique todos os dias e turbine sua pontuação no ENEM")
        ]
    },
    "enem-portugues": {
        "name": "ENEM Linguagens: Questões",
        "colors": [(30, 24, 6), (55, 42, 10), (20, 16, 4)],
        "highlight_color": (255, 208, 67),
        "slides": [
            ("Domine a prova de **Linguagens do ENEM**", "Questões oficiais de Língua Portuguesa e Literatura"),
            ("Treine com **Simulados Focados**", "Escolha 5, 10, 15 ou 20 perguntas com dicas inteligentes"),
            ("Análise de **Desempenho e Acertos**", "Acompanhe sua evolução e tempo de resolução"),
            ("Mantenha sua **Streak de Estudos**", "Crie o hábito de praticar diariamente para o ENEM")
        ]
    },
    "enem-humanas": {
        "name": "ENEM Humanas: Questões",
        "colors": [(20, 12, 35), (42, 25, 75), (14, 8, 25)],
        "highlight_color": (167, 139, 250),
        "slides": [
            ("Domine a prova de **Ciências Humanas**", "Questões de História, Geografia, Filosofia e Sociologia"),
            ("Simulados no **Seu Próprio Ritmo**", "Rodadas personalizadas com opções de dicas eliminatórias"),
            ("Resumo Completo de **Aproveitamento**", "Acompanhe acertos, tempo gasto e métricas de precisão"),
            ("Construa sua **Rotina Diária**", "Estude todos os dias e mantenha sua sequência ativa")
        ]
    },
    "enem-natureza": {
        "name": "ENEM Natureza: Questões",
        "colors": [(4, 25, 30), (10, 48, 55), (3, 18, 22)],
        "highlight_color": (20, 184, 166),
        "slides": [
            ("Domine a prova de **Ciências da Natureza**", "Questões oficiais de Biologia, Física e Química"),
            ("Simulados **Rápidos e Eficientes**", "Treine de 5 a 20 questões com gabarito e dicas"),
            ("Métricas de **Precisão e Velocidade**", "Analise seu tempo por questão e taxa de acertos"),
            ("Fortaleça sua **Sequência de Estudos**", "Treine diariamente e conquiste sua vaga na universidade")
        ]
    },
    "corinthians": {
        "name": "Quiz para Fãs do Corinthians",
        "colors": [(17, 17, 17), (35, 35, 35), (10, 10, 10)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Timão**", "O quiz definitivo sobre a história alvinegra, mundiais e títulos"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Corinthians** knowledge", "The ultimate trivia about the 2 World Titles, undefeated Libertadores and idols"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Timão**", "El quiz definitivo sobre el Bicampeonato Mundial, Libertadores e ídolos de Corinthians"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "palmeiras": {
        "name": "Quiz para Fãs do Palmeiras",
        "colors": [(0, 71, 36), (0, 100, 55), (0, 36, 18)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Verdão**", "O quiz definitivo sobre a história alviverde, títulos e ídolos"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Palmeiras** knowledge", "The ultimate quiz about titles, Copa Libertadores and Verdão legends"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Verdão**", "El quiz definitivo sobre títulos, Copa Libertadores e ídolos de Palmeiras"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "saopaulo": {
        "name": "Quiz para Fãs do São Paulo",
        "colors": [(30, 20, 22), (65, 10, 18), (18, 18, 18)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Soberano**", "O quiz definitivo sobre os Mundiais, Libertadores e ídolos do São Paulo"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **São Paulo FC** knowledge", "The ultimate trivia about the 3 World Titles, Libertadores and Tricolor idols"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Tricolor**", "El quiz definitivo sobre los 3 Mundiales, Libertadores e ídolos de São Paulo"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "santos": {
        "name": "Quiz para Fãs do Santos",
        "colors": [(20, 20, 20), (40, 40, 40), (10, 10, 10)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Peixe**", "O quiz definitivo sobre a Era Pelé, Libertadores e Meninos da Vila"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Santos FC** knowledge", "The ultimate quiz about Pelé, Intercontinental Cups and Meninos da Vila"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Peixe**", "El quiz definitivo sobre la Era Pelé, Libertadores y Meninos da Vila"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "gremio": {
        "name": "Quiz para Fãs do Grêmio",
        "colors": [(13, 128, 191), (10, 80, 130), (10, 15, 25)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Imortal**", "O quiz definitivo sobre a história tricolor, Libertadores e títulos"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Grêmio** knowledge", "The ultimate trivia about the 1983 World Title, 3 Libertadores and Tricolor idols"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Imortal**", "El quiz definitivo sobre el Mundial 1983, 3 Libertadores e ídolos de Grêmio"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "internacional": {
        "name": "Quiz para Fãs do Internacional",
        "colors": [(227, 6, 19), (160, 4, 14), (25, 10, 10)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Colorado**", "O quiz definitivo sobre o Mundial, Libertadores e ídolos do Inter"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Internacional** knowledge", "The ultimate trivia about the 2006 World Title, 2 Libertadores and Colorado idols"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Colorado**", "El quiz definitivo sobre el Mundial 2006, 2 Libertadores e ídolos de Inter"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "athleticopr": {
        "name": "Quiz para Fãs do Athletico-PR",
        "colors": [(200, 16, 26), (40, 10, 15), (15, 15, 15)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Furacão**", "O quiz definitivo sobre o Brasileirão 2001, Bi da Sul-Americana e ídolos"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Athletico-PR** knowledge", "The ultimate trivia about the 2001 Brasileirão, 2 Sudamericana titles and Furacão idols"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Furacão**", "El quiz definitivo sobre el Brasileirão 2001, 2 Sudamericanas e ídolos de Athletico"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "cruzeiro": {
        "name": "Quiz para Fãs do Cruzeiro",
        "colors": [(0, 58, 148), (0, 35, 100), (10, 15, 30)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **da Raposa**", "O quiz definitivo sobre o Rei de Copas, Tríplice Coroa e conquistas"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Cruzeiro** knowledge", "The ultimate trivia about the Rei de Copas, 2003 Treble and Raposa idols"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **de la Raposa**", "El quiz definitivo sobre el Rei de Copas, Tríplice Coroa e ídolos de Cruzeiro"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "atletico-mg": {
        "name": "Quiz para Fãs do Galo",
        "colors": [(17, 17, 17), (35, 35, 35), (10, 10, 10)],
        "highlight_color": (201, 149, 44),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Galo**", "O quiz definitivo sobre a Libertadores 2013, Triplete 2021 e ídolos"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detallado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "en": [
                ("Test your **Atlético-MG** knowledge", "The ultimate trivia about the 2013 Libertadores, 2021 Treble and Galo idols"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Galo**", "El quiz definitivo sobre la Libertadores 2013, Triplete 2021 e ídolos de Atlético"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ]
        }
    },
    "realmadrid": {
        "name": "Quiz para Fãs do Real Madrid",
        # Canvas is deliberately BRIGHTER than the in-app background (#001B33 -> #00060F).
        # Reusing the app palette here made the phone and the crops melt into the backdrop —
        # the three highest-installed apps in this niche all separate asset from content,
        # either with a light canvas or a flat brand colour.
        "colors": [(0, 60, 120), (0, 110, 200), (0, 40, 85)],
        "highlight_color": (254, 190, 16),
        # Real Madrid and Barcelona are multi-locale tenants (pt/es/ca) — slides_by_locale
        # is checked first in run_factory(); the flat "slides" key above is the legacy
        # single-locale (pt-only) shape still used by every other tenant in this dict.
        "slides_by_locale": {
            # Eight slots, one feature each, in SLIDE_SOURCES order. Headlines stay at
            # five to seven words and lead with the benefit — the first three slots are
            # what Play shows in search results and carry most of the install decision.
            "pt": [
                ("Desafie seus conhecimentos **do Real Madrid**", "O quiz definitivo sobre títulos, Galácticos e história merengue"),
                ("Perguntas sobre **títulos, ídolos e Clássicos**", "De Di Stéfano aos Galácticos e ao elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Real Madrid"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "es": [
                ("Desafía tus conocimientos **del Real Madrid**", "El quiz definitivo sobre títulos, Galácticos e historia merengue"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ],
            "ca": [
                ("Desafia els teus coneixements **del Real Madrid**", "El quiz definitiu sobre títols, Galàctics i història merenga"),
                ("Tria la **Quantitat de Preguntes**", "Juga rondes de 5, 10, 15 o 20 preguntes amb o sense pistes"),
                ("Resultat Detallat i **Temps de Resposta**", "Consulta el teu rendiment i precisió a cada partida"),
                ("Mantén la teva **Ratxa Diària**", "Entrena cada dia i enforteix la teva marca de Ratxa")
            ],
            "en": [
                ("Test your **Real Madrid** knowledge", "The ultimate quiz about titles, Galácticos and Merengue history"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ],
            "id": [
                ("Uji Pengetahuanmu tentang **Real Madrid**", "Kuis terbaik tentang gelar juara, era Galácticos, dan sejarah Merengue"),
                ("Pilih **Jumlah Pertanyaan**", "Mainkan ronde 5, 10, 15, atau 20 pertanyaan dengan atau tanpa petunjuk"),
                ("Hasil Lengkap dan **Waktu Respons**", "Lihat akurasi dan performamu di setiap pertandingan"),
                ("Pertahankan **Streak Harianmu**", "Latihan setiap hari dan bangun rekor Streak-mu")
            ],
            "fr": [
                ("Défiez vos connaissances sur le **Real Madrid**", "Le quiz ultime sur les titres, les Galáctiques et l'histoire merengue"),
                ("Choisissez le **Nombre de Questions**", "Jouez des séries de 5, 10, 15 ou 20 questions avec ou sans indices"),
                ("Résultats Détaillés et **Temps de Réponse**", "Consultez votre précision et vos performances à chaque match"),
                ("Maintenez votre **Série Quotidienne**", "Entraînez-vous chaque jour et développez votre Streak")
            ],
            "de": [
                ("Teste dein Wissen über **Real Madrid**", "Das ultimative Quiz über Titel, Galácticos und königliche Geschichte"),
                ("Wähle die **Anzahl der Fragen**", "Spiele Runden mit 5, 10, 15 oder 20 Fragen mit oder ohne Tipps"),
                ("Detaillierte Ergebnisse und **Antwortzeit**", "Verfolge deine Trefferquote und Leistung in jedem Spiel"),
                ("Halte deine **Tägliche Serie**", "Trainiere jeden Tag und baue deinen Streak aus")
            ],
            "hr": [
                ("Testirajte svoje znanje o **Real Madridu**", "Vrhunski kviz o trofejima, Galácticosima i povijesti Kraljevskog kluba"),
                ("Odaberite **Broj Pitanja**", "Igrajte runde od 5, 10, 15 ili 20 pitanja sa ili bez pomoći"),
                ("Detaljni Rezultati i **Vrijeme Odgovora**", "Pratite svoju točnost i učinak u svakoj igri"),
                ("Održavajte svoj **Dnevni Niz**", "Igrajte svaki dan i gradite svoj pobjednički Streak")
            ]
        }
    },
    "barcelona": {
        "name": "Quiz para Fãs do Barcelona",
        "colors": [(43, 0, 24), (165, 0, 68), (13, 0, 7)],
        "highlight_color": (237, 187, 0),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Barcelona**", "O quiz definitivo sobre títulos, ídolos e história blaugrana"),
                ("Escolha a **Quantidade de Perguntas**", "Jogue rodadas de 5, 10, 15 ou 20 questões com ou sem dicas"),
                ("Resultado Detalhado e **Tempo de Resposta**", "Veja seu aproveitamento e precisão em cada partida"),
                ("Mantenha sua **Sequência Diária**", "Treine todos os dias e fortaleça sua marca de Streak")
            ],
            "es": [
                ("Desafía tus conocimientos **del Barcelona**", "El quiz definitivo sobre títulos, ídolos e historia blaugrana"),
                ("Elige la **Cantidad de Preguntas**", "Juega rondas de 5, 10, 15 o 20 preguntas con o sin pistas"),
                ("Resultado Detallado y **Tiempo de Respuesta**", "Consulta tu rendimiento y precisión en cada partida"),
                ("Mantén tu **Racha Diaria**", "Entrena todos los días y fortalece tu marca de Racha")
            ],
            "ca": [
                ("Desafia els teus coneixements **del Barça**", "El quiz definitiu sobre títols, ídols i història blaugrana"),
                ("Tria la **Quantitat de Preguntes**", "Juga rondes de 5, 10, 15 o 20 preguntes amb o sense pistes"),
                ("Resultat Detallat i **Temps de Resposta**", "Consulta el teu rendiment i precisió a cada partida"),
                ("Mantén la teva **Ratxa Diària**", "Entrena cada dia i enforteix la teva marca de Ratxa")
            ],
            "en": [
                ("Test your **Barcelona** knowledge", "The ultimate quiz about titles, legends and Blaugrana history"),
                ("Choose Your **Question Count**", "Play rounds of 5, 10, 15 or 20 questions with or without hints"),
                ("Detailed Results and **Response Time**", "See your accuracy and performance in every match"),
                ("Keep Your **Daily Streak**", "Train every day and build up your Streak")
            ]
        }
    }
}

ALEFLY_SEEDS = "/Users/yuripacheco/Projetos/alefly/infra/firebase/seeds/tenants"


def _hex_to_rgb(value):
    value = (value or "").lstrip("#")
    if len(value) != 6:
        return None
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb):
    # WCAG relative luminance, used only to decide dark vs light text on the canvas.
    channels = []
    for c in rgb:
        c = c / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _shade(rgb, factor):
    if factor >= 1:
        return tuple(min(255, int(c + (255 - c) * (factor - 1))) for c in rgb)
    return tuple(max(0, int(c * factor)) for c in rgb)


def derive_palette(tenant_key):
    """Screenshot palette derived from the tenant seed, never hand-picked.

    The app paints its own background with `primaryColor`, so reusing it on the canvas
    made the phone and the crops melt into the backdrop. `accentColor` is the other
    brand colour and is what the canvas uses instead — gold behind Real Madrid's blue
    app, black behind Flamengo's red one — which keeps every tenant on brand while
    guaranteeing the asset separates from the content.

    Returns None when the seed is missing so the caller keeps its hardcoded colours.
    """
    seed_path = os.path.join(ALEFLY_SEEDS, f"{tenant_key}.json")
    if not os.path.exists(seed_path):
        return None
    with open(seed_path, encoding="utf-8") as fh:
        visual = (json.load(fh).get("visual") or {})
    accent = _hex_to_rgb(visual.get("accentColor"))
    primary = _hex_to_rgb(visual.get("primaryColor"))
    if not accent or not primary:
        return None

    # Light text on a dark canvas and vice versa — an accent like #FFFFFF or #FEBE10
    # would swallow the white headline the previous fixed styling assumed.
    dark_canvas = _relative_luminance(accent) < 0.5
    return {
        "colors": [_shade(accent, 0.82), accent, _shade(accent, 0.65)],
        "headline_color": (255, 255, 255) if dark_canvas else (12, 20, 32),
        "subhead_color": (222, 228, 238) if dark_canvas else (48, 60, 78),
        "highlight_color": primary,
    }


ALEFLY_ICONS = "/Users/yuripacheco/Projetos/alefly/tools/tenant-icons-python/icons-1024"


def paste_poster_icon(canvas, tenant_key, top_y):
    """Draws the tenant icon large instead of a device mockup.

    The three highest-installed apps in this niche do not put app UI in the first slot:
    two show pure key art. That slot carries most of the install decision and a whole
    screen shrunk to a search thumbnail communicates nothing, so it shows the brand
    instead. Rounded corners make the square read as an app icon rather than a pasted box.
    """
    for ext in ("png", "webp"):
        icon_path = os.path.join(ALEFLY_ICONS, f"icon_{tenant_key}.{ext}")
        if os.path.exists(icon_path):
            break
    else:
        return False

    cw, ch = canvas.size
    size = int(cw * 0.74)
    icon = Image.open(icon_path).convert("RGBA").resize((size, size), Image.LANCZOS)

    radius = int(size * 0.22)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=radius, fill=255)

    # Sits a fixed breath below the copy instead of centring in the leftover space —
    # centring left a dead band under the subheadline and crowded the bottom margin.
    x = (cw - size) // 2
    y = min(top_y + int(ch * 0.06), ch - size - int(ch * 0.08))

    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x + 12, y + 18, x + size + 12, y + size + 18], radius=radius, fill=(0, 0, 0, 70))
    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB"), (0, 0))
    canvas.paste(icon, (x, y), mask)
    return True


# Two zoom levels only, so the set reads as one system instead of six hand-tuned frames.
# Angle is 0 everywhere: the three highest-installed apps in this niche show the phone
# straight, and a tilt crops content off the canvas edge.
#
# WIDE is for screens whose payload sits in the upper half — the frame can be bigger because
# nothing important lives near the bottom. TALL is for screens whose payload runs to the
# bottom edge (share sheet, score plus stats plus CTA, answer explanation, scrolled home):
# they need the whole screen to fit or the point of the slide is clipped away.
ZOOM_WIDE = 0.76
ZOOM_TALL = 0.64

SLIDE_CONFIGS = {
    0: {"scale": ZOOM_WIDE, "angle": 0, "x_off": 0},
    1: {"scale": ZOOM_WIDE, "angle": 0, "x_off": 0},
    2: {"scale": ZOOM_TALL, "angle": 0, "x_off": 0},
    3: {"scale": ZOOM_TALL, "angle": 0, "x_off": 0},
    4: {"scale": ZOOM_TALL, "angle": 0, "x_off": 0},
    5: {"scale": ZOOM_TALL, "angle": 0, "x_off": 0},
}

# Store slot -> which Maestro capture it shows. Every slot is a whole screen inside the
# phone bezel, so each one needs its OWN capture: `crop` exists for the odd case but is
# unused today, because cropping regions out of a shared file was what let eight slots
# collapse into four distinct images.
#
# Order follows conversion research: the first three slots are what Play shows in search
# results and carry most of the install decision, so brand, core loop and the
# differentiator go there. Streak and stats are generic mechanics and sit at the end.
#
# Files 05 to 08 are not captured yet — .maestro/android/store-screenshots.yaml already
# walks through three of those screens without calling takeScreenshot. Missing files are
# skipped with a warning rather than falling back to a duplicate.
SLIDE_SOURCES = [
    {"file": "01-home.png",            "crop": None, "frame": True},
    {"file": "02-question.png",        "crop": None, "frame": True},
    {"file": "08-challenge-share.png", "crop": None, "frame": True},
    {"file": "04-result-summary.png",  "crop": None, "frame": True},
    {"file": "03-answer-feedback.png", "crop": None, "frame": True},
    {"file": "05-home-scrolled.png",   "crop": None, "frame": True},
]

def get_fonts(platform="ios"):
    f_bold = os.path.join(FONTS_DIR, "montserrat_bold.ttf")
    f_reg = os.path.join(FONTS_DIR, "montserrat.ttf")
    if not os.path.exists(f_bold): f_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    if not os.path.exists(f_reg): f_reg = "/System/Library/Fonts/Supplemental/Arial.ttf"
    if platform == "ipad":
        return ImageFont.truetype(f_bold, 148), ImageFont.truetype(f_reg, 70)
    return ImageFont.truetype(f_bold, 104), ImageFont.truetype(f_reg, 50)

def expand_bold_spans(text):
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

def _draw_line_centered(draw, line, font, y, width, style, highlight_color):
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
    total_w += space_w * (len(parts) - 1) if len(parts) > 1 else 0

    cur_x = (width - total_w) // 2
    for visible, is_hl, w in segments:
        col = highlight_color if is_hl else style.color
        # Shadow suave
        # The canvas is RGB, so PIL discards the alpha in `fill` and paints solid black:
        # shadow_alpha never actually softened anything, it only went unnoticed on dark
        # backgrounds. Skip the pass entirely when the style asks for no shadow.
        if style.shadow_alpha:
            draw.text((cur_x + 3, y + 3), visible, fill=(0, 0, 0), font=font)
        draw.text((cur_x, y), visible, fill=col, font=font)
        cur_x += w + space_w

def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

BACKGROUND_DARKEN_RATIO = 0.55

def darken_color(color, ratio=BACKGROUND_DARKEN_RATIO):
    keep = 1 - ratio
    return tuple(int(c * keep) for c in color)

def draw_brand_background(canvas, colors):
    w, h = canvas.size
    cx, cy = w / 2, h / 2
    diag = math.sqrt(w*w + h*h)
    rad = math.radians(GRADIENT_ANGLE_DEG)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    
    # Grid de pixels normalizado
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    t = ((x_coords - cx) * cos_a + (y_coords - cy) * sin_a) / diag + 0.5
    t = np.clip(t, 0.0, 1.0)

    n_c = len(colors)
    out = np.zeros((h, w, 3), dtype=np.float32)
    
    for i in range(n_c - 1):
        t0 = i / (n_c - 1)
        t1 = (i + 1) / (n_c - 1)
        mask = (t >= t0) & (t <= t1)
        lt = (t - t0) / (t1 - t0)
        
        c0 = np.array(colors[i], dtype=np.float32)
        c1 = np.array(colors[i+1], dtype=np.float32)
        
        for ch in range(3):
            out[..., ch] += mask * (c0[ch] + lt * (c1[ch] - c0[ch]))

    img = Image.fromarray(out.astype(np.uint8), mode="RGB")
    canvas.paste(img, (0, 0))

def draw_text_block(canvas, headline, subheadline, f_h, f_s, highlight_color, platform="ios",
                    headline_style=None, subhead_style=None):
    w, h = canvas.size
    text_w = w - (300 if platform == "ipad" else 220)
    top_margin = 190 if platform == "ipad" else TEXT_TOP_MARGIN
    headline_style = headline_style or HEADLINE_STYLE
    subhead_style = subhead_style or SUBHEAD_STYLE
    draw = ImageDraw.Draw(canvas)
    headline = expand_bold_spans(headline)
    subheadline = expand_bold_spans(subheadline)
    h_lines = wrap_text(headline, draw, f_h, text_w)
    s_lines = wrap_text(subheadline, draw, f_s, text_w)
    h_lh = int(f_h.size * HEADLINE_LINE_HEIGHT_RATIO)
    s_lh = int(f_s.size * SUBHEAD_LINE_HEIGHT_RATIO)
    gap = int(f_h.size * HEADLINE_SUBHEAD_GAP_RATIO)

    curr_y = top_margin
    for line in h_lines:
        _draw_line_centered(draw, line, f_h, curr_y, w, headline_style, highlight_color)
        curr_y += h_lh
    curr_y += gap
    for line in s_lines:
        _draw_line_centered(draw, line, f_s, curr_y, w, subhead_style, highlight_color)
        curr_y += s_lh

    return (len(h_lines) * h_lh) + (len(s_lines) * s_lh) + gap

def process_screenshot(tenant_key, idx, headline, subheadline, input_path, output_path, platform="android", use_slide_sources=False):
    config = TENANT_CONFIGS[tenant_key]
    if platform == "ipad":
        cw, ch = 2048, 2732
    elif platform == "android":
        cw, ch = ANDROID_WIDTH, ANDROID_HEIGHT
    else:
        cw, ch = WIDTH, HEIGHT
    canvas = Image.new('RGB', (cw, ch))
    palette = derive_palette(tenant_key)
    if palette:
        # Already the intended canvas colour — darkening it here would turn Real Madrid's
        # gold into brown. darken_color() only exists to tame the legacy hardcoded palettes,
        # which reused the in-app background and needed dimming to sit behind white text.
        draw_brand_background(canvas, palette["colors"])
    else:
        draw_brand_background(canvas, [darken_color(c) for c in config["colors"]])

    f_h, f_s = get_fonts(platform=platform)
    if palette:
        # Shadows are what keep the text readable over the gradient; on a light canvas a
        # dark shadow would smear, so it drops with the text colour.
        dark_canvas = palette["headline_color"] == (255, 255, 255)
        headline_style = TextStyle(color=palette["headline_color"], shadow_alpha=90 if dark_canvas else 0)
        subhead_style = TextStyle(color=palette["subhead_color"], shadow_alpha=70 if dark_canvas else 0)
        highlight = palette["highlight_color"]
    else:
        headline_style = subhead_style = None
        highlight = config["highlight_color"]
    total_text_h = draw_text_block(canvas, headline, subheadline, f_h, f_s, highlight, platform=platform,
                                   headline_style=headline_style, subhead_style=subhead_style)

    top_margin = 190 if platform == "ipad" else TEXT_TOP_MARGIN
    device_y = top_margin + total_text_h + (ANCHOR_MARGIN // 2)
    if platform == "ipad":
        device_y_max, device_y_fallback = 950, 900
    elif platform == "android":
        device_y_max, device_y_fallback = DEVICE_Y_MAX_ANDROID, DEVICE_Y_FALLBACK_ANDROID
    else:
        device_y_max, device_y_fallback = DEVICE_Y_MAX, DEVICE_Y_FALLBACK
    if device_y > device_y_max: device_y = device_y_fallback

    is_poster = use_slide_sources and idx < len(SLIDE_SOURCES) and SLIDE_SOURCES[idx].get("poster")
    if is_poster and paste_poster_icon(canvas, tenant_key, device_y):
        pass
    elif os.path.exists(input_path):
        screen = Image.open(input_path).convert("RGBA")
        conf = SLIDE_CONFIGS.get(idx, SLIDE_CONFIGS[0])

        # Zoom into one feature before scaling, so the slot reads at thumbnail size
        # instead of showing a whole screen nobody can parse. Normalized box keeps the
        # values resolution-independent across capture devices.
        source = SLIDE_SOURCES[idx] if idx < len(SLIDE_SOURCES) else {}
        crop = source.get("crop") if use_slide_sources else None
        if crop:
            w, h = screen.size
            x1, y1, x2, y2 = crop
            screen = screen.crop((int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)))

        draw_frame = source.get("frame", True) if use_slide_sources else True
        target_w = int(cw * (conf["scale"] if platform != "ipad" else 0.82))
        aspect = screen.height / screen.width
        target_h = int(target_w * aspect)
        screen = screen.resize((target_w, target_h), Image.LANCZOS)

        if platform == "android":
            radius = 45
            border_col = (130, 130, 135)
            light_col = (190, 190, 195)
        elif platform == "ipad":
            radius = 40
            border_col = (200, 200, 205)
            light_col = (240, 240, 245)
        else:
            radius = 80
            border_col = (210, 210, 215)
            light_col = (245, 245, 250)

        mask = Image.new('L', (target_w, target_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, target_w, target_h], radius=radius, fill=255)

        pad = 60 if platform == "ipad" else 50
        device_layer = Image.new("RGBA", (target_w + (pad*2), target_h + (pad*2)), (0,0,0,0))
        device_layer.paste(screen, (pad, pad), mask)

        if draw_frame:
            border_w = 20 if platform == "ipad" else 22
            ImageDraw.Draw(device_layer).rounded_rectangle([pad, pad, target_w+pad, target_h+pad], radius=radius, outline=border_col, width=border_w)
            ImageDraw.Draw(device_layer).rounded_rectangle([pad+2, pad+2, target_w+pad-2, target_h+pad-2], radius=radius, outline=light_col, width=3)

            cam_x = (target_w + (pad*2)) // 2
            if platform == "android":
                ImageDraw.Draw(device_layer).ellipse([cam_x-10, 80, cam_x+10, 100], fill=(15,15,15))
            elif platform == "ios":
                island_w, island_h = 135, 38
                ImageDraw.Draw(device_layer).rounded_rectangle([cam_x-(island_w//2), 75, cam_x+(island_w//2), 75+island_h], radius=18, fill=(10,10,10))

        if draw_frame and conf["angle"] != 0 and platform != "ipad":
            device_layer = device_layer.rotate(conf["angle"], resample=Image.BICUBIC, expand=True)

        x_off = int(conf["x_off"] * (cw / REFERENCE_WIDTH))
        canvas.paste(device_layer, ((cw-device_layer.width)//2 + x_off, device_y), device_layer)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, quality=100, subsampling=0)
    print(f"  ✅ Salvo [{platform.upper()}]: {output_path}")

# Content-locale (used by slides_by_locale / capture-multilocale-screenshots.sh
# subfolders) -> store-listing locale folder name (store-assets/{tenant}/{locale}/),
# same convention already used by alefly's ASO metadata and feature-graphic pipelines.
STORE_LOCALE_BY_CONTENT_LOCALE = {
    "pt": "pt-BR",
    "es": "es-ES",
    "ca": "ca",
    "en": "en-US",
    "id": "id-ID",
    "fr": "fr-FR",
    "de": "de-DE",
    "hr": "hr",
    "ar": "ar",
    "zh": "zh-CN",
    "tr": "tr-TR"
}

def run_factory(target_tenant=None, target_platform="all", target_locale=None):
    platforms = ["android", "ios", "ipad"] if target_platform == "all" else [target_platform]

    print(f"🚀 Fábrica de Screenshots Alefly (Plataformas: {', '.join(platforms).upper()})...")

    tenants = [target_tenant] if target_tenant else list(TENANT_CONFIGS.keys())

    for platform in platforms:
        print(f"\n📱 PLATAFORMA: {platform.upper()}")
        for tenant in tenants:
            if tenant not in TENANT_CONFIGS:
                print(f"⚠️ Tenant '{tenant}' não encontrado nas configurações.")
                continue

            config = TENANT_CONFIGS[tenant]
            print(f"  📦 App: {config['name']} ({tenant})")

            is_multi_locale = "slides_by_locale" in config
            if is_multi_locale:
                locales = [target_locale] if target_locale else list(config["slides_by_locale"].keys())
            else:
                if target_locale and target_locale != "pt":
                    print(f"  ⚠️ Tenant '{tenant}' só tem slides em pt — ignorando --locale {target_locale}.")
                locales = ["pt"]

            base_output_dir = "/Users/yuripacheco/Projetos/alefly/output/store-assets"

            for locale in locales:
                slides = config["slides_by_locale"][locale] if is_multi_locale else config["slides"]
                store_locale = STORE_LOCALE_BY_CONTENT_LOCALE.get(locale, "pt-BR")
                # Multi-locale tenants archive raw captures per locale (see
                # scripts/capture-multilocale-screenshots.sh in the alefly repo) —
                # single-locale tenants keep reading the unsuffixed legacy path so
                # their existing capture flow needs zero changes.
                locale_suffix = os.path.join(locale) if is_multi_locale else ""

                if platform == "android":
                    raw_screenshots_dir = os.path.join(base_output_dir, tenant, "android", "screenshots", locale_suffix)
                    if not os.path.exists(raw_screenshots_dir) or not glob.glob(f"{raw_screenshots_dir}/*.png"):
                        raw_screenshots_dir = os.path.join(base_output_dir, tenant, "ios", "screenshots", "iphone", locale_suffix)
                elif platform == "ipad":
                    raw_screenshots_dir = os.path.join(base_output_dir, tenant, "ios", "screenshots", "ipad", locale_suffix)
                else:
                    raw_screenshots_dir = os.path.join(base_output_dir, tenant, "ios", "screenshots", "iphone", locale_suffix)

                if not os.path.exists(raw_screenshots_dir):
                    print(f"  ⚠️ Pasta de screenshots crus não encontrada ({locale}): {raw_screenshots_dir}")
                    continue

                maestro_filenames = [
                    "01-home.png",
                    "02-question.png",
                    "03-answer-feedback.png",
                    "04-result-summary.png"
                ]

                screenshots_dir = os.path.join(ALEFLY_STORE_ASSETS, tenant, store_locale, "screenshots")
                output_dir = os.path.join(screenshots_dir, platform)

                # Tenants migrated to the eight-slot spec declare eight captions and are
                # driven by SLIDE_SOURCES, which names the capture and region per slot.
                # Legacy four-caption tenants keep the old positional mapping untouched
                # until they are migrated one at a time.
                use_slide_sources = len(slides) == len(SLIDE_SOURCES)

                for i, (headline, subheadline) in enumerate(slides):
                    if use_slide_sources:
                        candidate = os.path.join(raw_screenshots_dir, SLIDE_SOURCES[i]["file"])
                        input_file = candidate if os.path.exists(candidate) else None
                    elif i < len(maestro_filenames) and os.path.exists(os.path.join(raw_screenshots_dir, maestro_filenames[i])):
                        input_file = os.path.join(raw_screenshots_dir, maestro_filenames[i])
                    else:
                        # Fallback to available files in directory
                        avail = sorted(glob.glob(f"{raw_screenshots_dir}/*.png"))
                        input_file = avail[min(i, len(avail)-1)] if avail else None

                    output_file = os.path.join(output_dir, f"slide_{i+1}.png")

                    if input_file and os.path.exists(input_file):
                        process_screenshot(tenant, i, headline, subheadline, input_file, output_file,
                                           platform=platform, use_slide_sources=use_slide_sources)
                    else:
                        print(f"    ⚠️ Screenshot de entrada não encontrada ({locale}): {input_file}")

    print("\n🎉 Todas as screenshots para Android, iOS e iPad foram geradas com sucesso nas pastas padrão!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default=None, help="Tenant específico para gerar (ex: flamengo, vasco, worldcup, etc)")
    parser.add_argument("--platform", choices=["android", "ios", "ipad", "all"], default="all")
    parser.add_argument("--locale", default=None, help="Locale específico (pt/es/ca) para tenants multi-idioma; default processa todos os locales do tenant")
    args = parser.parse_args()

    run_factory(target_tenant=args.tenant, target_platform=args.platform, target_locale=args.locale)
