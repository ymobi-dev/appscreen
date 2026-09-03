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

# Caminhos base
ALEFLY_REPO_ROOT = os.environ.get("ALEFLY_REPO_ROOT", "/Users/yuripacheco/Projetos/alefly")
ALEFLY_STORE_ASSETS = os.path.join(ALEFLY_REPO_ROOT, "store-assets")
APPSCREEN_ROOT = "/Users/yuripacheco/Projetos/appscreen"
FONTS_DIR = os.path.join(APPSCREEN_ROOT, "apps", "biblia365", "fonts")

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


# WCAG's floor for large/bold text (headline/highlight qualify by size; subhead at 50pt
# bold on this canvas reads as large too — see the 2026-09-03 contrast audit).
MIN_TEXT_CONTRAST = 3.0


def _worst_contrast(rgb, gradient_stops):
    """Contrast of `rgb` against whichever gradient stop it clashes with hardest.

    The canvas is a 3-stop vertical gradient, not one flat colour — a text colour
    picked against the *middle* stop (or a single accent luminance sample, the old
    approach) can still fail against the 65%-shade stop. This checks every stop, so
    the decision holds across the whole banner, not just the point someone eyeballed.
    """
    return min(_contrast_ratio(rgb, stop) for stop in gradient_stops)


def _min_scrim_alpha(gradient_stops, target_contrast, step=0.05):
    """Smallest black-overlay alpha (0-1) that gets white text to `target_contrast`
    against the worst gradient stop.

    Solved numerically instead of algebraically: relative luminance gamma-expands each
    channel before summing, so scaling a channel by (1 - alpha) does not scale luminance
    linearly. A small stepped search is simpler and more obviously correct than inverting
    that curve, and it only runs once per tenant at palette-derivation time.
    """
    alpha = 0.0
    while alpha < 1.0:
        darkened = [_shade(stop, 1 - alpha) for stop in gradient_stops]
        if _worst_contrast((255, 255, 255), darkened) >= target_contrast:
            return alpha
        alpha += step
    return 1.0


def _lighten_toward_white(rgb, factor):
    return tuple(int(c + (255 - c) * factor) for c in rgb)


def _lighten_until_readable(rgb, background_stops, target_contrast, step=0.05):
    """Tints `rgb` toward white just enough to clear `target_contrast`, instead of
    discarding it for a flat fallback colour.

    Exists because the scrim darkens the whole canvas toward black, which only ever
    helps colours that were already light — a dark brand primary (cruzeiro's navy blue,
    for instance) gets WORSE contrast as the canvas darkens under it, not better, so
    picking between "primary as-is" and "give up, use white" threw away the brand
    colour on every dark-primary tenant. Blending toward white keeps the hue (still
    reads as "blue", not grey) while guaranteeing the same floor every other role gets.
    """
    factor = 0.0
    while factor < 1.0:
        candidate = _lighten_toward_white(rgb, factor)
        if _worst_contrast(candidate, background_stops) >= target_contrast:
            return candidate
        factor += step
    return (255, 255, 255)


