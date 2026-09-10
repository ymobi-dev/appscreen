import os
import sys
import glob
import json
import math
import re
import argparse
import colorsys
import itertools
import numpy as np
from collections import namedtuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
MIN_TEXT_DEVICE_GAP = 48

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
TextStyle = namedtuple("TextStyle", "color")
HEADLINE_STYLE = TextStyle(color=(255, 255, 255))
SUBHEAD_STYLE = TextStyle(color=(220, 225, 235))

# Base paths
ALEFLY_REPO_ROOT = os.environ.get("ALEFLY_REPO_ROOT", "/Users/yuripacheco/Projetos/alefly")
ALEFLY_STORE_ASSETS = os.path.join(ALEFLY_REPO_ROOT, "store-assets")
APPSCREEN_ROOT = "/Users/yuripacheco/Projetos/appscreen"

# TENANTS ATIVOS NAS LOJAS E SUAS CONFIGURAÇÕES DE DESIGN
TENANT_CONFIGS = {
    "flamengo": {
        "name": "Quiz para Fãs do Fla",
        "colors": [(26, 0, 0), (122, 0, 0), (26, 26, 26)],
        "highlight_color": (255, 70, 70),
        "slides": [
            ("Desafie seus conhecimentos **do Flamengo**", "O quiz definitivo sobre títulos, ídolos e história rubro-negra"),
            ("Perguntas sobre **títulos, ídolos e clássicos**", "De Zico a Arrascaeta e ao elenco atual"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Flamengo"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "botafogo": {
        "name": "Quiz para Fãs do Botafogo",
        "colors": [(13, 11, 6), (30, 26, 16), (10, 10, 10)],
        "highlight_color": (232, 232, 232),
        "slides": [
            ("Desafie seus conhecimentos **do Botafogo**", "O quiz definitivo sobre títulos, ídolos e história alvinegra"),
            ("Perguntas sobre **títulos, ídolos e clássicos**", "De Garrincha a Luiz Henrique e ao elenco atual"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Botafogo"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "fluminense": {
        "name": "Quiz para Fãs do Fluminense",
        "colors": [(13, 4, 5), (74, 14, 26), (10, 5, 5)],
        "highlight_color": (0, 168, 107),
        "slides": [
            ("Desafie seus conhecimentos **do Fluminense**", "O quiz definitivo sobre títulos, ídolos e história tricolor"),
            ("Perguntas sobre **títulos, ídolos e clássicos**", "De Castilho e Didi ao time campeão da Libertadores 2023"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Fluminense"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "vasco": {
        "name": "Quiz para Fãs do Vasco",
        "colors": [(10, 10, 10), (26, 26, 26), (5, 5, 5)],
        "highlight_color": (224, 224, 224),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Vasco**", "O quiz definitivo sobre títulos, ídolos e história cruzmaltina"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Ademir de Menezes ao time campeão da Libertadores 1998"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Vasco"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Vasco** knowledge", "The ultimate quiz on titles, legends and Vasco da Gama history"),
                ("Questions on **titles, legends and rivalries**", "From Ademir de Menezes to the 1998 Libertadores champions"),
                ("Challenge a friend **by link**", "Send the match and see who knows Vasco best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Pon a prueba tu conocimiento **del Vasco**", "El quiz definitivo sobre títulos, ídolos e historia del Vasco da Gama"),
                ("Preguntas sobre **títulos, ídolos y rivalidades**", "De Ademir de Menezes al campeón de la Libertadores de 1998"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Vasco"),
                ("Tu puntaje al instante, **partida a partida**", "Puntos, precisión y progreso en cada ronda"),
                ("El que sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Atascado? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de partidas")
            ]
        }
    },
    "worldcup": {
        "name": "Quiz para fãs da Copa",
        "colors": [(8, 21, 40), (21, 57, 97), (6, 15, 30)],
        "highlight_color": (46, 204, 113),
        "slides": [
            ("Desafie seus conhecimentos **de Copa**", "O quiz definitivo sobre seleções, craques e história do futebol mundial"),
            ("Perguntas sobre **craques, seleções e finais**", "De Garrincha e Pelé a Mbappé e o futebol de hoje"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais de futebol mundial"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "bible": {
        "name": "Quiz da Bíblia",
        "colors": [(8, 21, 40), (22, 46, 84), (6, 15, 30)],
        "highlight_color": (201, 149, 44),
        "slides": [
            ("Desafie seus conhecimentos **da Bíblia**", "O quiz definitivo sobre o Antigo e o Novo Testamento"),
            ("Perguntas sobre **personagens, livros e ensinamentos**", "De Gênesis ao Apocalipse, com contexto para aprender"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem conhece mais as Escrituras"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "geography-world": {
        "name": "Quiz Geografia Mundial",
        "colors": [(15, 43, 31), (27, 67, 50), (10, 30, 20)],
        "highlight_color": (82, 183, 136),
        "slides": [
            ("Desafie seus conhecimentos **de Geografia**", "O quiz definitivo sobre bandeiras, capitais e países do mundo"),
            ("Perguntas sobre **bandeiras, capitais e mapas**", "De países vizinhos a nações do outro lado do planeta"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem conhece mais o mundo"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "enem-matematica": {
        "name": "ENEM Matemática: Questões",
        "colors": [(3, 30, 20), (5, 50, 30), (2, 20, 15)],
        "highlight_color": (0, 229, 117),
        "slides": [
            ("Domine a prova **de Matemática do ENEM**", "O simulado definitivo com questões oficiais e gabarito comentado"),
            ("Questões sobre **álgebra, geometria e estatística**", "Do básico às questões que mais caem na prova"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem está mais preparado"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "enem-portugues": {
        "name": "ENEM Linguagens: Questões",
        "colors": [(30, 24, 6), (55, 42, 10), (20, 16, 4)],
        "highlight_color": (255, 208, 67),
        "slides": [
            ("Domine a prova **de Linguagens do ENEM**", "O simulado definitivo de Língua Portuguesa e Literatura"),
            ("Questões sobre **gramática, interpretação e literatura**", "Do básico às questões que mais caem na prova"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem está mais preparado"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "enem-humanas": {
        "name": "ENEM Humanas: Questões",
        "colors": [(20, 12, 35), (42, 25, 75), (14, 8, 25)],
        "highlight_color": (167, 139, 250),
        "slides": [
            ("Domine a prova **de Ciências Humanas**", "O simulado definitivo de História, Geografia, Filosofia e Sociologia"),
            ("Questões sobre **história, geografia e política**", "Do básico às questões que mais caem na prova"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem está mais preparado"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "enem-natureza": {
        "name": "ENEM Natureza: Questões",
        "colors": [(4, 25, 30), (10, 48, 55), (3, 18, 22)],
        "highlight_color": (20, 184, 166),
        "slides": [
            ("Domine a prova **de Ciências da Natureza**", "O simulado definitivo de Biologia, Física e Química"),
            ("Questões sobre **biologia, física e química**", "Do básico às questões que mais caem na prova"),
            ("Desafie um amigo **por link**", "Envie a partida e veja quem está mais preparado"),
            ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
            ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
            ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
            ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
            ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
        ]
    },
    "manchesterunited": {
        "name": "Quiz para Fãs do Manchester United",
        "colors": [(51, 0, 0), (218, 2, 14), (13, 0, 0)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Manchester United**", "O quiz definitivo sobre títulos, ídolos e história dos Red Devils"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Cristiano Ronaldo a Bruno Fernandes e ao elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Manchester United"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Manchester United** knowledge", "The ultimate quiz on titles, legends and Red Devils history"),
                ("Questions on **titles, legends and rivalries**", "From Cristiano Ronaldo to Bruno Fernandes and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Manchester United best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ]
        }
    },
    "manchestercity": {
        "name": "Quiz para Fãs do Manchester City",
        "colors": [(6, 26, 46), (108, 171, 221), (2, 13, 26)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Manchester City**", "O quiz definitivo sobre a Tríplice Coroa, ídolos e história dos Cityzens"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Agüero e De Bruyne a Haaland e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Manchester City"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Manchester City** knowledge", "The ultimate quiz on the Treble, legends and Cityzens history"),
                ("Questions on **titles, legends and rivalries**", "From Agüero and De Bruyne to Haaland and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Manchester City best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ]
        }
    },
    "juventus": {
        "name": "Quiz para Fãs da Juventus",
        "colors": [(17, 17, 17), (35, 35, 35), (10, 10, 10)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **da Juventus**", "O quiz definitivo sobre Scudetti, ídolos e história da Vecchia Signora"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Del Piero e Buffon a Cristiano Ronaldo e Dybala"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais da Juventus"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "it": [
                ("Metti alla prova le tue conoscenze **sulla Juventus**", "Il quiz definitivo su Scudetti, idoli e storia della Vecchia Signora"),
                ("Domande su **titoli, idoli e derby**", "Da Del Piero e Buffon a Cristiano Ronaldo e Dybala"),
                ("Sfida un amico **con un link**", "Invia la partita e scopri chi ne sa di più sulla Juventus"),
                ("Il tuo punteggio subito, **round dopo round**", "Punteggio, percentuale di risposte corrette ed evoluzione a ogni partita"),
                ("Chi ne sa di più **resta in cima**", "Classifica in tempo reale tra te e i tuoi amici"),
                ("Hai sbagliato? La risposta arriva **spiegata**", "Ogni domanda mostra quella giusta e il motivo"),
                ("Bloccato? **Usa un suggerimento**", "Un aiuto per domanda, quando ne hai bisogno"),
                ("Torna ogni giorno e **mantieni la serie**", "Serie giornaliera, classifica e cronologia delle tue partite")
            ]
        }
    },
    "corinthians": {
        "name": "Quiz para Fãs do Corinthians",
        "colors": [(17, 17, 17), (35, 35, 35), (10, 10, 10)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Corinthians**", "O quiz definitivo sobre a história alvinegra, mundiais e títulos"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Sócrates e Rivellino a Cássio e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Corinthians"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Corinthians** knowledge", "The ultimate trivia about the 2 World Titles, undefeated Libertadores and idols"),
                ("Questions on **titles, legends and derbies**", "From Sócrates and Rivellino to Cássio and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Corinthians best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Corinthians**", "El quiz definitivo sobre el Bicampeonato Mundial, Libertadores e ídolos de Corinthians"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Sócrates y Rivellino a Cássio y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Corinthians"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "palmeiras": {
        "name": "Quiz para Fãs do Palmeiras",
        "colors": [(0, 71, 36), (0, 100, 55), (0, 36, 18)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Palmeiras**", "O quiz definitivo sobre a história alviverde, títulos e ídolos"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Ademir da Guia a Dudu e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Palmeiras"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Palmeiras** knowledge", "The ultimate quiz about titles, Copa Libertadores and Verdão legends"),
                ("Questions on **titles, legends and derbies**", "From Ademir da Guia to Dudu and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Palmeiras best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Palmeiras**", "El quiz definitivo sobre títulos, Copa Libertadores e ídolos de Palmeiras"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Ademir da Guia a Dudu y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Palmeiras"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "saopaulo": {
        "name": "Quiz para Fãs do São Paulo",
        "colors": [(30, 20, 22), (65, 10, 18), (18, 18, 18)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do São Paulo**", "O quiz definitivo sobre os Mundiais, Libertadores e ídolos do São Paulo"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Serginho Chulapa a Lucas Moura e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do São Paulo"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **São Paulo FC** knowledge", "The ultimate trivia about the 3 World Titles, Libertadores and Tricolor idols"),
                ("Questions on **titles, legends and derbies**", "From Serginho Chulapa to Lucas Moura and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows São Paulo best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del São Paulo**", "El quiz definitivo sobre los 3 Mundiales, Libertadores e ídolos de São Paulo"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Serginho Chulapa a Lucas Moura y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del São Paulo"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "santos": {
        "name": "Quiz para Fãs do Santos",
        "colors": [(20, 20, 20), (40, 40, 40), (10, 10, 10)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Santos**", "O quiz definitivo sobre a Era Pelé, Libertadores e Meninos da Vila"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Pelé e Pepe a Neymar e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Santos"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Santos FC** knowledge", "The ultimate quiz about Pelé, Intercontinental Cups and Meninos da Vila"),
                ("Questions on **titles, legends and derbies**", "From Pelé and Pepe to Neymar and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Santos best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Santos**", "El quiz definitivo sobre la Era Pelé, Libertadores y Meninos da Vila"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Pelé y Pepe a Neymar y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Santos"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "gremio": {
        "name": "Quiz para Fãs do Grêmio",
        "colors": [(13, 128, 191), (10, 80, 130), (10, 15, 25)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Grêmio**", "O quiz definitivo sobre a história tricolor, Libertadores e títulos"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Renato Gaúcho a Ronaldinho Gaúcho e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Grêmio"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Grêmio** knowledge", "The ultimate trivia about the 1983 World Title, 3 Libertadores and Tricolor idols"),
                ("Questions on **titles, legends and derbies**", "From Renato Gaúcho to Ronaldinho Gaúcho and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Grêmio best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Grêmio**", "El quiz definitivo sobre el Mundial 1983, 3 Libertadores e ídolos de Grêmio"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Renato Gaúcho a Ronaldinho Gaúcho y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Grêmio"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "internacional": {
        "name": "Quiz para Fãs do Internacional",
        "colors": [(227, 6, 19), (160, 4, 14), (25, 10, 10)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Internacional**", "O quiz definitivo sobre o Mundial, Libertadores e ídolos do Inter"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Falcão a D'Alessandro e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Internacional"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Internacional** knowledge", "The ultimate trivia about the 2006 World Title, 2 Libertadores and Colorado idols"),
                ("Questions on **titles, legends and derbies**", "From Falcão to D'Alessandro and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Internacional best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Internacional**", "El quiz definitivo sobre el Mundial 2006, 2 Libertadores e ídolos de Inter"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Falcão a D'Alessandro y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Internacional"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "athleticopr": {
        "name": "Quiz para Fãs do Athletico-PR",
        "colors": [(200, 16, 26), (40, 10, 15), (15, 15, 15)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Athletico-PR**", "O quiz definitivo sobre o Brasileirão 2001, Bi da Sul-Americana e ídolos"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "Do Brasileirão 2001 ao elenco atual do Furacão"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Athletico-PR"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Athletico-PR** knowledge", "The ultimate trivia about the 2001 Brasileirão, 2 Sudamericana titles and Furacão idols"),
                ("Questions on **titles, legends and derbies**", "From the 2001 Brasileirão to today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Athletico-PR best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Athletico-PR**", "El quiz definitivo sobre el Brasileirão 2001, 2 Sudamericanas e ídolos de Athletico"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "Del Brasileirão 2001 a la plantilla actual del Furacão"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Athletico-PR"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "cruzeiro": {
        "name": "Quiz para Fãs do Cruzeiro",
        "colors": [(0, 58, 148), (0, 35, 100), (10, 15, 30)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Cruzeiro**", "O quiz definitivo sobre o Rei de Copas, Tríplice Coroa e conquistas"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Tostão e Dirceu Lopes a Ronaldo e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Cruzeiro"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Cruzeiro** knowledge", "The ultimate trivia about the Rei de Copas, 2003 Treble and Raposa idols"),
                ("Questions on **titles, legends and derbies**", "From Tostão and Dirceu Lopes to Ronaldo and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Cruzeiro best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Cruzeiro**", "El quiz definitivo sobre el Rei de Copas, Tríplice Coroa e ídolos de Cruzeiro"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Tostão y Dirceu Lopes a Ronaldo y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Cruzeiro"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "atleticomg": {
        "name": "Quiz para Fãs do Galo",
        "colors": [(17, 17, 17), (35, 35, 35), (10, 10, 10)],
        "highlight_color": (201, 149, 44),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Atlético-MG**", "O quiz definitivo sobre a Libertadores 2013, Triplete 2021 e ídolos"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Reinaldo e Dadá Maravilha a Hulk e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Atlético-MG"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Atlético-MG** knowledge", "The ultimate trivia about the 2013 Libertadores, 2021 Treble and Galo idols"),
                ("Questions on **titles, legends and derbies**", "From Reinaldo and Dadá Maravilha to Hulk and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Atlético-MG best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Atlético-MG**", "El quiz definitivo sobre la Libertadores 2013, Triplete 2021 e ídolos de Atlético"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Reinaldo y Dadá Maravilha a Hulk y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Atlético-MG"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
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
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "es": [
                ("Desafía tus conocimientos **del Real Madrid**", "El quiz definitivo sobre títulos, Galácticos e historia merengue"),
                ("Preguntas sobre **títulos, ídolos y Clásicos**", "De Di Stéfano a los Galácticos y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Real Madrid"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "ca": [
                ("Desafia els teus coneixements **del Real Madrid**", "El quiz definitiu sobre títols, Galàctics i història merenga"),
                ("Preguntes sobre **títols, ídols i Clàssics**", "De Di Stéfano als Galàctics i la plantilla actual"),
                ("Desafia un amic **per enllaç**", "Envia la partida i descobreix qui en sap més del Real Madrid"),
                ("El teu marcador a l'instant, **partida a partida**", "Puntuació, percentatge d'encert i evolució a cada ronda"),
                ("Qui en sap més **arriba al capdamunt**", "Rànquing en temps real entre tu i els teus amics"),
                ("Has fallat? La resposta ve **explicada**", "Cada pregunta mostra la correcta i el perquè"),
                ("T'has encallat? **Usa una pista**", "Una ajuda per pregunta, quan la necessitis"),
                ("Torna cada dia i **manté la teva ratxa**", "Ratxa diària, rànquing i historial de les teves partides")
            ],
            "en": [
                ("Test your **Real Madrid** knowledge", "The ultimate quiz on titles, Galácticos and Merengue history"),
                ("Questions on **titles, legends and Clásicos**", "From Di Stéfano to the Galácticos and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Real Madrid best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "id": [
                ("Uji Pengetahuanmu tentang **Real Madrid**", "Kuis terbaik tentang gelar juara, era Galácticos, dan sejarah Merengue"),
                ("Pertanyaan seputar **gelar juara, legenda, dan Clásico**", "Dari Di Stéfano hingga era Galácticos dan skuad saat ini"),
                ("Tantang teman **lewat tautan**", "Kirim pertandingan dan lihat siapa yang paling paham Real Madrid"),
                ("Skormu langsung terlihat, **ronde demi ronde**", "Poin, persentase jawaban benar, dan perkembangan di tiap ronde"),
                ("Yang paling paham **naik ke puncak**", "Peringkat real-time antara kamu dan teman-temanmu"),
                ("Salah jawab? Jawabannya **langsung dijelaskan**", "Setiap pertanyaan menampilkan jawaban benar dan alasannya"),
                ("Buntu? **Gunakan petunjuk**", "Satu bantuan per pertanyaan, saat kamu membutuhkannya"),
                ("Kembali tiap hari dan **jaga streak-mu**", "Streak harian, peringkat, dan riwayat setiap rondemu")
            ],
            "fr": [
                ("Défiez vos connaissances sur le **Real Madrid**", "Le quiz ultime sur les titres, les Galáctiques et l'histoire merengue"),
                ("Questions sur les **titres, légendes et Clásicos**", "De Di Stéfano aux Galáctiques jusqu'à l'effectif actuel"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui connaît le mieux le Real Madrid"),
                ("Votre score à l'instant, **match après match**", "Points, pourcentage de réussite et progression à chaque manche"),
                ("Le plus fort **grimpe au sommet**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ],
            "de": [
                ("Teste dein Wissen über **Real Madrid**", "Das ultimative Quiz über Titel, Galácticos und königliche Geschichte"),
                ("Fragen zu **Titeln, Legenden und Clásicos**", "Von Di Stéfano bis zu den Galácticos und dem aktuellen Kader"),
                ("Fordere einen Freund **per Link** heraus", "Schick das Spiel und finde heraus, wer Real Madrid am besten kennt"),
                ("Dein Ergebnis sofort, **Runde für Runde**", "Punkte, Trefferquote und Fortschritt in jeder Runde"),
                ("Wer mehr weiß, **steht ganz oben**", "Ranking in Echtzeit zwischen dir und deinen Freunden"),
                ("Falsch geraten? Die Antwort wird **erklärt**", "Jede Frage zeigt die richtige Lösung und das Warum"),
                ("Nicht weiter? **Nutze einen Hinweis**", "Eine Hilfe pro Frage, wann immer du sie brauchst"),
                ("Komm täglich zurück und **halte deinen Streak**", "Täglicher Streak, Ranking und Verlauf deiner Runden")
            ],
            "hr": [
                ("Testirajte svoje znanje o **Real Madridu**", "Vrhunski kviz o trofejima, Galácticosima i povijesti Kraljevskog kluba"),
                ("Pitanja o **trofejima, legendama i Klasicima**", "Od Di Stéfana do Galácticosa i sadašnje momčadi"),
                ("Izazovi prijatelja **putem poveznice**", "Pošalji partiju i saznaj tko bolje poznaje Real Madrid"),
                ("Tvoj rezultat odmah, **runda za rundom**", "Bodovi, postotak točnih odgovora i napredak u svakoj rundi"),
                ("Tko zna više **stiže na vrh**", "Ljestvica uživo između tebe i tvojih prijatelja"),
                ("Pogrešan odgovor? Točan **je objašnjen**", "Svako pitanje prikazuje točan odgovor i razlog"),
                ("Zapeo si? **Iskoristi pomoć**", "Jedna pomoć po pitanju, kad god ti zatreba"),
                ("Vrati se svaki dan i **održi svoj niz**", "Dnevni niz, ljestvica i povijest tvojih rundi")
            ],
            "ar": [
                ("اختبر معلوماتك عن **ريال مدريد**", "أفضل اختبار عن الألقاب وحقبة الغالاكتيكوس وتاريخ الفريق الملكي"),
                ("أسئلة عن **الألقاب والأساطير والكلاسيكو**", "من دي ستيفانو إلى حقبة الغالاكتيكوس والتشكيلة الحالية"),
                ("تحدَّ صديقًا **عبر رابط**", "أرسل الجولة واكتشف من يعرف ريال مدريد أكثر"),
                ("نتيجتك فورًا، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتقدم في كل جولة"),
                ("الأكثر معرفة **يتصدر الترتيب**", "ترتيب مباشر بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة **مشروحة**", "كل سؤال يعرض الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحًا**", "مساعدة واحدة لكل سؤال، وقتما تحتاجها"),
                ("عد كل يوم **وحافظ على تتابعك**", "تتابع يومي وترتيب وسجل لجولاتك")
            ],
            "zh": [
                ("测试你对**皇马**的了解程度", "关于冠军荣誉、银河战舰时代与皇室历史的终极问答"),
                ("题目涵盖**冠军、传奇球星与国家德比**", "从迪斯蒂法诺到银河战舰时代，直至现今阵容"),
                ("**通过链接**挑战好友", "发送对局链接，看看谁更懂皇马"),
                ("成绩**即时呈现，一轮接一轮**", "每轮的得分、正确率与进步一目了然"),
                ("登上**排行榜**榜首", "你与好友之间的实时排名"),
                ("答错了？答案**附带解析**", "每道题都会显示正确答案及原因"),
                ("卡住了？**使用提示**", "每题一次提示，随时可用"),
                ("每天回来，**保持连续答题**", "每日连续答题、排行榜与对局历史")
            ],
            "tr": [
                ("**Real Madrid** bilgini test et", "Şampiyonluklar, Galácticos dönemi ve Bernabéu tarihiyle dolu quiz"),
                ("**Şampiyonluklar, efsaneler ve Clásico'lar** hakkında sorular", "Di Stéfano'dan Galácticos dönemine, bugünkü kadroya kadar"),
                ("Bir arkadaşını **bağlantıyla** meydan oku", "Maçı gönder ve Real Madrid'i kim daha iyi biliyor gör"),
                ("Skorun anında elinde, **turdan tura**", "Puan, doğru cevap yüzdesi ve her turdaki gelişimin"),
                ("En çok bilen **zirveye çıkar**", "Sen ve arkadaşların arasında gerçek zamanlı sıralama"),
                ("Yanlış mı bildin? Cevap **açıklamalı**", "Her soru doğru cevabı ve nedenini gösterir"),
                ("Takıldın mı? **İpucunu kullan**", "İhtiyacın olduğunda soru başına bir yardım"),
                ("Her gün geri dön, **serini sürdür**", "Günlük seri, sıralama ve turlarının geçmişi")
            ]
        }
    },
    "bayern": {
        "name": "Quiz para Fãs do Bayern",
        "colors": [(20, 0, 5), (150, 0, 20), (10, 0, 2)],
        "highlight_color": (255, 90, 90),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Bayern**", "O quiz definitivo sobre Champions, Bundesligas e a história do Rekordmeister"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Beckenbauer e Gerd Müller a Lewandowski e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Bayern"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "de": [
                ("Teste dein Wissen über **Bayern**", "Das ultimative Quiz über Meisterschaften, Champions-League-Titel und die Geschichte des Rekordmeisters"),
                ("Fragen zu **Titeln, Legenden und Klassikern**", "Von Beckenbauer und Gerd Müller bis Lewandowski und dem aktuellen Kader"),
                ("Fordere einen Freund **per Link** heraus", "Schick das Spiel und finde heraus, wer Bayern am besten kennt"),
                ("Dein Ergebnis sofort, **Runde für Runde**", "Punkte, Trefferquote und Fortschritt in jeder Runde"),
                ("Wer mehr weiß, **steht ganz oben**", "Ranking in Echtzeit zwischen dir und deinen Freunden"),
                ("Falsch geraten? Die Antwort wird **erklärt**", "Jede Frage zeigt die richtige Lösung und das Warum"),
                ("Nicht weiter? **Nutze einen Hinweis**", "Eine Hilfe pro Frage, wann immer du sie brauchst"),
                ("Komm täglich zurück und **halte deinen Streak**", "Täglicher Streak, Ranking und Verlauf deiner Runden")
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
                ("Perguntas sobre **títulos, ídolos e Clássicos**", "De Cruyff aos craques atuais do Barça"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Barcelona"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "es": [
                ("Desafía tus conocimientos **del Barcelona**", "El quiz definitivo sobre títulos, ídolos e historia blaugrana"),
                ("Preguntas sobre **títulos, ídolos y Clásicos**", "De Cruyff a las estrellas actuales del Barça"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Barcelona"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "ca": [
                ("Desafia els teus coneixements **del Barça**", "El quiz definitiu sobre títols, ídols i història blaugrana"),
                ("Preguntes sobre **títols, ídols i Clàssics**", "De Cruyff a les estrelles actuals del Barça"),
                ("Desafia un amic **per enllaç**", "Envia la partida i descobreix qui en sap més del Barcelona"),
                ("El teu marcador a l'instant, **partida a partida**", "Puntuació, percentatge d'encert i evolució a cada ronda"),
                ("Qui en sap més **arriba al capdamunt**", "Rànquing en temps real entre tu i els teus amics"),
                ("Has fallat? La resposta ve **explicada**", "Cada pregunta mostra la correcta i el perquè"),
                ("T'has encallat? **Usa una pista**", "Una ajuda per pregunta, quan la necessitis"),
                ("Torna cada dia i **manté la teva ratxa**", "Ratxa diària, rànquing i historial de les teves partides")
            ],
            "en": [
                ("Test your **Barcelona** knowledge", "The ultimate quiz about titles, legends and Blaugrana history"),
                ("Questions on **titles, legends and Clásicos**", "From Cruyff to today's Barça stars"),
                ("Challenge a friend **by link**", "Send the match and see who knows Barcelona best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ]
        }
    },
    "chelsea": {
        "name": "Quiz para Fãs do Chelsea",
        "colors": [(0, 30, 70), (3, 70, 148), (0, 12, 30)],
        "highlight_color": (255, 193, 7),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Chelsea**", "O quiz definitivo sobre títulos, ídolos e história do Chelsea FC"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Lampard e Drogba a Hazard e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Chelsea"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Chelsea** knowledge", "The ultimate quiz on titles, legends and Chelsea FC history"),
                ("Questions on **titles, legends and rivalries**", "From Lampard and Drogba to Hazard and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Chelsea best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ]
        }
    },
    "psg": {
        "name": "Quiz para Fãs do PSG",
        "colors": [(0, 16, 37), (0, 65, 112), (0, 8, 18)],
        "highlight_color": (218, 41, 28),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do PSG**", "O quiz definitivo sobre títulos, ídolos e história do Paris Saint-Germain"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Mbappé e Neymar a Marquinhos e o elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do PSG"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "fr": [
                ("Défiez vos connaissances sur le **PSG**", "Le quiz ultime sur les titres, les légendes et l'histoire du Paris Saint-Germain"),
                ("Questions sur les **titres, légendes et classiques**", "De Mbappé et Neymar à Marquinhos et l'effectif actuel"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui connaît le mieux le PSG"),
                ("Votre score à l'instant, **match après match**", "Points, pourcentage de réussite et progression à chaque manche"),
                ("Le plus fort **grimpe au sommet**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ]
        }
    },
    "liverpool": {
        "name": "Quiz para Fãs do Liverpool",
        # Fallback only — derive_palette() reads visual.primaryColor/accentColor from the
        # tenant seed (red/white) and wins whenever the seed has them, same as realmadrid.
        "colors": [(90, 5, 15), (200, 16, 46), (20, 1, 3)],
        "highlight_color": (200, 16, 46),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Liverpool**", "O quiz definitivo sobre títulos, ídolos e história dos Reds"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Shankly e Gerrard a Salah e ao elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Liverpool"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Liverpool FC** knowledge", "The ultimate quiz on titles, legends and Anfield history"),
                ("Questions on **titles, legends and rivalries**", "From Shankly and Gerrard to Salah and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Liverpool best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ]
        }
    },
    "bocajuniors": {
        "name": "Quiz para Fãs do Boca Juniors",
        "colors": [(0, 8, 20), (0, 19, 38), (5, 5, 13)],
        "highlight_color": (252, 180, 21),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Boca Juniors**", "O quiz definitivo sobre títulos, ídolos e história Xeneize"),
                ("Perguntas sobre **títulos, ídolos e Superclássicos**", "De Maradona e Riquelme ao elenco atual da Bombonera"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Boca"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "es": [
                ("Poné a prueba lo que sabés **del Boca Juniors**", "El quiz definitivo sobre títulos, ídolos e historia Xeneize"),
                ("Preguntas sobre **títulos, ídolos y Superclásicos**", "De Maradona y Riquelme al plantel actual de la Bombonera"),
                ("Desafiá a un amigo **por enlace**", "Mandale la partida y fijate quién sabe más del Boca"),
                ("Tu puntaje al instante, **partida a partida**", "Puntos, porcentaje de acierto y evolución en cada ronda"),
                ("El que más sabe **llega a la cima**", "Clasificación en tiempo real entre vos y tus amigos"),
                ("¿Te equivocaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te trabaste? **Usá una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Volvé todos los días y **mantené tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "riverplate": {
        "name": "Quiz para Fãs do River Plate",
        "colors": [(38, 4, 5), (13, 1, 2), (5, 1, 2)],
        "highlight_color": (235, 28, 36),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do River Plate**", "O quiz definitivo sobre títulos, ídolos e história do Millonario"),
                ("Perguntas sobre **títulos, ídolos e Superclássicos**", "De Di Stéfano e Francescoli ao elenco atual do Monumental"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do River"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "es": [
                ("Poné a prueba lo que sabés **del River Plate**", "El quiz definitivo sobre títulos, ídolos e historia Millonaria"),
                ("Preguntas sobre **títulos, ídolos y Superclásicos**", "De Di Stéfano y Francescoli al plantel actual del Monumental"),
                ("Desafiá a un amigo **por enlace**", "Mandale la partida y fijate quién sabe más del River"),
                ("Tu puntaje al instante, **partida a partida**", "Puntos, porcentaje de acierto y evolución en cada ronda"),
                ("El que más sabe **llega a la cima**", "Clasificación en tiempo real entre vos y tus amigos"),
                ("¿Te equivocaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te trabaste? **Usá una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Volvé todos los días y **mantené tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "clubamerica": {
        "name": "Quiz para Fãs do Club América",
        "colors": [(0, 16, 51), (0, 13, 41), (0, 4, 13)],
        "highlight_color": (254, 225, 43),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Club América**", "O quiz definitivo sobre títulos, ídolos e história Azulcrema"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Cuauhtémoc Blanco ao elenco atual do Estádio Azteca"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do América"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "es": [
                ("Ponte a prueba con **el Club América**", "El quiz definitivo sobre títulos, ídolos e historia Azulcrema"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Cuauhtémoc Blanco al plantel actual del Azteca"),
                ("Reta a un amigo **por enlace**", "Envíale la partida y descubre quién sabe más del América"),
                ("Tu puntaje al instante, **partida a partida**", "Puntos, porcentaje de acierto y evolución en cada ronda"),
                ("El que más sabe **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Te equivocaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te trabaste? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve todos los días y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "chivas": {
        "name": "Quiz para Fãs do Chivas",
        "colors": [(38, 3, 8), (13, 1, 3), (8, 0, 2)],
        "highlight_color": (200, 16, 46),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Chivas Guadalajara**", "O quiz definitivo sobre títulos, ídolos e história do Rebaño Sagrado"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "Do Chava Reyes ao elenco atual do Estádio Akron"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Chivas"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "es": [
                ("Ponte a prueba con **el Chivas Guadalajara**", "El quiz definitivo sobre títulos, ídolos e historia del Rebaño Sagrado"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Chava Reyes al plantel actual del Estadio Akron"),
                ("Reta a un amigo **por enlace**", "Envíale la partida y descubre quién sabe más del Chivas"),
                ("Tu puntaje al instante, **partida a partida**", "Puntos, porcentaje de acierto y evolución en cada ronda"),
                ("El que más sabe **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Te equivocaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te trabaste? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve todos los días y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "alhilal": {
        "name": "Quiz para Fãs do Al-Hilal",
        "colors": [(0, 17, 38), (0, 80, 179), (0, 6, 13)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Al-Hilal**", "O quiz completo sobre o Al-Hilal, seus títulos e sua história"),
                ("Perguntas sobre **títulos, ídolos e o Derby de Riad**", "Da hegemonia na AFC Champions League a ídolos como Sami Al-Jaber"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Al-Hilal"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Al-Hilal** knowledge", "The comprehensive quiz on Al-Hilal, its titles and history"),
                ("Questions on **titles, legends and the Riyadh Derby**", "From AFC Champions League dominance to legends like Sami Al-Jaber"),
                ("Challenge a friend **by link**", "Send the match and see who knows Al-Hilal best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "ar": [
                ("اختبر معلوماتك عن **الهلال**", "كويز شامل عن الهلال وألقابه وتاريخه العريق"),
                ("أسئلة عن **الألقاب والأساطير وديربي الرياض**", "من هيمنة دوري أبطال آسيا إلى أساطير مثل سامي الجابر"),
                ("تحدَّ صديقًا **عبر رابط**", "أرسل الجولة واكتشف من يعرف الهلال أكثر"),
                ("نتيجتك فورًا، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتقدم في كل جولة"),
                ("الأكثر معرفة **يتصدر الترتيب**", "ترتيب مباشر بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة **مشروحة**", "كل سؤال يعرض الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحًا**", "مساعدة واحدة لكل سؤال، وقتما تحتاجها"),
                ("عد كل يوم **وحافظ على تتابعك**", "تتابع يومي وترتيب وسجل لجولاتك")
            ]
        }
    },
    "alahly": {
        "name": "Quiz para Fãs do Al Ahly",
        "colors": [(38, 3, 3), (179, 16, 16), (13, 0, 0)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Al Ahly**", "O quiz definitivo sobre o Clube do Século, seus títulos e sua história"),
                ("Perguntas sobre **títulos, ídolos e o Derby do Cairo**", "Da hegemonia na CAF Champions League a ídolos como Aboutrika"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Al Ahly"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Al Ahly** knowledge", "The ultimate quiz on the Club of the Century, its titles and history"),
                ("Questions on **titles, legends and the Cairo Derby**", "From CAF Champions League dominance to legends like Aboutrika"),
                ("Challenge a friend **by link**", "Send the match and see who knows Al Ahly best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "ar": [
                ("اختبر معلوماتك عن **الأهلي**", "أفضل اختبار عن نادي القرن وألقابه وتاريخه العريق"),
                ("أسئلة عن **الألقاب والأساطير وديربي القاهرة**", "من هيمنة دوري أبطال أفريقيا إلى أساطير مثل أبو تريكة"),
                ("تحدَّ صديقًا **عبر رابط**", "أرسل الجولة واكتشف من يعرف الأهلي أكثر"),
                ("نتيجتك فورًا، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتقدم في كل جولة"),
                ("الأكثر معرفة **يتصدر الترتيب**", "ترتيب مباشر بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة **مشروحة**", "كل سؤال يعرض الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحًا**", "مساعدة واحدة لكل سؤال، وقتما تحتاجها"),
                ("عد كل يوم **وحافظ على تتابعك**", "تتابع يومي وترتيب وسجل لجولاتك")
            ]
        }
    },
    "galatasaray": {
        "name": "Quiz para Fãs do Galatasaray",
        "colors": [(38, 3, 10), (169, 4, 50), (13, 1, 4)],
        "highlight_color": (253, 185, 18),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Galatasaray**", "O quiz definitivo sobre títulos, ídolos e história do Cimbom"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "Da conquista da Copa da UEFA em 2000 ao elenco atual do Aslan"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Galatasaray"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "tr": [
                ("**Galatasaray** bilgini test et", "Cimbom'un tarihi, kupaları ve efsaneleri üzerine en kapsamlı bilgi yarışması"),
                ("**Kupalar, efsaneler ve klasikler** üzerine sorular", "2000 UEFA Kupası zaferinden Aslan'ın bugünkü kadrosuna kadar"),
                ("Bir arkadaşını **linkle** meydan oku", "Turu gönder, Galatasaray'ı kim daha iyi biliyor gör"),
                ("Skorun anında, **tur be tur**", "Puan, doğru cevap yüzdesi ve her turdaki gelişimin"),
                ("Daha çok bilen **zirveye çıkar**", "Sen ve arkadaşların arasında gerçek zamanlı sıralama"),
                ("Yanlış mı bildin? Cevap **açıklamalı gelir**", "Her soru doğru cevabı ve nedenini gösterir"),
                ("Takıldın mı? **İpucu kullan**", "Her soru için bir yardım, ihtiyacın olduğunda"),
                ("Her gün geri gel, **serini koru**", "Günlük seri, sıralama ve tur geçmişin")
            ]
        }
    },
    "celtic": {
        "name": "Quiz para Fãs do Celtic",
        "colors": [(5, 26, 7), (27, 94, 32), (2, 13, 4)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Celtic**", "O quiz definitivo sobre títulos, ídolos e história dos Bhoys"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "Dos Lisbon Lions de 1967 ao Old Firm contra o Rangers"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Celtic"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Celtic** knowledge", "The ultimate quiz on titles, legends and the Hoops' history"),
                ("Questions on **titles, legends and the Old Firm**", "From the 1967 Lisbon Lions to today's clashes with Rangers"),
                ("Challenge a friend **by link**", "Send the match and see who knows Celtic best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ]
        }
    },
    "rangers": {
        "name": "Quiz para Fãs do Rangers",
        "colors": [(0, 26, 48), (0, 102, 178), (0, 13, 24)],
        "highlight_color": (255, 255, 255),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Rangers**", "O quiz completo sobre títulos, ídolos e história dos Gers"),
                ("Perguntas sobre **títulos, lendas e o Old Firm**", "Dos 55 títulos escoceses à Recopa de 1972 e clássicos com o Celtic"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Rangers"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Rangers** knowledge", "The comprehensive quiz on titles, legends and the Gers' history"),
                ("Questions on **titles, legends and the Old Firm**", "From 55 league titles and the 1972 Cup Winners' Cup to Ibrox glory"),
                ("Challenge a friend **by link**", "Send the match and see who knows Rangers best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ]
        }
    },
    "alnassr": {
        "name": "Quiz para Fãs do Al-Nassr",
        "colors": [(6, 19, 36), (10, 34, 64), (2, 7, 13)],
        "highlight_color": (246, 185, 0),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Al-Nassr**", "O quiz completo sobre títulos, ídolos e história do Al-Alami"),
                ("Perguntas sobre **títulos, lendas e o Derby de Riad**", "De Majed Abdullah a Cristiano Ronaldo e a história dos Cavaleiros de Najd"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Al-Nassr"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Al-Nassr** knowledge", "The comprehensive quiz on Al-Alami's titles, legends and history"),
                ("Questions on **titles, legends and Riyadh derbies**", "From Majed Abdullah to Cristiano Ronaldo and the FIFA Club World Cup"),
                ("Challenge a friend **by link**", "Send the match and see who knows Al-Nassr best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "ar": [
                ("اختبر معلوماتك عن **نادي النصر**", "الكويز الشامل عن بطولات العالمي، الأساطير وتاريخ فرسان نجد"),
                ("أسئلة عن **البطولات، الأساطير وديربي الرياض**", "من ماجد عبد الله إلى كريستيانو رونالدو ومشاركات كأس العالم للأندية"),
                ("تحدَّ صديقك **عبر الرابط**", "أرسل التحدي واكتشف من يعرف النصر أكثر"),
                ("نتيجتك فورية، **جولة بعد جولة**", "النقاط، دقة الإجابات وتطور مستواك في كل مباراة"),
                ("من يعرف أكثر **يتصدر الترتيب**", "ترتيب مباشر بينك وبين أصدقائك المشجعين"),
                ("أخطأت؟ الإجابة تأتيك **مشروحة**", "كل سؤال يوضح لك الإجابة الصحيحة والسبب"),
                ("واجهت صعوبة؟ **استخدم تلميحاً**", "مساعدة في كل سؤال عندما تحتاجها"),
                ("عد يومياً و**حافظ على سلسلتك**", "سلسلة يومية، لوحة الشرف وتاريخ جولاتك")
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


def _contrast_ratio(rgb_a, rgb_b):
    # WCAG contrast ratio between two colours, e.g. a highlight word against the canvas
    # it sits on. Order-independent: darker of the two always goes in the denominator.
    l_a, l_b = _relative_luminance(rgb_a), _relative_luminance(rgb_b)
    lighter, darker = max(l_a, l_b), min(l_a, l_b)
    return (lighter + 0.05) / (darker + 0.05)


def _shade(rgb, factor):
    if factor >= 1:
        return tuple(min(255, int(c + (255 - c) * (factor - 1))) for c in rgb)
    return tuple(max(0, int(c * factor)) for c in rgb)


# Single comfortable floor for every text role (WCAG AA body text). The headline would
# legally pass at 3:1 as large text, but the text band is engineered dark enough that
# 4.5:1 costs nothing and reads better at Play Store thumbnail scale.
MIN_TEXT_CONTRAST = 4.5

# Text band: the top of the canvas is painted with the accent shaded to this factor —
# dark, but still carrying the brand hue ("night gold", not brown). Every text role sits
# on this one flat colour, so contrast is exact, not sampled across a gradient.
TEXT_BAND_SHADE = 0.18
# Greys/whites/blacks cannot "highlight" a word by colour, only by weight — anything
# under this HLS saturation is skipped as a highlight candidate.
MIN_HIGHLIGHT_SATURATION = 0.15
# How far below the text band the background takes to reach the full accent colour
# (fraction of canvas height). The ramp starts exactly at the band's end (where the
# mockup begins) and is deliberately long — 0.18 read as abrupt (user review 2026-09-03).
ACCENT_REACH_RATIO = 0.42

WHITE, NEAR_BLACK = (255, 255, 255), (12, 20, 32)
SUBHEAD_ON_DARK, SUBHEAD_ON_LIGHT = (224, 224, 224), (48, 60, 78)


def _saturation(rgb):
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))[2]


def _lighten_until_readable(rgb, background, target_contrast, step=0.05):
    """Raises `rgb`'s HLS lightness just enough to clear `target_contrast` against
    `background`, pushing saturation toward 1.0 alongside it.

    A dark brand colour (cruzeiro's navy, flamengo's red) on the dark text band cannot
    pass as-is. A flat RGB blend toward white technically keeps the hue but desaturates
    as fast as it lightens — the result read as "apagado" (washed-out near-white) rather
    than "highlighted blue" (user feedback, 2026-09-03). Lightening in HLS while boosting
    saturation keeps the colour visibly vivid at the same contrast ratio.
    """
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    factor = 0.0
    while factor < 1.0:
        cr, cg, cb = colorsys.hls_to_rgb(h, l + (1 - l) * factor, min(1.0, s + factor))
        candidate = (int(cr * 255), int(cg * 255), int(cb * 255))
        if _contrast_ratio(candidate, background) >= target_contrast:
            return candidate
        factor += step
    return WHITE


def _pick_highlight(primary, accent, band, headline_color):
    """Brand colour for the **highlighted** word, measured against the text band.

    Prefers the more saturated of the two brand colours as-is; if neither clears the
    floor, lightens the most saturated one. Falls back to the headline colour (weight-only
    emphasis) when the tenant has no saturated colour at all — santos is white-on-white.
    """
    candidates = sorted((primary, accent), key=_saturation, reverse=True)
    vivid = [c for c in candidates if _saturation(c) >= MIN_HIGHLIGHT_SATURATION]
    if not vivid:
        return headline_color
    for color in vivid:
        if _contrast_ratio(color, band) >= MIN_TEXT_CONTRAST:
            return color
    return _lighten_until_readable(vivid[0], band, MIN_TEXT_CONTRAST)


def derive_palette(tenant_key):
    """Screenshot palette derived from the tenant seed, never hand-picked.

    Layout (2026-09-03 redesign, after scrim + stroke attempts read as amateur): the top
    of the canvas is a flat dark band in the accent's hue, holding headline + subhead;
    below the text the background ramps to the full accent (where the mockup sits) and
    on to a 65% shade at the bottom. The app paints its own background with
    `primaryColor`, so the canvas uses `accentColor` to keep the phone separating from
    the backdrop.

    Text never gets a stroke, shadow or overlay: the band is dark by construction, so
    white / light-grey / the brand colour are measured against ONE exact colour and
    pass on their own. `primary`/`accent` order for the highlight is by saturation.

    Returns None when the seed is missing so the caller keeps its hardcoded colours.
    """
    brand = _load_brand_colors(tenant_key)
    if not brand:
        return None
    primary, accent = brand
    return _palette_from_brand(primary, accent)


def _load_brand_colors(tenant_key):
    """(primary, accent) RGB tuples from the tenant seed, or None if either is missing."""
    seed_path = os.path.join(ALEFLY_SEEDS, f"{tenant_key}.json")
    if not os.path.exists(seed_path):
        return None
    with open(seed_path, encoding="utf-8") as fh:
        visual = (json.load(fh).get("visual") or {})
    accent = _hex_to_rgb(visual.get("accentColor"))
    primary = _hex_to_rgb(visual.get("primaryColor"))
    return (primary, accent) if accent and primary else None


def _palette_from_brand(primary, accent):
    band = _shade(accent, TEXT_BAND_SHADE)
    # Computed, not assumed: at 18% shade even a white accent lands at (46,46,46), so
    # white wins everywhere today — the max() is what keeps that true if the shade
    # constant ever moves.
    headline_color = max((WHITE, NEAR_BLACK), key=lambda c: _contrast_ratio(c, band))
    subhead_color = SUBHEAD_ON_DARK if headline_color == WHITE else SUBHEAD_ON_LIGHT
    if _contrast_ratio(subhead_color, band) < MIN_TEXT_CONTRAST:
        subhead_color = headline_color

    return {
        "band": band,
        "colors": [band, accent, _shade(accent, 0.65)],
        "headline_color": headline_color,
        "subhead_color": subhead_color,
        "highlight_color": _pick_highlight(primary, accent, band, headline_color),
    }


ALEFLY_ICONS = "/Users/yuripacheco/Projetos/alefly/tools/tenant-icons-python/icons-1024"

# Poster slot geometry, as fractions of the canvas: icon takes 74% of the width (reads at
# search-thumbnail size), corner radius matches the launcher-icon squircle (22%), and the
# icon sits a fixed 6% below the copy while never crossing an 8% bottom margin.
POSTER_ICON_WIDTH_RATIO = 0.74
POSTER_ICON_CORNER_RATIO = 0.22
POSTER_ICON_TOP_GAP_RATIO = 0.06
POSTER_ICON_BOTTOM_MARGIN_RATIO = 0.08


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
    size = int(cw * POSTER_ICON_WIDTH_RATIO)
    icon = Image.open(icon_path).convert("RGBA").resize((size, size), Image.LANCZOS)

    radius = int(size * POSTER_ICON_CORNER_RATIO)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=radius, fill=255)

    # Sits a fixed breath below the copy instead of centring in the leftover space —
    # centring left a dead band under the subheadline and crowded the bottom margin.
    x = (cw - size) // 2
    y = min(top_y + int(ch * POSTER_ICON_TOP_GAP_RATIO), ch - size - int(ch * POSTER_ICON_BOTTOM_MARGIN_RATIO))

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
    6: {"scale": ZOOM_WIDE, "angle": 0, "x_off": 0},
    7: {"scale": ZOOM_TALL, "angle": 0, "x_off": 0},
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
    {"file": "07-ranking.png",         "crop": None, "frame": True},
    {"file": "03-answer-feedback.png", "crop": None, "frame": True},
    {"file": "06-hint-used.png",       "crop": None, "frame": True},
    {"file": "05-home-scrolled.png",   "crop": None, "frame": True},
]

# Four-caption tenants (not yet on the eight-slot spec above) map captions positionally
# onto these captures. Deliberately a different order from SLIDE_SOURCES: slot 3 there is
# the share sheet, here it is the answer feedback. Retire together with the last legacy tenant.
LEGACY_SLIDE_FILES = ["01-home.png", "02-question.png", "03-answer-feedback.png", "04-result-summary.png"]

# Locales written right-to-left. Nunito carries no Arabic glyphs at all — an "ar"
# slide rendered with it comes out as a row of .notdef boxes, which measures a normal
# width so only looking at the image catches it.
RTL_LOCALES = {"ar"}
ARABIC_FONTS = ("/System/Library/Fonts/SFArabic.ttf", "/System/Library/Fonts/GeezaPro.ttc")

# Same .notdef-box failure as Arabic: Nunito carries no CJK glyphs.
CJK_LOCALES = {"zh"}
CJK_FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"


Fonts = namedtuple("Fonts", "headline highlight subhead")

# The app's own typeface (Android res/font, iOS bundle and web all ship Nunito) — the
# screenshots used Montserrat until 2026-09-03, which made the listing look like a
# different product from the app it advertises. Single variable file, weight axis
# 200-1000, so every weight the app uses is available without extra font files.
NUNITO_VARIABLE = "/Users/yuripacheco/Projetos/alefly/shared/mobile/src/androidMain/res/font/nunito_variable.ttf"
# Headline 700 vs highlight 900: at 800 the two Nunito weights sat too close to read
# as a hierarchy side by side (visual review 2026-09-03).
HEADLINE_WEIGHT, HIGHLIGHT_WEIGHT, SUBHEAD_WEIGHT = 700, 900, 600


def _nunito(size, weight):
    font = ImageFont.truetype(NUNITO_VARIABLE, size)
    font.set_variation_by_axes([weight])
    return font


def get_fonts(platform="ios", locale="pt", scale=1.0):
    # Hierarchy comes from weight + size only (no stroke/shadow): headline 700, the
    # **highlighted** word 900, subhead 600. Subhead sized for legibility at real Play
    # Store thumbnail scale (~4x smaller than this canvas) — 50pt regular was unreadable
    # there (audit 2026-09-03), independent of colour. `scale` < 1 is the auto-fit
    # fallback in layout_text_block, never a per-tenant choice.
    size_h, size_s = (148, 88) if platform == "ipad" else (104, 64)
    size_h, size_s = int(size_h * scale), int(size_s * scale)
    if locale in RTL_LOCALES:
        arabic = next((f for f in ARABIC_FONTS if os.path.exists(f)), None)
        if arabic:
            head = ImageFont.truetype(arabic, size_h)
            return Fonts(head, head, ImageFont.truetype(arabic, size_s))
    if locale in CJK_LOCALES and os.path.exists(CJK_FONT):
        # index 2/0 = W6 (bold) / W3 (regular) faces inside the .ttc. CJK strokes are
        # already heavier at a given point size than Latin type, so W3 still reads fine
        # for the subhead. No heavier face than W6 in the .ttc, so highlight == headline.
        head = ImageFont.truetype(CJK_FONT, size_h, index=2)
        return Fonts(head, head, ImageFont.truetype(CJK_FONT, size_s, index=0))
    return Fonts(_nunito(size_h, HEADLINE_WEIGHT), _nunito(size_h, HIGHLIGHT_WEIGHT),
                 _nunito(size_s, SUBHEAD_WEIGHT))

# CJK Unified Ideographs + common fullwidth punctuation. These scripts carry no spaces
# between words, so wrapping has to break per character instead of per \S+ token.
CJK_RE = re.compile(r'[一-鿿㐀-䶿豈-﫿　-〿＀-￯]')

def _is_cjk_char(s):
    return len(s) == 1 and bool(CJK_RE.match(s))

def _split_words(text):
    return list(text) if CJK_RE.search(text) else text.split()

def expand_bold_spans(text):
    """Rewrites text into a fully space-delimited token stream.

    For Latin languages the source text already has spaces around **bold** spans, so
    this only needed to split multi-word spans into individually-highlighted **word**
    units. CJK text has no spaces anywhere in the source — reusing the old regex
    substitution left the plain text flush against the `**` markers, and the
    whitespace-only tokenizer below (`\\S+`) then swallowed marker and neighbouring
    characters into one dirty token. Walking the string once and re-joining every
    unit (bold or plain, word or CJK character) with real spaces gives wrap_text a
    clean, script-agnostic token boundary everywhere.
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        if text[i:i + 2] == '**':
            end = text.find('**', i + 2)
            if end == -1:
                out.append(text[i:])
                break
            out.extend(f'**{u}**' for u in _split_words(text[i + 2:end]))
            i = end + 2
        elif CJK_RE.match(text[i]):
            out.append(text[i])
            i += 1
        else:
            j = i
            while j < n and text[j:j + 2] != '**' and not CJK_RE.match(text[j]):
                j += 1
            out.extend(text[i:j].split())
            i = j
    return ' '.join(out)

def _measure_units(text, draw, font, hl_font, space_w):
    """Tokens grouped into unbreakable units, each with its rendered width.

    A `**highlight span**` (expanded to one `**word**` per token by expand_bold_spans)
    is one unit, so "da **Bíblia**" never lands with "da" on one line and "Bíblia" on
    the next. Highlight tokens are measured with the heavier face — at weight 900 a word
    is visibly wider than the body weight, and measuring it with the body font over-fills.
    """
    tokens = re.findall(r'\*\*[^*]+\*\*|\S+', text)
    units, i = [], 0
    while i < len(tokens):
        j = i + 1
        while tokens[i].startswith('**') and j < len(tokens) and tokens[j].startswith('**'):
            j += 1
        width, prev = 0, ''
        for k, tok in enumerate(tokens[i:j]):
            visible = tok.replace('**', '')
            # No gap between two adjacent bare CJK characters — real spacing would look
            # like letter-spaced Latin type, which Chinese headlines don't use.
            gap = 0 if k == 0 or (_is_cjk_char(prev) and _is_cjk_char(visible)) else space_w
            width += gap + draw.textlength(visible, font=hl_font if tok.startswith('**') else font)
            prev = visible
        units.append((tokens[i:j], width))
        i = j
    return units


def _greedy_lines(units, max_width, space_w):
    lines, current, current_w = [], [], 0
    for tokens, width in units:
        first, last = tokens[0].replace('**', ''), current[-1].replace('**', '') if current else ''
        gap = 0 if not current or (_is_cjk_char(last) and _is_cjk_char(first)) else space_w
        if current and current_w + gap + width > max_width:
            lines.append(current)
            current, current_w = list(tokens), width
        else:
            current += tokens
            current_w += gap + width
    if current:
        lines.append(current)
    return lines


def _line_width(units, space_w):
    width, prev = 0, ''
    for i, (tokens, w) in enumerate(units):
        first = tokens[0].replace('**', '')
        width += w + (0 if i == 0 or (_is_cjk_char(prev) and _is_cjk_char(first)) else space_w)
        prev = tokens[-1].replace('**', '')
    return width


def wrap_text(text, draw, font, max_width, hl_font=None):
    """Greedy wrap decides the line count; then every way of breaking the units into
    that many lines is scored and the most even one wins (CSS `text-wrap: balance`),
    instead of a full first line and a one-word orphan at the end. Brute force is fine:
    a headline is ≤ ~12 units and ≤ 4 lines."""
    space_w = draw.textlength(' ', font=font)
    units = _measure_units(text, draw, font, hl_font or font, space_w)
    # A highlight span wider than the column must break like normal words — keeping it
    # whole overflowed the canvas edge (found on realmadrid slide 2, 2026-09-03).
    units = [u for tokens, w in units
             for u in ([(tokens, w)] if w <= max_width else
                       [([tok], draw.textlength(tok.replace('**', ''), font=hl_font or font)) for tok in tokens])]
    if not units:
        return []
    n_lines = len(_greedy_lines(units, max_width, space_w))
    best, best_score = None, None
    for breaks in itertools.combinations(range(1, len(units)), n_lines - 1):
        bounds = (0, *breaks, len(units))
        lines = [units[a:b] for a, b in zip(bounds, bounds[1:])]
        widths = [_line_width(line, space_w) for line in lines]
        if max(widths) > max_width:
            continue
        mean = sum(widths) / len(widths)
        score = sum((w - mean) ** 2 for w in widths)
        if best_score is None or score < best_score:
            best, best_score = lines, score
    return [' '.join(tok for tokens, _ in line for tok in tokens) for line in best]

def _draw_line_centered(draw, line, font, y, width, style, highlight_color, rtl=False, hl_font=None):
    # No stroke, no shadow: the text band is dark by construction (see derive_palette),
    # so plain fills pass contrast on their own. Outlines read as amateur (user review,
    # 2026-09-03) and a fixed-offset shadow only ever darkened, which never helped.
    hl_font = hl_font or font
    if rtl:
        # Drawn in one call so Raqm can shape and reorder the run. The per-word cursor
        # below advances left-to-right, which lays an Arabic line out backwards; the
        # highlight colour is the price of correct text, and it is the cheaper loss.
        visible = line.replace('**', '')
        x = (width - draw.textlength(visible, font=font)) // 2
        draw.text((x, y), visible, fill=style.color, font=font)
        return
    space_w = draw.textlength(' ', font=font)
    parts = re.findall(r'\*\*[^*]+\*\*|\S+', line)
    segments = []
    gaps = []
    total_w = 0
    prev_visible = ''
    for i, part in enumerate(parts):
        is_hl = part.startswith('**') and part.endswith('**')
        visible = part.replace('**', '')
        w = draw.textlength(visible, font=hl_font if is_hl else font)
        gap = 0 if i > 0 and _is_cjk_char(prev_visible) and _is_cjk_char(visible) else (space_w if i > 0 else 0)
        gaps.append(gap)
        segments.append((visible, is_hl, w))
        total_w += w + gap
        prev_visible = visible

    cur_x = (width - total_w) // 2
    for (visible, is_hl, w), gap in zip(segments, gaps):
        cur_x += gap
        draw.text((cur_x, y), visible, fill=highlight_color if is_hl else style.color,
                  font=hl_font if is_hl else font)
        cur_x += w

def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

# Only for the legacy hardcoded palettes (palette is None): those reused the in-app
# background under white text, and 55% darkening was tuned by eye before derive_palette
# existed. Every seed-backed tenant goes through derive_palette and its measured contrast.
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
    
    # Normalized pixel grid
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

def draw_band_background(canvas, band, accent, bottom, band_end_y):
    """Vertical gradient: flat `band` colour from the top down to `band_end_y` (the
    bottom of the text block), ramping to the full `accent` over ACCENT_REACH_RATIO of
    the height, then easing to `bottom` at the canvas edge.

    The band's extent is measured from the real wrapped text, so a 3-line headline and a
    1-line one both get exactly the dark surface they need — the mockup starts where the
    accent begins ("dark on top, lightening from where the mockup sits", user direction
    2026-09-03). Replaces the diagonal gradient + full-canvas scrim, which darkened the
    mockup area too and turned vivid accents muddy.
    """
    w, h = canvas.size
    y = np.arange(h, dtype=np.float32)[:, None]
    reach = max(1.0, h * ACCENT_REACH_RATIO)
    # smoothstep so the band has no visible seam where the ramp starts.
    t_accent = smoothstep((y - band_end_y) / reach)
    t_bottom = np.clip((y - band_end_y - reach) / max(1.0, h - band_end_y - reach), 0.0, 1.0)
    band, accent, bottom = (np.array(c, dtype=np.float32) for c in (band, accent, bottom))
    col = band + (accent - band) * t_accent
    col = col + (bottom - col) * t_bottom
    rows = np.repeat(col[:, None, :], w, axis=1)
    canvas.paste(Image.fromarray(rows.astype(np.uint8), mode="RGB"), (0, 0))


TextLayout = namedtuple("TextLayout", "fonts h_lines s_lines h_lh s_lh gap total_h")

# Auto-fit: shrink the type in small steps only when a caption would not fit at the
# nominal size — more lines than the layout is designed for, or a highlight span wider
# than the column (so it can stay on one line instead of being split). 82% is the floor;
# below that the caption is a copy problem, not a layout one.
MAX_HEADLINE_LINES, MAX_SUBHEAD_LINES = 3, 3
AUTOFIT_SCALES = (1.0, 0.96, 0.92, 0.88, 0.85, 0.82)
# Keeping a highlight span on one line is worth at most this much shrink; past it the
# span breaks by word instead, so headline sizes stay consistent across a tenant's set.
KEEP_SPAN_MIN_SCALE = 0.92


def _fits(draw, text, font, hl_font, max_width, max_lines, keep_spans):
    space_w = draw.textlength(' ', font=font)
    units = _measure_units(text, draw, font, hl_font, space_w)
    if keep_spans and any(w > max_width for _, w in units):
        return False
    units = [u for tokens, w in units
             for u in ([(tokens, w)] if w <= max_width else
                       [([tok], draw.textlength(tok.replace('**', ''), font=hl_font)) for tok in tokens])]
    return len(_greedy_lines(units, max_width, space_w)) <= max_lines


def layout_text_block(canvas, headline, subheadline, platform="ios", locale="pt"):
    """Wraps both blocks and returns their geometry (plus the fonts actually used, after
    auto-fit) — split from drawing so the background can be painted to the measured
    text height before the text goes on."""
    w, _ = canvas.size
    text_w = w - (300 if platform == "ipad" else 220)
    draw = ImageDraw.Draw(canvas)
    headline, subheadline = expand_bold_spans(headline), expand_bold_spans(subheadline)
    attempts = [(sc, True) for sc in AUTOFIT_SCALES if sc >= KEEP_SPAN_MIN_SCALE] + [(sc, False) for sc in AUTOFIT_SCALES]
    for scale, keep_spans in attempts:
        fonts = get_fonts(platform=platform, locale=locale, scale=scale)
        if (_fits(draw, headline, fonts.headline, fonts.highlight, text_w, MAX_HEADLINE_LINES, keep_spans)
                and _fits(draw, subheadline, fonts.subhead, fonts.subhead, text_w, MAX_SUBHEAD_LINES, keep_spans)):
            break
    h_lines = wrap_text(headline, draw, fonts.headline, text_w, hl_font=fonts.highlight)
    s_lines = wrap_text(subheadline, draw, fonts.subhead, text_w)
    h_lh = int(fonts.headline.size * HEADLINE_LINE_HEIGHT_RATIO)
    s_lh = int(fonts.subhead.size * SUBHEAD_LINE_HEIGHT_RATIO)
    gap = int(fonts.headline.size * HEADLINE_SUBHEAD_GAP_RATIO)
    total_h = (len(h_lines) * h_lh) + (len(s_lines) * s_lh) + gap
    return TextLayout(fonts, h_lines, s_lines, h_lh, s_lh, gap, total_h)


def draw_text_block(canvas, layout, highlight_color, platform="ios",
                    headline_style=None, subhead_style=None, locale="pt"):
    fonts = layout.fonts
    w, _ = canvas.size
    top_margin = 190 if platform == "ipad" else TEXT_TOP_MARGIN
    headline_style = headline_style or HEADLINE_STYLE
    subhead_style = subhead_style or SUBHEAD_STYLE
    draw = ImageDraw.Draw(canvas)
    rtl = locale in RTL_LOCALES

    curr_y = top_margin
    for line in layout.h_lines:
        _draw_line_centered(draw, line, fonts.headline, curr_y, w, headline_style, highlight_color, rtl,
                            hl_font=fonts.highlight)
        curr_y += layout.h_lh
    curr_y += layout.gap
    for line in layout.s_lines:
        _draw_line_centered(draw, line, fonts.subhead, curr_y, w, subhead_style, highlight_color, rtl)
        curr_y += layout.s_lh

def _paste_with_shadow(canvas, layer, x, y, blur=28, offset=18, opacity=0.45):
    """Composites an RGBA layer with a soft drop shadow under it.

    The bezel takes the text band's colour, so on a dark-accent tenant (flamengo,
    juventus) the device would melt into the band with only the faint rim separating
    it. A diffuse shadow built from the layer's own alpha separates it on every
    background without depending on colour.
    """
    alpha = layer.getchannel("A").filter(ImageFilter.GaussianBlur(blur)).point(lambda a: int(a * opacity))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", layer.size, (0, 0, 0, 255)), (x, y + offset), alpha)
    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), shadow).convert("RGB"), (0, 0))
    canvas.paste(layer, (x, y), layer)


def process_screenshot(tenant_key, idx, headline, subheadline, input_path, output_path, platform="android", use_slide_sources=False, locale="pt"):
    config = TENANT_CONFIGS[tenant_key]
    if platform == "ipad":
        cw, ch = 2048, 2732
    elif platform == "android":
        cw, ch = ANDROID_WIDTH, ANDROID_HEIGHT
    else:
        cw, ch = WIDTH, HEIGHT
    canvas = Image.new('RGB', (cw, ch))
    palette = derive_palette(tenant_key)
    layout = layout_text_block(canvas, headline, subheadline, platform=platform, locale=locale)
    top_margin = 190 if platform == "ipad" else TEXT_TOP_MARGIN
    device_y = top_margin + layout.total_h + MIN_TEXT_DEVICE_GAP

    if palette:
        band, accent, bottom = palette["colors"]
        draw_band_background(canvas, band, accent, bottom, device_y)
        headline_style = TextStyle(color=palette["headline_color"])
        subhead_style = TextStyle(color=palette["subhead_color"])
        highlight = palette["highlight_color"]
    else:
        # Legacy hardcoded palettes reused the in-app background and need dimming to sit
        # behind white text; darken_color() exists only for them.
        draw_brand_background(canvas, [darken_color(c) for c in config["colors"]])
        headline_style = subhead_style = None
        highlight = config["highlight_color"]
    draw_text_block(canvas, layout, highlight, platform=platform,
                    headline_style=headline_style, subhead_style=subhead_style, locale=locale)

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
        if palette:
            # Bezel in the text band's own dark tint with a faint lighter rim, so the
            # device reads as part of the composition instead of a grey sticker outline
            # sitting on the brand colour (visual review 2026-09-03).
            border_col = palette["band"]
            light_col = _shade(palette["band"], 1.22)

        mask = Image.new('L', (target_w, target_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, target_w, target_h], radius=radius, fill=255)

        pad = 60 if platform == "ipad" else 50
        device_layer = Image.new("RGBA", (target_w + (pad*2), target_h + (pad*2)), (0,0,0,0))
        device_layer.paste(screen, (pad, pad), mask)

        if draw_frame:
            border_w = 20 if platform == "ipad" else 22
            # The stroke is centred on the rectangle it is given, so drawing it on the screen's
            # own bounds ate ~border_w/2 of pixels off each edge — the bezel was cropping the
            # screenshot instead of surrounding it. Offsetting the rect outward by half the
            # stroke makes its inner edge land exactly on the screen edge, touching without
            # overlapping. pad (50) leaves room for the excursion.
            half = border_w // 2
            ImageDraw.Draw(device_layer).rounded_rectangle(
                [pad - half, pad - half, target_w + pad + half, target_h + pad + half],
                radius=radius + half, outline=border_col, width=border_w)
            ImageDraw.Draw(device_layer).rounded_rectangle(
                [pad - border_w, pad - border_w, target_w + pad + border_w, target_h + pad + border_w],
                radius=radius + border_w, outline=light_col, width=3)

            cam_x = (target_w + (pad*2)) // 2
            if platform == "android":
                ImageDraw.Draw(device_layer).ellipse([cam_x-10, 80, cam_x+10, 100], fill=(15,15,15))
            elif platform == "ios":
                island_w, island_h = 135, 38
                ImageDraw.Draw(device_layer).rounded_rectangle([cam_x-(island_w//2), 75, cam_x+(island_w//2), 75+island_h], radius=18, fill=(10,10,10))

        if draw_frame and conf["angle"] != 0 and platform != "ipad":
            device_layer = device_layer.rotate(conf["angle"], resample=Image.BICUBIC, expand=True)

        x_off = int(conf["x_off"] * (cw / REFERENCE_WIDTH))
        _paste_with_shadow(canvas, device_layer, (cw - device_layer.width) // 2 + x_off, device_y)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    canvas.save(output_path, quality=100, subsampling=0)
    print(f"  ✅ Saved [{platform.upper()}]: {output_path}")

# Per-tenant override of STORE_LOCALE_BY_CONTENT_LOCALE below. Argentine clubs' "es" content
# (voseo, Rioplatense Spanish) targets Google Play's "es-419" (Latin America) listing locale,
# not "es-ES" (Spain) -- the global default used by Spain-based tenants like realmadrid/barcelona.
TENANT_STORE_LOCALE_OVERRIDES = {
    "bible": {"pt": ["pt-BR", "pt-PT", "pt-AO"]},
    "bocajuniors": {"es": "es-419"},
    "riverplate": {"es": "es-419"},
    "clubamerica": {"es": "es-419"},
    "chivas": {"es": "es-419"},
    "celtic": {"en": "en-GB"},
    "rangers": {"en": "en-GB"},
}

# Content-locale (used by slides_by_locale / capture-multilocale-screenshots.sh
# subfolders) -> store-listing locale folder name (store-assets/{tenant}/{locale}/),
# same convention already used by alefly's ASO metadata and feature-graphic pipelines.
STORE_LOCALE_BY_CONTENT_LOCALE = {
    "pt": "pt-BR",
    "es": "es-ES",
    "ca": "ca",
    "en": "en-US",
    # "id" and "tr" stay bare on purpose. store-assets/{tenant}/ carries BOTH id/ and
    # id-ID/, and Play resolves Indonesian as "id" — the longer folder is the one it
    # ignores, so writing there would hide the screenshots. There is no tr-TR/ folder at
    # all; the Turkish metadata lives in tr/.
    "id": "id",
    "fr": "fr-FR",
    "de": "de-DE",
    "hr": "hr",
    "ar": "ar",
    "zh": "zh-CN",
    "tr": "tr",
    "it": "it-IT",
}

def resolve_store_locales(tenant: str, locale: str) -> list[str]:
    """Store-listing locale folders for a given content locale. A tenant override
    may be a single string (existing behavior, one country) or a list of strings
    (multiple country storefronts sharing the same content/screenshots)."""
    override = TENANT_STORE_LOCALE_OVERRIDES.get(tenant, {}).get(locale)
    if override is None:
        return [STORE_LOCALE_BY_CONTENT_LOCALE.get(locale, "pt-BR")]
    if isinstance(override, str):
        return [override]
    return list(override)

def run_factory(target_tenant=None, target_platform="all", target_locale=None):
    platforms = ["android", "ios", "ipad"] if target_platform == "all" else [target_platform]

    print(f"🚀 Alefly screenshot factory (platforms: {', '.join(platforms).upper()})...")

    tenants = [target_tenant] if target_tenant else list(TENANT_CONFIGS.keys())
    failures = []

    for platform in platforms:
        print(f"\n📱 PLATFORM: {platform.upper()}")
        for tenant in tenants:
            if tenant not in TENANT_CONFIGS:
                print(f"⚠️ Tenant '{tenant}' not found in TENANT_CONFIGS.")
                continue

            config = TENANT_CONFIGS[tenant]
            print(f"  📦 App: {config['name']} ({tenant})")

            is_multi_locale = "slides_by_locale" in config
            if is_multi_locale:
                locales = [target_locale] if target_locale else list(config["slides_by_locale"].keys())
            else:
                if target_locale and target_locale != "pt":
                    print(f"  ⚠️ Tenant '{tenant}' only has pt slides — ignoring --locale {target_locale}.")
                locales = ["pt"]

            base_output_dir = os.path.join(ALEFLY_REPO_ROOT, "output/store-assets")

            for locale in locales:
                slides = config["slides_by_locale"][locale] if is_multi_locale else config["slides"]
                store_locales = resolve_store_locales(tenant, locale)

                sub = ("android", "screenshots") if platform == "android" else ("ios", "screenshots", "ipad" if platform == "ipad" else "iphone")
                # Per-locale folder first; then the unsuffixed legacy folder (a tenant that
                # became multi-locale after its captures were taken — 14 clubs on 2026-09-03
                # were silently skipped here); Android last falls back to iPhone captures.
                # The capture script archives per locale whenever the SEED lists several
                # locales, independent of whether TENANT_CONFIGS has slides_by_locale — so the
                # locale folder is tried first for every tenant (flamengo has slides in pt only
                # here but pt/en/es in the seed; its fresh captures live in screenshots/pt/).
                candidates = [os.path.join(base_output_dir, tenant, *sub, locale),
                              os.path.join(base_output_dir, tenant, *sub),
                              os.path.join(base_output_dir, tenant, *sub, "pt")]
                if platform == "android":
                    candidates += [os.path.join(base_output_dir, tenant, "ios", "screenshots", "iphone", locale),
                                   os.path.join(base_output_dir, tenant, "ios", "screenshots", "iphone"),
                                   os.path.join(base_output_dir, tenant, "ios", "screenshots", "iphone", "pt")]
                raw_screenshots_dir = next((d for d in candidates if glob.glob(f"{d}/*.png")), None)

                if not raw_screenshots_dir:
                    print(f"  ⚠️ Raw screenshots folder not found ({locale}): {candidates[0]}")
                    continue

                # Tenants migrated to the eight-slot spec declare eight captions and are
                # driven by SLIDE_SOURCES, which names the capture and region per slot.
                # Legacy four-caption tenants keep the old positional mapping untouched
                # until they are migrated one at a time.
                use_slide_sources = len(slides) == len(SLIDE_SOURCES)

                for store_locale in store_locales:
                    screenshots_dir = os.path.join(ALEFLY_STORE_ASSETS, tenant, store_locale, "screenshots")
                    output_dir = os.path.join(screenshots_dir, platform)
                    os.makedirs(output_dir, exist_ok=True)

                    for i, (headline, subheadline) in enumerate(slides):
                        if use_slide_sources:
                            candidate = os.path.join(raw_screenshots_dir, SLIDE_SOURCES[i]["file"])
                            if candidate and os.path.exists(candidate):
                                input_file = candidate
                            elif i < len(LEGACY_SLIDE_FILES) and os.path.exists(os.path.join(raw_screenshots_dir, LEGACY_SLIDE_FILES[i])):
                                input_file = os.path.join(raw_screenshots_dir, LEGACY_SLIDE_FILES[i])
                            else:
                                avail = sorted(glob.glob(f"{raw_screenshots_dir}/*.png"))
                                input_file = avail[min(i, len(avail)-1)] if avail else None
                        elif i < len(LEGACY_SLIDE_FILES) and os.path.exists(os.path.join(raw_screenshots_dir, LEGACY_SLIDE_FILES[i])):
                            input_file = os.path.join(raw_screenshots_dir, LEGACY_SLIDE_FILES[i])
                        else:
                            # Fallback to available files in directory
                            avail = sorted(glob.glob(f"{raw_screenshots_dir}/*.png"))
                            input_file = avail[min(i, len(avail)-1)] if avail else None

                        output_file = os.path.join(output_dir, f"slide_{i+1}.png")

                        if not input_file or not os.path.exists(input_file):
                            failures.append(f"{tenant}/{locale}/{platform} slide {i + 1}: raw capture missing ({input_file})")
                            print(f"    ⚠️ Input screenshot not found ({locale}): {input_file}")
                            continue
                        try:
                            process_screenshot(tenant, i, headline, subheadline, input_file, output_file,
                                               platform=platform, use_slide_sources=use_slide_sources,
                                               locale=locale)
                        except Exception as exc:  # keep rendering the rest, report everything at the end
                            failures.append(f"{tenant}/{locale}/{platform} slide {i + 1}: {exc!r}")
                            print(f"    ❌ Failed to render slide {i + 1} ({locale}): {exc!r}")

    if failures:
        print("\n❌ Missing or failed slides:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
    print("\n🎉 All screenshots generated into store-assets for the requested platforms.")

def _selfcheck():
    """Assert-based check over every real seed (no pytest in this repo): headline,
    subhead and highlight all clear MIN_TEXT_CONTRAST against the text band, and the
    highlight is genuinely coloured whenever the tenant has a saturated brand colour."""
    checked = 0
    for path in sorted(glob.glob(os.path.join(ALEFLY_SEEDS, "*.json"))):
        tenant = os.path.basename(path)[:-5]
        palette = derive_palette(tenant)
        if not palette:
            continue
        band = palette["band"]
        for role in ("headline_color", "subhead_color", "highlight_color"):
            ratio = _contrast_ratio(palette[role], band)
            assert ratio >= MIN_TEXT_CONTRAST, f"{tenant}: {role}={palette[role]} vs band={band} contrast={ratio:.2f}"
        with open(path, encoding="utf-8") as fh:
            visual = json.load(fh).get("visual") or {}
        brand = (_hex_to_rgb(visual.get("primaryColor")), _hex_to_rgb(visual.get("accentColor")))
        if max(_saturation(c) for c in brand) >= MIN_HIGHLIGHT_SATURATION:
            assert _saturation(palette["highlight_color"]) >= MIN_HIGHLIGHT_SATURATION, \
                f"{tenant}: highlight {palette['highlight_color']} lost the brand colour"
        checked += 1
    assert checked, "no seeds found"
    print(f"✅ selfcheck ok: {checked} tenants, every text role >= {MIN_TEXT_CONTRAST}:1 on its band")

    # resolve_store_locales: backward compat (no override or string) + new list form
    assert resolve_store_locales("flamengo", "pt") == ["pt-BR"]  # no override, falls back to the global default
    assert resolve_store_locales("bocajuniors", "es") == ["es-419"]  # existing string override becomes a 1-item list
    TENANT_STORE_LOCALE_OVERRIDES["_selfcheck_multi"] = {"en": ["en-US", "en-GB", "en-PH"]}
    assert resolve_store_locales("_selfcheck_multi", "en") == ["en-US", "en-GB", "en-PH"]
    del TENANT_STORE_LOCALE_OVERRIDES["_selfcheck_multi"]
    print("✅ resolve_store_locales: backward compat + multi-country list ok")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default=None, help="Tenant específico para gerar (ex: flamengo, vasco, worldcup, etc)")
    parser.add_argument("--platform", choices=["android", "ios", "ipad", "all"], default="all")
    parser.add_argument("--locale", default=None, help="Locale específico (pt/es/ca) para tenants multi-idioma; default processa todos os locales do tenant")
    parser.add_argument("--selfcheck", action="store_true", help="Assert text contrast on every tenant seed and exit")
    args = parser.parse_args()

    if args.selfcheck:
        _selfcheck()
    else:
        run_factory(target_tenant=args.tenant, target_platform=args.platform, target_locale=args.locale)