def derive_palette(tenant_key):
    """Screenshot palette derived from the tenant seed, never hand-picked.

    The app paints its own background with `primaryColor`, so reusing it on the canvas
    made the phone and the crops melt into the backdrop. `accentColor` is the other
    brand colour and is what the canvas uses instead — gold behind Real Madrid's blue
    app, black behind Flamengo's red one — which keeps every tenant on brand while
    guaranteeing the asset separates from the content.

    Every text role below is chosen by measuring real WCAG contrast against the actual
    rendered gradient (all 3 stops, not a single accent sample) and falling back to a
    role that is proven safe when a brand colour would not read — fully automatic from
    the tenant's own primary/accent pair, no per-tenant hardcoding. `_draw_line_centered`
    additionally strokes every glyph in the opposite luminance as a second safety net
    for whatever this contrast math still misjudges.

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

    gradient_stops = [_shade(accent, 0.82), accent, _shade(accent, 0.65)]
    WHITE, NEAR_BLACK = (255, 255, 255), (12, 20, 32)

    # A medium-luminance canvas (golds, mid-greens, teals) can pass the WCAG floor with
    # EITHER white or near-black text and still look weak in practice — found via visual
    # review (2026-09-03) on bible/realmadrid/worldcup/fluminense, all texture-heavy
    # golds/greens where 3-4.5:1 math didn't translate into a comfortable read. Flat
    # dark canvases (flamengo, juventus) never had this problem: white text there is
    # already well past comfortable without any help. So: only reach for the scrim when
    # plain white text doesn't clear a *comfortable* target (4.5:1, not just the 3:1
    # floor) on its own — a real dark canvas skips it entirely.
    COMFORTABLE_CONTRAST = 4.5
    needs_scrim = _worst_contrast(WHITE, gradient_stops) < COMFORTABLE_CONTRAST
    scrim_alpha = _min_scrim_alpha(gradient_stops, COMFORTABLE_CONTRAST) if needs_scrim else 0.0

    if needs_scrim:
        # Under the scrim every stop is darkened toward black by the same alpha, so white
        # is unconditionally the highest-contrast choice — no more picking between two
        # imperfect options per tenant.
        headline_color = WHITE
        subhead_color = WHITE
    else:
        # Pick whichever of the two safe headline candidates wins across the whole
        # gradient, instead of assuming "light accent -> always use the dark pair" — a
        # medium-luminance accent can have its darkest stop favour one pair and its
        # lightest stop favour the other.
        headline_color = max((WHITE, NEAR_BLACK), key=lambda c: _worst_contrast(c, gradient_stops))
        subhead_color = headline_color

    # Highlight word prefers `primary` for brand pop (e.g. Real Madrid's blue against
    # its gold canvas). Found via audit (2026-09-03): santos has primary == accent (both
    # white) — contrast 1.0, the highlight word was literally invisible; psg (2.17),
    # manchestercity (2.47) and flamengo (2.96) were all unreadable in practice despite
    # passing a naive "different hue" glance.
    #
    # A scrim darkens the canvas toward black, which only ever helps colours that were
    # already light — a dark primary (cruzeiro's navy) gets WORSE, not better, so under
    # a scrim this tints primary toward white until it clears the same comfortable floor
    # the headline gets, instead of the binary "as-is or give up to plain white" choice
    # used when there is no scrim. Cruzeiro still reads as blue, just a lighter one.
    # Highlight keeps the plain WCAG floor even under a scrim, not the headline's
    # higher comfortable bar — cruzeiro's navy blue and a mid-grey scrim backdrop are
    # near isoluminant (WCAG contrast only weighs luminance, not hue), so demanding
    # 4.5:1 here forced the lightening loop past pale-blue all the way to indistinguishable
    # -from-white before it would ever pass. 3:1 keeps a visible blue tint; text below it
    # falls through to the headline colour instead of "technically blue but reads as white".
    effective_stops = [_shade(s, 1 - scrim_alpha) for s in gradient_stops] if needs_scrim else gradient_stops
    if _worst_contrast(primary, effective_stops) >= MIN_TEXT_CONTRAST:
        highlight_color = primary
    elif needs_scrim:
        highlight_color = _lighten_until_readable(primary, effective_stops, MIN_TEXT_CONTRAST)
    else:
        highlight_color = headline_color

    return {
        "colors": gradient_stops,
        "headline_color": headline_color,
        "subhead_color": subhead_color,
        "highlight_color": highlight_color,
        "scrim_alpha": scrim_alpha,
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

# Locales written right-to-left. Montserrat carries no Arabic glyphs at all — an "ar"
# slide rendered with it comes out as a row of .notdef boxes, which measures a normal
# width so only looking at the image catches it.
RTL_LOCALES = {"ar"}
ARABIC_FONTS = ("/System/Library/Fonts/SFArabic.ttf", "/System/Library/Fonts/GeezaPro.ttc")

# Same .notdef-box failure as Arabic: Montserrat carries no CJK glyphs.
CJK_LOCALES = {"zh"}
CJK_FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def get_fonts(platform="ios", locale="pt"):
    # Subhead sized/weighted for legibility at real Play Store thumbnail scale (screenshots
    # render ~4x smaller there than this canvas), not just contrast on this full-size
    # render — audit (2026-09-03) found the previous 50pt regular weight unreadable once
    # scaled down, independent of colour/stroke. Bumped size (50->64, ~28%) and swapped
    # regular for semibold: a heavier stroke-per-glyph survives downscaling and
    # compression far better than a thin regular face does.
    if locale in RTL_LOCALES:
        arabic = next((f for f in ARABIC_FONTS if os.path.exists(f)), None)
        if arabic:
            size_h, size_s = (148, 88) if platform == "ipad" else (104, 64)
            return ImageFont.truetype(arabic, size_h), ImageFont.truetype(arabic, size_s)
    if locale in CJK_LOCALES and os.path.exists(CJK_FONT):
        size_h, size_s = (148, 88) if platform == "ipad" else (104, 64)
        # index 2/0 = W6 (bold) / W3 (regular) faces inside the .ttc. CJK strokes are
        # already heavier at a given point size than Latin type, so W3 (regular) still
        # reads fine here even though Latin subhead moved to a semibold weight above.
        return (ImageFont.truetype(CJK_FONT, size_h, index=2),
                ImageFont.truetype(CJK_FONT, size_s, index=0))
    f_bold = os.path.join(FONTS_DIR, "montserrat_bold.ttf")
    f_semibold = os.path.join(FONTS_DIR, "montserrat_semibold.ttf")
    if not os.path.exists(f_bold): f_bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    if not os.path.exists(f_semibold): f_semibold = f_bold
    if platform == "ipad":
        return ImageFont.truetype(f_bold, 148), ImageFont.truetype(f_semibold, 88)
    return ImageFont.truetype(f_bold, 104), ImageFont.truetype(f_semibold, 64)

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

def wrap_text(text, draw, font, max_width):
    raw_tokens = re.findall(r'\*\*[^*]+\*\*|\S+', text)
    lines = []
    current = []
    current_w = 0
    prev_visible = ''
    space_w = draw.textlength(' ', font=font)
    for tok in raw_tokens:
        visible = tok.replace('**', '')
        tok_w = draw.textlength(visible, font=font)
        # No gap between two adjacent bare CJK characters — real spacing would look
        # like letter-spaced Latin type, which Chinese headlines don't use.
        gap = 0 if _is_cjk_char(prev_visible) and _is_cjk_char(visible) else space_w
        added = tok_w + (gap if current else 0)
        if current and current_w + added > max_width:
            lines.append(' '.join(current))
            current = [tok]
            current_w = tok_w
        else:
            current.append(tok)
            current_w += added
        prev_visible = visible
    if current:
        lines.append(' '.join(current))
    return lines

def _stroke_color_for(rgb):
    # Opposite-luminance outline so the glyph edge holds up regardless of what the
    # gradient is doing directly behind it — a fixed offset shadow only darkens, which
    # does nothing when the text is already the dark side of the pair (see the subhead
    # contrast audit, 2026-09-03: 13/26 tenants dropped below WCAG 3:1 at some point in
    # the gradient because the shadow never lightened anything).
    return (0, 0, 0) if _relative_luminance(rgb) > 0.5 else (255, 255, 255)


def _draw_line_centered(draw, line, font, y, width, style, highlight_color, rtl=False, stroke_width=0):
    if rtl:
        # Drawn in one call so Raqm can shape and reorder the run. The per-word cursor
        # below advances left-to-right, which lays an Arabic line out backwards; the
        # highlight colour is the price of correct text, and it is the cheaper loss.
        visible = line.replace('**', '')
        x = (width - draw.textlength(visible, font=font)) // 2
        draw.text((x, y), visible, fill=style.color, font=font,
                   stroke_width=stroke_width, stroke_fill=_stroke_color_for(style.color))
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
        w = draw.textlength(visible, font=font)
        gap = 0 if i > 0 and _is_cjk_char(prev_visible) and _is_cjk_char(visible) else (space_w if i > 0 else 0)
        gaps.append(gap)
        segments.append((visible, is_hl, w))
        total_w += w + gap
        prev_visible = visible

    cur_x = (width - total_w) // 2
    for (visible, is_hl, w), gap in zip(segments, gaps):
        cur_x += gap
        col = highlight_color if is_hl else style.color
        # PIL's native stroke draws the outline centred on the glyph path in every
        # direction, unlike the old fixed-offset "shadow" (which only ever darkened
        # toward bottom-right and did nothing on a background lighter than the text).
        draw.text((cur_x, y), visible, fill=col, font=font,
                   stroke_width=stroke_width, stroke_fill=_stroke_color_for(col))
        cur_x += w

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

def _draw_text_scrim(canvas, alpha):
    """Darkens the whole canvas so white text always has a guaranteed-dark surface to
    sit on, regardless of the gradient colour underneath — a bounded card behind just
    the text read as a floating sticker instead of part of the design, so this covers
    edge to edge like the gradient itself does.

    Composited as its own RGBA layer rather than drawn straight onto the RGB canvas —
    `ImageDraw` on an RGB image ignores alpha entirely and paints the fill opaque, which
    would hide the gradient instead of just darkening it.
    """
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, int(255 * alpha)))
    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB"), (0, 0))


def draw_text_block(canvas, headline, subheadline, f_h, f_s, highlight_color, platform="ios",
                    headline_style=None, subhead_style=None, locale="pt", scrim_alpha=0.0):
    w, h = canvas.size
    text_w = w - (300 if platform == "ipad" else 220)
    top_margin = 190 if platform == "ipad" else TEXT_TOP_MARGIN
    headline_style = headline_style or HEADLINE_STYLE
    subhead_style = subhead_style or SUBHEAD_STYLE
    draw = ImageDraw.Draw(canvas)
    rtl = locale in RTL_LOCALES
    headline = expand_bold_spans(headline)
    subheadline = expand_bold_spans(subheadline)
    h_lines = wrap_text(headline, draw, f_h, text_w)
    s_lines = wrap_text(subheadline, draw, f_s, text_w)
    h_lh = int(f_h.size * HEADLINE_LINE_HEIGHT_RATIO)
    s_lh = int(f_s.size * SUBHEAD_LINE_HEIGHT_RATIO)
    gap = int(f_h.size * HEADLINE_SUBHEAD_GAP_RATIO)
    total_text_h = (len(h_lines) * h_lh) + (len(s_lines) * s_lh) + gap

    if scrim_alpha:
        _draw_text_scrim(canvas, scrim_alpha)
        draw = ImageDraw.Draw(canvas)  # canvas pixels changed under the old ImageDraw's cache

    # Stroke width scales with font size so it reads the same relative weight on
    # headline vs subhead instead of a fixed px value looking chunky on the smaller face.
    h_stroke = max(2, f_h.size // 26)
    s_stroke = max(2, f_s.size // 20)

    curr_y = top_margin
    for line in h_lines:
        _draw_line_centered(draw, line, f_h, curr_y, w, headline_style, highlight_color, rtl, stroke_width=h_stroke)
        curr_y += h_lh
    curr_y += gap
    for line in s_lines:
        _draw_line_centered(draw, line, f_s, curr_y, w, subhead_style, highlight_color, rtl, stroke_width=s_stroke)
        curr_y += s_lh

    return total_text_h

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
    if palette:
        # Already the intended canvas colour — darkening it here would turn Real Madrid's
        # gold into brown. darken_color() only exists to tame the legacy hardcoded palettes,
        # which reused the in-app background and needed dimming to sit behind white text.
        draw_brand_background(canvas, palette["colors"])
    else:
        draw_brand_background(canvas, [darken_color(c) for c in config["colors"]])

    f_h, f_s = get_fonts(platform=platform, locale=locale)
    if palette:
        # Native PIL stroke (drawn in _draw_line_centered) keeps every one of these
        # readable regardless of canvas luminance now, so there is no dark/light branch
        # to pick here anymore.
        headline_style = TextStyle(color=palette["headline_color"])
        subhead_style = TextStyle(color=palette["subhead_color"])
        highlight = palette["highlight_color"]
    else:
        headline_style = subhead_style = None
        highlight = config["highlight_color"]
    scrim_alpha = palette.get("scrim_alpha", 0.0) if palette else 0.0
    total_text_h = draw_text_block(canvas, headline, subheadline, f_h, f_s, highlight, platform=platform,
                                   headline_style=headline_style, subhead_style=subhead_style, locale=locale,
                                   scrim_alpha=scrim_alpha)

    top_margin = 190 if platform == "ipad" else TEXT_TOP_MARGIN
    device_y = top_margin + total_text_h + MIN_TEXT_DEVICE_GAP

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

            base_output_dir = os.path.join(ALEFLY_REPO_ROOT, "output/store-assets")

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
                                           platform=platform, use_slide_sources=use_slide_sources,
                                           locale=locale)
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
