import os
import sys
import glob
import json
import math
import re
import argparse
import colorsys
import itertools
import shutil
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
# Ephemeral, gitignored, pre-framed Maestro output -- named "raw-captures", not
# "store-assets", so it's never confused with ALEFLY_STORE_ASSETS (committed,
# store-ready content). Written by alefly's capture-multilocale-screenshots.sh,
# consumed here as this factory's own raw material.
ALEFLY_RAW_CAPTURES = os.path.join(ALEFLY_REPO_ROOT, "output/raw-captures")
APPSCREEN_ROOT = "/Users/yuripacheco/Projetos/appscreen"

# TENANTS ATIVOS NAS LOJAS E SUAS CONFIGURAÇÕES DE DESIGN
TENANT_CONFIGS = {
    "cricketindia": {
        "name": "Indian Cricket Quiz",
        "colors": [(7, 26, 62), (13, 46, 107), (5, 19, 43)],
        "highlight_color": (255, 153, 51),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Críquete**", "O quiz definitivo sobre jogadores, títulos, recordes e história da Índia"),
                ("Perguntas sobre **craques, Copas e recordes**", "De Gavaskar e Tendulkar a Kohli, Rohit e Bumrah"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais de críquete"),
                ("Seu placar na hora, **lance a lance**", "Pontuação, percentual de acerto e evolução a cada rodada"),
                ("Quem sabe mais **lidera a tabela**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your Indian **cricket knowledge**", "The ultimate trivia on players, trophies, records and history"),
                ("Questions on **stars, World Cups and records**", "From Gavaskar and Tendulkar to Kohli, Rohit and Bumrah"),
                ("Challenge a friend **by link**", "Send the match and see who knows cricket best"),
                ("Your score, **instantly, ball by ball**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "hi": [
                ("भारतीय **क्रिकेट ज्ञान** को परखें", "खिलाड़ियों, ट्रॉफियों, रिकॉर्ड और इतिहास पर अंतिम क्विज़"),
                ("**सितारों, वर्ल्ड कप और रिकॉर्ड** पर सवाल", "गावस्कर और तेंदुलकर से लेकर कोहली, रोहित और बुमराह तक"),
                ("दोस्तों को **लिंक से चुनौती** दें", "मैच भेजें और देखें कि क्रिकेट को कौन बेहतर जानता है"),
                ("आपका स्कोर तुरंत, **गेंद दर गेंद**", "प्रत्येक राउंड में अंक, सटीकता और प्रगति"),
                ("लीडरबोर्ड के **शीर्ष पर पहुंचें**", "आपके और आपके दोस्तों के बीच रीयल-टाइम रैंकिंग"),
                ("गलत उत्तर? जवाब **व्याख्या के साथ**", "हर सवाल सही उत्तर और उसका कारण दिखाता है"),
                ("अटक गए? **संकेत लें**", "जब भी जरूरत हो, प्रति प्रश्न एक सहायता"),
                ("रोज़ खेलें और **स्ट्रीक बनाए रखें**", "दैनिक स्ट्रीक, रैंकिंग और मैचों का इतिहास")
            ]
        }
    },
    "cars": {
        "name": "Car Quiz",
        "colors": [(11, 11, 11), (35, 35, 38), (1, 1, 1)],
        "highlight_color": (232, 64, 42),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **sobre Carros**", "O quiz definitivo sobre marcas, modelos, motores e supercarros"),
                ("Perguntas sobre **marcas, modelos e potência**", "Do JDM aos clássicos e hipercarros modernos"),
                ("Desafie um amigo **por link**", "Envie a disputa e veja quem manja mais de carros"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada desafio"),
                ("Quem sabe mais **assume a liderança**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your automotive **knowledge & skills**", "The ultimate trivia on car brands, models, engines and supercars"),
                ("Questions on **brands, specs and power**", "From JDM legends to classics and modern hypercars"),
                ("Challenge a friend **by link**", "Send the match and see who knows cars best"),
                ("Your score, **instantly, round after round**", "Points, accuracy and progress in every challenge"),
                ("Take the **top spot**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **sobre Autos**", "El quiz definitivo sobre marcas, modelos, motores y superdeportivos"),
                ("Preguntas sobre **marcas, modelos y potencia**", "Del JDM a los clásicos y los hiperdeportivos modernos"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de autos"),
                ("Tu marcador al instante, **ronda a ronda**", "Puntuación, porcentaje de acierto y evolución en cada desafío"),
                ("Quien sabe más **toma el liderato**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "it": [
                ("Metti alla prova le tue conoscenze **sulle Auto**", "Il quiz definitivo su marchi, modelli, motori e supercar"),
                ("Domande su **marchi, modelli e potenza**", "Dal JDM ai classici e alle hypercar moderne"),
                ("Sfida un amico **tramite link**", "Invia la sfida e scopri chi ne sa di più di auto"),
                ("Il tuo punteggio all'istante, **round dopo round**", "Punti, precisione e progressi in ogni sfida"),
                ("Chi ne sa di più **conquista la vetta**", "Classifica in tempo real tra te e i tuoi amici"),
                ("Hai sbagliato? La risposta è **spiegata**", "Ogni domanda mostra la risposta corretta e il motivo"),
                ("Bloccato? **Usa un indizio**", "Un aiuto per domanda, quando ne hai bisogno"),
                ("Torna ogni giorno e **mantieni la serie**", "Serie giornaliera, classifica e cronologia delle sfide")
            ],
            "de": [
                ("Teste dein Wissen **über Autos**", "Das ultimative Quiz über Marken, Modelle, Motoren und Supercars"),
                ("Fragen zu **Marken, Modellen und Leistung**", "Von JDM-Klassikern bis zu modernen Hypercars"),
                ("Fordere einen Freund **per Link heraus**", "Teile das Duell und finde heraus, wer Autos am besten kennt"),
                ("Dein Punktestand sofort, **Runde für Runde**", "Punkte, Trefferquote und Entwicklung bei jeder Herausforderung"),
                ("Wer mehr weiß, **übernimmt die Spitze**", "Echtzeit-Rangliste zwischen dir und deinen Freunden"),
                ("Falsch geantwortet? Die Erklärung **folgt sofort**", "Jede Frage zeigt die richtige Antwort und den Grund"),
                ("Kommst du nicht weiter? **Nimm einen Tipp**", "Eine Hilfe pro Frage, wann immer du sie brauchst"),
                ("Komm täglich wieder und **halte die Serie**", "Tägliche Serie, Rangliste und Spielverlauf")
            ],
            "fr": [
                ("Testez vos connaissances **sur les Voitures**", "Le quiz ultime sur les marques, modèles, moteurs et supercars"),
                ("Des questions sur **marques, modèles et puissance**", "Du JDM aux classiques et aux hypercars modernes"),
                ("Défiez un ami **par lien**", "Envoyez le défi et voyez qui s'y connaît le plus en voitures"),
                ("Votre score à l'instant, **manche après manche**", "Points, taux de réussite et progression à chaque défi"),
                ("Celui qui en sait le plus **prend la tête**", "Classement en temps réel entre vous et vos amis"),
                ("Raté ? La réponse est **expliquée**", "Chaque question montre la bonne réponse et le pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Un coup de pouce par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ]
        }
    },
    "worldhistory": {
        "name": "World History Quiz",
        "colors": [(28, 19, 13), (62, 42, 30), (14, 9, 7)],
        "highlight_color": (184, 115, 46),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de História**", "O quiz definitivo sobre civilizações antigas, impérios e guerras"),
                ("Perguntas sobre **impérios, revoluções e guerras**", "Da Antiguidade e Idade Média ao século XX"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais de história"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada desafio"),
                ("Quem sabe mais **lidera o ranking**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your knowledge **of History**", "A quiz on ancient civilizations, empires and wars"),
                ("Questions on **empires, revolutions and wars**", "From Antiquity and the Middle Ages to the 20th century"),
                ("Challenge a friend **by link**", "Send the match and see who knows more history"),
                ("Your score instantly, **round by round**", "Score, accuracy rate and progress with every challenge"),
                ("Know more? **Lead the leaderboard**", "Real-time leaderboard between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right answer and why"),
                ("Stuck? **Use a hint**", "One hint per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, leaderboard and history of your rounds")
            ],
            "es": [
                ("Desafía tus conocimientos **de Historia**", "Quiz sobre civilizaciones antiguas, imperios y guerras"),
                ("Preguntas sobre **imperios, revoluciones y guerras**", "De la Antigüedad y la Edad Media al siglo XX"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de historia"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada reto"),
                ("Quien sabe más **lidera la clasificación**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "worldfood": {
        "name": "World Food Quiz",
        "colors": [(102, 42, 33), (140, 58, 46), (86, 36, 28)],
        "highlight_color": (255, 107, 74),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Culinária**", "O quiz definitivo sobre pratos, ingredientes e gastronomia mundial"),
                ("Perguntas sobre **pratos típicos e temperos**", "Sabores e tradições de todos os continentes"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem manja mais de gastronomia"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada desafio"),
                ("Quem sabe mais **assume o topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **culinary knowledge**", "The ultimate quiz on dishes, ingredients and world cuisine"),
                ("Questions on **classic dishes and spices**", "Flavors and traditions from every continent"),
                ("Challenge a friend **by link**", "Send the match and see who knows food best"),
                ("Your score, **instantly, round after round**", "Points, accuracy and progress in every challenge"),
                ("Whoever knows more **takes the lead**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **de Cocina**", "Un quiz sobre platos, ingredientes y gastronomía del mundo"),
                ("Preguntas sobre **platos típicos y especias**", "Sabores y tradiciones de todos los continentes"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de gastronomía"),
                ("Tu marcador al instante, **ronda a ronda**", "Puntuación, porcentaje de aciertos y progreso en cada desafío"),
                ("Quien sabe más **llega a lo más alto**", "Ranking en tiempo real entre tus amigos y tú"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te bloqueaste? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén la racha**", "Racha diaria, ranking e historial de tus rondas")
            ],
            "fr": [
                ("Testez vos connaissances **en gastronomie**", "Le quiz complet sur les plats, ingrédients et cuisines du monde"),
                ("Questions sur **plats typiques et épices**", "Saveurs et traditions de tous les continents"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui s'y connaît le plus en cuisine"),
                ("Votre score à l'instant, **manche après manche**", "Points, taux de réussite et progression à chaque défi"),
                ("Qui en sait le plus **prend la tête**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question montre la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos parties")
            ]
        }
    },
    "animals": {
        "name": "Animals Quiz",
        "colors": [(11, 24, 16), (27, 59, 39), (5, 10, 7)],
        "highlight_color": (224, 165, 39),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **sobre Animais**", "O quiz definitivo sobre fauna, espécies, habitats e curiosidades"),
                ("Perguntas sobre **espécies, habitats e recordes**", "Mamíferos, aves, répteis e vida marinha"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais sobre a vida selvagem"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada desafio"),
                ("Quem sabe mais **lidera o ranking**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your wildlife **knowledge**", "The ultimate trivia on species, habitats, diet and taxonomy"),
                ("Questions on **species, habitats and fauna**", "Mammals, birds, reptiles, marine life and insects"),
                ("Challenge a friend **by link**", "Send the match and see who knows world wildlife best"),
                ("Your score, **instantly, round after round**", "Points, accuracy and progress in every challenge"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **sobre Animales**", "El quiz definitivo sobre fauna, especies, hábitats y curiosidades"),
                ("Preguntas sobre **especies, hábitats y fauna**", "Mamíferos, aves, reptiles, vida marina e insectos"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más sobre vida salvaje"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada reto"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "nba": {
        "name": "NBA Quiz",
        "colors": [(16, 30, 51), (31, 58, 95), (10, 20, 32)],
        "highlight_color": (255, 122, 26),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de NBA**", "O quiz definitivo sobre jogadores, MVPs, draft e franquias da liga"),
                ("Perguntas sobre **estrelas, prêmios e draft**", "De Jordan e LeBron a Curry, Jokić e os maiores campeões"),
                ("Desafie um amigo **por link**", "Envie a rodada e veja quem sabe mais de basquete"),
                ("Seu placar na hora, **lance a lance**", "Pontuação, percentual de acerto e evolução a cada rodada"),
                ("Quem sabe mais **crava a liderança**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar no clutch time"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your basketball **IQ & knowledge**", "The ultimate trivia on players, MVPs, draft and NBA history"),
                ("Questions on **superstars, arenas and draft**", "From Jordan and LeBron to Curry, Jokić and modern legends"),
                ("Challenge a friend **by link**", "Send the match and see who knows hoops best"),
                ("Your score, **instantly, shot by shot**", "Points, shooting accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right answer and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it in crunch time"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **de NBA**", "El quiz definitivo sobre jugadores, MVPs, draft y franquicias"),
                ("Preguntas sobre **estrellas, pabellones y draft**", "De Jordan y LeBron a Curry, Jokić y los grandes campeones"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de basquetbol"),
                ("Tu marcador al instante, **jugada a jugada**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "f1": {
        "name": "F1 Quiz",
        "colors": [(16, 21, 28), (27, 36, 48), (11, 15, 20)],
        "highlight_color": (242, 169, 0),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Fórmula 1**", "O quiz definitivo sobre pilotos, campeões, circuitos e história"),
                ("Perguntas sobre **pilotos, recordes e GPs**", "De Senna e Fangio a Hamilton, Verstappen e os grandes circuitos"),
                ("Desafie um amigo **por link**", "Envie a corrida e veja quem sabe mais de Fórmula 1"),
                ("Seu placar na hora, **volta a volta**", "Pontuação, percentual de acerto e evolução a cada rodada"),
                ("Quem sabe mais **fica na pole**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar no grid"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Formula 1** knowledge", "The ultimate trivia on drivers, champions, tracks and Grand Prix history"),
                ("Questions on **drivers, records and tracks**", "From Senna and Fangio to Hamilton, Verstappen and iconic circuits"),
                ("Challenge a friend **by link**", "Send the race and see who knows Formula 1 best"),
                ("Your score, **instantly, lap after lap**", "Points, accuracy and progress in every round"),
                ("Claim the **pole position**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it on the grid"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and race history")
            ],
            "es": [
                ("Desafía tus conocimientos **de Fórmula 1**", "El quiz definitivo sobre pilotos, campeones, circuitos e historia"),
                ("Preguntas sobre **pilotos, récords y grandes premios**", "De Senna y Fangio a Hamilton, Verstappen y los grandes trazados"),
                ("Desafía a un amigo **por enlace**", "Envía la carrera y descubre quién sabe más de Fórmula 1"),
                ("Tu marcador al instante, **vuelta a vuelta**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **se lleva la pole**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites en la parrilla"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "it": [
                ("Metti alla prova le tue conoscenze **sulla Formula 1**", "Il quiz definitivo su piloti, campioni, circuiti e storia"),
                ("Domande su **piloti, record e Gran Premi**", "Da Senna e Fangio a Hamilton, Verstappen e le piste storiche"),
                ("Sfida un amico **tramite link**", "Invia la gara e scopri chi ne sa di più di Formula 1"),
                ("Il tuo punteggio all'istante, **giro dopo giro**", "Punti, precisione e progressi in ogni manche"),
                ("Chi ne sa di più **conquista la pole**", "Classifica in tempo reale tra te e i tuoi amici"),
                ("Hai sbagliato? La risposta è **spiegata**", "Ogni domanda mostra la risposta corretta e il motivo"),
                ("Bloccato? **Usa un indizio**", "Un aiuto per domanda, quando ne hai bisogno sulla griglia"),
                ("Torna ogni giorno e **mantieni la serie**", "Serie giornaliera, classifica e cronologia delle gare")
            ],
            "de": [
                ("Teste dein Wissen **über die Formel 1**", "Das ultimative Quiz über Fahrer, Weltmeister, Strecken und Rennsport-Geschichte"),
                ("Fragen zu **Fahrern, Rekorden und Grand Prix**", "Von Senna und Fangio bis Hamilton, Verstappen und Traditionskursen"),
                ("Fordere einen Freund **per Link heraus**", "Teile das Rennen und finde heraus, wer die Formel 1 am besten kennt"),
                ("Dein Punktestand sofort, **Runde für Runde**", "Punkte, Trefferquote und Leistungssteigerung in jedem Match"),
                ("Wer am meisten weiß, **holt die Pole Position**", "Echtzeit-Rangliste zwischen dir und deinen Freunden"),
                ("Falsch geantwortet? Die Lösung wird **erklärt**", "Jede Frage zeigt die richtige Antwort und die Hintergründe"),
                ("Kommst du nicht weiter? **Nutze einen Tipp**", "Ein Joker pro Frage, wann immer du ihn im Startfeld brauchst"),
                ("Komm täglich wieder und **halte deine Serie**", "Tägliche Serie, Rangliste und Renn-Verlauf")
            ],
            "fr": [
                ("Testez vos connaissances **sur la Formule 1**", "Le quiz sur les pilotes, champions, circuits et l'histoire de la F1"),
                ("Questions sur **pilotes, records et Grands Prix**", "De Senna et Fangio à Hamilton et Verstappen, sans oublier les circuits mythiques"),
                ("Défiez un ami **par lien**", "Envoyez la course et voyez qui connaît le mieux la Formule 1"),
                ("Votre score en direct, **tour après tour**", "Points, taux de réussite et progression à chaque manche"),
                ("Qui en sait le plus **prend la pole**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et le pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin sur la grille"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ]
        }
    },
    "flamengo": {
        "name": "Quiz para Fãs do Fla",
        "colors": [(26, 0, 0), (122, 0, 0), (26, 26, 26)],
        "highlight_color": (255, 70, 70),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Flamengo**", "O quiz definitivo sobre títulos, ídolos e história rubro-negra"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Zico a Arrascaeta e ao elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Flamengo"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Flamengo** knowledge", "The ultimate quiz on titles, legends and Rubro-Negro history"),
                ("Questions on **titles, legends and classics**", "From Zico to Arrascaeta and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Flamengo best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Flamengo**", "El quiz definitivo sobre títulos, ídolos e historia rubro-negra"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Zico a Arrascaeta y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Flamengo"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "botafogo": {
        "name": "Quiz para Fãs do Botafogo",
        "colors": [(13, 11, 6), (30, 26, 16), (10, 10, 10)],
        "highlight_color": (232, 232, 232),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Botafogo**", "O quiz definitivo sobre títulos, ídolos e história alvinegra"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Garrincha a Luiz Henrique e ao elenco atual"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Botafogo"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Botafogo** knowledge", "The ultimate quiz on titles, legends and Alvinegra history"),
                ("Questions on **titles, legends and classics**", "From Garrincha to Luiz Henrique and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Botafogo best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Botafogo**", "El quiz definitivo sobre títulos, ídolos e historia alvinegra"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Garrincha a Luiz Henrique y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Botafogo"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "ar": [
                ("اختبر معلوماتك عن **بوتافوغو**", "أفضل اختبار عن الألقاب والأساطير وتاريخ الفريق الأسود والأبيض"),
                ("أسئلة عن **الألقاب والأساطير والكلاسيكيات**", "من غارينشا إلى لويز هنريكي والتشكيلة الحالية"),
                ("تحدَّ صديقًا **عبر رابط**", "أرسل الجولة واكتشف من يعرف بوتافوغو أكثر"),
                ("نتيجتك فورًا، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتقدم في كل جولة"),
                ("الأكثر معرفة **يتصدر الترتيب**", "ترتيب مباشر بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة **مشروحة**", "كل سؤال يعرض الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحًا**", "مساعدة واحدة لكل سؤال، وقتما تحتاجها"),
                ("عد كل يوم **وحافظ على تتابعك**", "تتابع يومي وترتيب وسجل لجولاتك")
            ],
            "fr": [
                ("Défiez vos connaissances sur **Botafogo**", "Le quiz ultime sur les titres, les légendes et l'histoire alvinegra"),
                ("Questions sur les **titres, légendes et classiques**", "De Garrincha à Luiz Henrique jusqu'à l'effectif actuel"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui connaît le mieux Botafogo"),
                ("Votre score à l'instant, **match après match**", "Points, pourcentage de réussite et progression à chaque manche"),
                ("Le plus fort **grimpe au sommet**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ]
        }
    },
    "fluminense": {
        "name": "Quiz para Fãs do Fluminense",
        "colors": [(13, 4, 5), (74, 14, 26), (10, 5, 5)],
        "highlight_color": (0, 168, 107),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **do Fluminense**", "O quiz definitivo sobre títulos, ídolos e história tricolor"),
                ("Perguntas sobre **títulos, ídolos e clássicos**", "De Castilho e Didi ao time campeão da Libertadores 2023"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais do Fluminense"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Fluminense** knowledge", "The ultimate trivia about titles, legends and Tricolor history"),
                ("Questions on **titles, legends and derbies**", "From Castilho and Didi to the 2023 Libertadores champions"),
                ("Challenge a friend **by link**", "Send the match and see who knows Fluminense best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Fluminense**", "El quiz definitivo sobre títulos, ídolos e historia tricolor"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Castilho y Didi al equipo campeón de la Libertadores 2023"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Fluminense"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
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
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Copa**", "O quiz definitivo sobre seleções, craques e história do futebol mundial"),
                ("Perguntas sobre **craques, seleções e finais**", "De Garrincha e Pelé a Mbappé e o futebol de hoje"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem sabe mais de futebol mundial"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **World Cup** knowledge", "The ultimate trivia on national teams, stars and world football history"),
                ("Questions on **stars, teams and finals**", "From Garrincha and Pelé to Mbappé and football today"),
                ("Challenge a friend **by link**", "Send the match and see who knows more about world football"),
                ("Your score, **round after round**", "Points, accuracy and progress in every match"),
                ("Whoever knows more **tops the board**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and history of your rounds")
            ],
            "es": [
                ("Pon a prueba tus conocimientos **del Mundial**", "El quiz sobre selecciones, cracks e historia del fútbol mundial"),
                ("Preguntas sobre **cracks, selecciones y finales**", "De Garrincha y Pelé a Mbappé y el fútbol de hoy"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de fútbol mundial"),
                ("Tu marcador al instante, **ronda a ronda**", "Puntuación, porcentaje de aciertos y evolución en cada partida"),
                ("Quien sabe más **lidera la clasificación**", "Ranking en tiempo real entre tus amigos y tú"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te bloqueaste? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, ranking e historial de tus rondas")
            ]
        }
    },
    "bible": {
        "name": "Quiz da Bíblia",
        "colors": [(8, 21, 40), (22, 46, 84), (6, 15, 30)],
        "highlight_color": (201, 149, 44),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **da Bíblia**", "O quiz definitivo sobre o Antigo e o Novo Testamento"),
                ("Perguntas sobre **personagens, livros e ensinamentos**", "De Gênesis ao Apocalipse, com contexto para aprender"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem conhece mais as Escrituras"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **Bible** knowledge", "The ultimate trivia on the Old and New Testaments"),
                ("Questions on **people, books and verses**", "From Genesis to Revelation, with context to learn"),
                ("Challenge a friend **by link**", "Send the match and see who knows Scripture best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Pon a prueba tu conocimiento **de la Biblia**", "El quiz definitivo sobre el Antiguo y el Nuevo Testamento"),
                ("Preguntas sobre **personajes, libros y versículos**", "De Génesis a Apocalipsis, con contexto para aprender"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién conoce más las Escrituras"),
                ("Tu puntaje al instante, **partida a partida**", "Puntos, precisión y progreso en cada ronda"),
                ("El que sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Atascado? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de partidas")
            ]
        }
    },
    "emoji": {
        "name": "Quiz de Emoji",
        "colors": [(35, 18, 53), (61, 31, 92), (24, 12, 36)],
        "highlight_color": (255, 201, 51),
        "slides_by_locale": {
            "pt": [
                ("Decifre o significado **dos emojis**", "O quiz definitivo com perguntas visuais, lógicas e divertidas"),
                ("Desafios de **lógica, emoções e bandeiras**", "De significados clássicos a charadas visuais surpreendentes"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem decifra mais emojis"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem decifra mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra o significado oficial e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Decode the meaning **of emojis**", "The ultimate quiz with visual, logic and fun trivia"),
                ("Challenges on **logic, emotions & flags**", "From classic meanings to surprising visual riddles"),
                ("Challenge a friend **by link**", "Send the match and see who decodes the most emojis"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the official meaning and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Descifra el significado **de los emojis**", "El quiz definitivo con preguntas visuales, lógicas y divertidas"),
                ("Retos de **lógica, emociones y banderas**", "De significados clásicos a acertijos visuales sorprendentes"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién descifra más emojis"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien descifra más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra el significado oficial y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "geography-world": {
        "name": "Quiz Geografia Mundial",
        "colors": [(15, 43, 31), (27, 67, 50), (10, 30, 20)],
        "highlight_color": (82, 183, 136),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Geografia**", "O quiz definitivo sobre bandeiras, capitais e países do mundo"),
                ("Perguntas sobre **bandeiras, capitais e mapas**", "De países vizinhos a nações do outro lado do planeta"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem conhece mais o mundo"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **geography knowledge**", "The ultimate quiz on world flags, capitals and countries"),
                ("Questions on **flags, capitals and maps**", "From neighboring countries to nations across the planet"),
                ("Challenge a friend **by link**", "Send the match and see who knows the world better"),
                ("Your score instantly, **round by round**", "Points, accuracy rate and progress in every match"),
                ("Whoever knows more **stays on top**", "Real-time leaderboard between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right answer and why"),
                ("Stuck? **Use a hint**", "One hint per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, leaderboard and history of your rounds")
            ],
            "es": [
                ("Pon a prueba tus conocimientos **de geografía**", "El quiz definitivo sobre banderas, capitales y países del mundo"),
                ("Preguntas sobre **banderas, capitales y mapas**", "De países vecinos a naciones al otro lado del planeta"),
                ("Reta a un amigo **por enlace**", "Envía la partida y descubre quién conoce mejor el mundo"),
                ("Tu marcador al instante, **ronda a ronda**", "Puntuación, porcentaje de aciertos y evolución en cada partida"),
                ("Quien más sabe **se queda arriba**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascaste? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén la racha**", "Racha diaria, clasificación e historial de tus rondas")
            ]
        }
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Manchester United**", "El quiz definitivo sobre títulos, leyendas e historia de los Red Devils"),
                ("Preguntas sobre **títulos, ídolos y rivalidades**", "De Cristiano Ronaldo a Bruno Fernandes y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Manchester United"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La resposta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "id": [
                ("Uji pengetahuanmu tentang **Manchester United**", "Kuis definitif tentang gelar, legenda, dan sejarah Red Devils"),
                ("Pertanyaan tentang **gelar, ikon, dan rivalitas**", "Dari Cristiano Ronaldo hingga Bruno Fernandes dan skuad saat ini"),
                ("Tantang teman **lewat tautan**", "Kirim pertandingan dan buktikan siapa yang paling tahu tentang Manchester United"),
                ("Skormu langsung muncul, **ronde demi ronde**", "Poin, akurasi, dan progres di setiap putaran"),
                ("Yang paling tahu **berada di puncak**", "Peringkat langsung antara kamu dan teman-temanmu"),
                ("Salah jawab? Jawabannya ada **penjelasannya**", "Setiap soal menampilkan jawaban yang benar beserta alasannya"),
                ("Buntu? **Gunakan petunjuk**", "Satu bantuan per soal saat kamu membutuhkannya"),
                ("Kembali tiap hari dan **jaga rentetanmu**", "Rentetan harian, peringkat, dan riwayat pertandinganmu")
            ],
            "ar": [
                ("اختبر معلوماتك عن **مانشستر يونايتد**", "الكويز الشامل عن الألقاب، أساطير الشياطين الحمر وتاريخ أولد ترافورد"),
                ("أسئلة عن **البطولات، الأساطير والكلاسيكيات**", "من كريستيانو رونالدو إلى برونو فيرنانديز والتشكيلة الحالية"),
                ("تحدَّ صديقاً **عبر الرابط**", "أرسل التحدي واكتشف من يعرف مانشستر يونايتد أكثر"),
                ("نتيجتك فوراً، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتطور في كل مباراة"),
                ("من يعرف أكثر **يتصدر الترتيب**", "ترتيب فوري بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة تأتيك **مشروحة**", "كل سؤال يوضح الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحاً**", "مساعدة واحدة لكل سؤال، متى احتجت إليها"),
                ("عد يومياً و**حافظ على سلسلتك**", "سلسلة يومية وترتيب وسجل مبارياتك")
            ],
            "zh": [
                ("测试你对**曼联**的了解程度", "关于三冠王、传奇球星与红魔历史的终极问答"),
                ("题目涵盖**冠军、传奇球星与经典对决**", "从弗格森时代、C罗到现今红魔阵容"),
                ("**通过链接**挑战好友", "发送对局链接，看看谁更懂曼联"),
                ("成绩**即时呈现，一轮接一轮**", "每轮的得分、正确率与进步一目了然"),
                ("登上**排行榜**榜首", "你与好友之间的实时排名"),
                ("答错了？答案**附带解析**", "每道题都会显示正确答案及原因"),
                ("卡住了？**使用提示**", "每题一次提示，随时可用"),
                ("每天回来，**保持连续答题**", "每日连续答题、排行榜与对局历史")
            ],
            "hi": [
                ("**मैनचेस्टर यूनाइटेड** के अपने ज्ञान को परखें", "खिताबों, दिग्गजों और रेड डेविल्स के इतिहास पर अंतिम क्विज़"),
                ("**खिताबों, दिग्गजों और प्रतिद्वंद्विता** पर प्रश्न", "क्रिस्टियानो रोनाल्डो से लेकर ब्रूनो फर्नांडीस और वर्तमान टीम तक"),
                ("एक दोस्त को **लिंक द्वारा** चुनौती दें", "मैच भेजें और देखें कि मैनचेस्टर यूनाइटेड को कौन बेहतर जानता है"),
                ("आपका स्कोर तुरंत, **राउंड दर राउंड**", "प्रत्येक राउंड में अंक, सटीकता और प्रगति"),
                ("जो सबसे ज्यादा जानता है **शीर्ष पर रहता है**", "आपके और आपके दोस्तों के बीच रीयल-टाइम रैंकिंग"),
                ("गलत उत्तर? उत्तर **स्पष्टीकरण के साथ** आता है", "प्रत्येक प्रश्न सही उत्तर और कारण दिखाता है"),
                ("अटक गए? **संकेत का उपयोग करें**", "जब भी आपको आवश्यकता हो, प्रति प्रश्न एक सहायता"),
                ("हर दिन वापस आएं और **अपनी लकीर बनाए रखें**", "दैनिक स्ट्रीक, रैंकिंग और मैचों का इतिहास")
            ],
            "ko": [
                ("**맨체스터 유나이티드** 상식을 테스트해보세요", "우승 타이틀, 레전드, 붉은 악마 역사를 다룬 최고의 퀴즈"),
                ("**우승, 레전드, 라이벌전**에 관한 문제", "크리스티아누 호날두부터 브루누 페르난드스와 현재 선수단까지"),
                ("**링크로** 친구에게 도전하세요", "매치를 공유하고 맨유를 누가 더 잘 아는지 겨뤄보세요"),
                ("**라운드마다 즉시** 확인하는 내 점수", "매 라운드 점수, 정답률, 실력 향상을 한눈에"),
                ("가장 많이 맞힌 사람이 **1위 달성**", "친구들과 실시간으로 겨루는 랭킹"),
                ("틀려도 괜찮아요, **정답 해설 제공**", "모든 문제의 정답과 상세한 이유를 확인"),
                ("막힐 땐? **힌트 사용**", "필요할 때 문제마다 제공되는 힌트 찬스"),
                ("매일 도전하고 **연속 기록을 유지하세요**", "데일리 스트릭, 랭킹, 매치 기록까지")
            ],
            "ja": [
                ("**マンチェスター・ユナイテッド**の知識を試そう", "タイトル、伝説の選手、赤い悪魔の歴史を網羅した決定版クイズ"),
                ("**タイトル、伝説、ライバル対決**に挑む", "クリスティアーノ・ロナウドからブルーノ・フェルナンデス、現役スカッドまで"),
                ("**リンクで**友達に対戦を申し込もう", "マッチを共有して、誰が一番マンUに詳しいか勝負"),
                ("**ラウンドごとに即時**スコアを表示", "各ラウンドの得点、正解率、上達をリアルタイムで確認"),
                ("最高スコアで**ランキング1位**を目指せ", "友達とリアルタイムで競い合うランキング"),
                ("間違えても安心、**解説付きで学べる**", "全問で正解と詳しい理由を表示"),
                ("困ったときは？**ヒントを活用**", "1問につき1回、必要なときに使えるアシスト"),
                ("毎日挑戦して**デイリーストリークを維持しよう**", "デイリーストリーク、ランキング、対戦履歴を記録")
            ],
            "ur": [
                ("**مانچسٹر یونائیٹڈ** کے اپنے علم کو پرکھیں", "ٹائٹلز، لیجنڈز اور ریڈ ڈیولز کی تاریخ پر حتمی کوئز"),
                ("**ٹائٹلز، لیجنڈز اور روایتی حریفوں** پر سوالات", "کرسٹیانو رونالڈو سے لے کر برونو فرنانڈس اور موجودہ اسکواڈ تک"),
                ("کسی دوست کو **لنک کے ذریعے** چیلنج کریں", "میچ شیئر کریں اور دیکھیں کہ مانچسٹر یونائیٹڈ کو کون زیادہ جانتا ہے"),
                ("آپ کا اسکور فوری طور پر، **راؤنڈ در راؤنڈ**", "ہر راؤنڈ میں پوائنٹس، درستگی اور آپ کی پیش رفت"),
                ("سب سے زیادہ جاننے والا **سب سے اوپر رہتا ہے**", "آپ اور آپ کے دوستوں کے درمیان ریئل ٹائم رینکنگ"),
                ("غلط جواب؟ جواب **وضاحت کے ساتھ** آتا ہے", "ہر سوال درست جواب اور اس کی وجہ دکھاتا ہے"),
                ("اٹک گئے؟ **اشارہ استعمال کریں**", "جب بھی آپ کو ضرورت ہو، فی سوال ایک مدد"),
                ("روزانہ واپس آئیں اور **اپنا تسلسل برقرار رکھیں**", "روزانہ کا تسلسل، رینکنگ اور میچوں کی ہسٹری")
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Manchester City**", "El quiz definitivo sobre el Triplete, leyendas e historia de los Cityzens"),
                ("Preguntas sobre **títulos, ídolos y rivalidades**", "De Agüero y De Bruyne a Haaland y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Manchester City"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La resposta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "no": [
                ("Test kunnskapen din **om Manchester City**", "Den ultimate quizen om The Treble, legender og Cityzens-historie"),
                ("Spørsmål om **titler, legender og rivaler**", "Fra Agüero og De Bruyne til Haaland og dagens tropp"),
                ("Utfordre en venn **med lenke**", "Del kampen og se hvem som kan mest om Manchester City"),
                ("Poengsummen din, **runde for runde**", "Poeng, treffsikkerhet og fremgang i hver omgang"),
                ("Den beste **når toppen**", "Direkteleaderboard mellom deg og vennene dine"),
                ("Svarte du feil? Svaret blir **forklart**", "Hvert spørsmål viser det rette svaret og hvorfor"),
                ("Står du fast? **Bruk et hint**", "Én hjelp per spørsmål, når du trenger det"),
                ("Kom tilbake daglig og **hold rekken i gang**", "Daglig streak, rangering og kamphistorikk")
            ],
            "ar": [
                ("اختبر معلوماتك **عن مانشستر سيتي**", "الكويز الشامل عن الثلاثية التاريخية، الأساطير وتاريخ السيتيزنز"),
                ("أسئلة عن **الألقاب، النجوم والكلاسيكيات**", "من أغويرو ودي بروين إلى هالاند والتشكيلة الحالية"),
                ("تحدَّ صديقك **عبر الرابط**", "أرسل المواجهة واكتشف من يعرف مانشستر سيتي أكثر"),
                ("نتيجتك فوراً، **جولة بجولة**", "النقاط، نسبة الدقة وتطور مستواك في كل مباراة"),
                ("الأكثر معرفة **في الصدارة**", "ترتيب فوري بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة تأتي **مع الشرح**", "كل سؤال يعرض الإجابة الصحيحة مع بيان السبب"),
                ("عالق؟ **استخدم تلميحاً**", "مساعدة واحدة لكل سؤال متى احتجت إليها"),
                ("عد يومياً وحافظ على **سلسلة أيامك**", "سلسلة متواصلة، ترتيب وسجل مواجهاتك")
            ],
            "zh": [
                ("测试你对**曼城**的了解程度", "关于三冠王、传奇球星与蓝月亮历史的终极问答"),
                ("题目涵盖**冠军、传奇球星与经典对决**", "从阿圭罗、德布劳内到哈兰德与现今阵容"),
                ("**通过链接**挑战好友", "发送对局链接，看看谁更懂曼城"),
                ("成绩**即时呈现，一轮接一轮**", "每轮的得分、正确率与进步一目了然"),
                ("登上**排行榜**榜首", "你与好友之间的实时排名"),
                ("答错了？答案**附带解析**", "每道题都会显示正确答案及原因"),
                ("卡住了？**使用提示**", "每题一次提示，随时可用"),
                ("每天回来，**保持连续答题**", "每日连续答题、排行榜与对局历史")
            ],
            "hi": [
                ("**मैनचेस्टर सिटी** के अपने ज्ञान को परखें", "ट्रेबल, दिग्गजों और सिटीज़न्स के इतिहास पर अंतिम क्विज़"),
                ("**खिताबों, दिग्गजों और प्रतिद्वंद्विता** पर प्रश्न", "एगुएरो और डी ब्रौने से लेकर हालैंड और वर्तमान टीम तक"),
                ("एक दोस्त को **लिंक द्वारा** चुनौती दें", "मैच भेजें और देखें कि मैनचेस्टर सिटी को कौन बेहतर जानता है"),
                ("आपका स्कोर तुरंत, **राउंड दर राउंड**", "प्रत्येक राउंड में अंक, सटीकता और प्रगति"),
                ("जो सबसे ज्यादा जानता है **शीर्ष पर रहता है**", "आपके और आपके दोस्तों के बीच रीयल-टाइम रैंकिंग"),
                ("गलत उत्तर? उत्तर **स्पष्टीकरण के साथ** आता है", "प्रत्येक प्रश्न सही उत्तर और कारण दिखाता है"),
                ("अटक गए? **संकेत का उपयोग करें**", "जब भी आपको आवश्यकता हो, प्रति प्रश्न एक सहायता"),
                ("हर दिन वापस आएं और **अपनी लकीर बनाए रखें**", "दैनिक स्ट्रीक, रैंकिंग और मैचों का इतिहास")
            ],
            "bn": [
                ("**ম্যানচেস্টার সিটি** সম্পর্কে আপনার জ্ঞান যাচাই করুন", "ট্রেবল, কিংবদন্তি এবং সিটিজেন্সদের ইতিহাস নিয়ে সেরা কুইজ"),
                ("**শিরোপা, কিংবদন্তি এবং প্রতিদ্বন্দ্বিতা** নিয়ে প্রশ্ন", "আগুয়েরো ও ডি ব্রুইনা থেকে হালান্ড ও বর্তমান দল পর্যন্ত"),
                ("**লিংকের মাধ্যমে** বন্ধুকে চ্যালেঞ্জ করুন", "ম্যাচ পাঠান এবং দেখুন কে ম্যানচেস্টার সিটি সম্পর্কে বেশি জানে"),
                ("আপনার স্কোর তাৎক্ষণিকভাবে, **রাউন্ড অনুযায়ী**", "প্রতিটি রাউন্ডে পয়েন্ট, নির্ভুলতা এবং অগ্রগতি"),
                ("যে বেশি জানে সে **শীর্ষে থাকে**", "আপনার ও বন্ধুদের মধ্যে রিয়েল-টাইম র‍্যাঙ্কিং"),
                ("ভুল উত্তর দিলেন? উত্তর **ব্যাখ্যাসহ** আসে", "প্রতিটি প্রশ্নে সঠিক উত্তর ও কারণ দেখানো হয়"),
                ("আটকে গেছেন? **একটি ইঙ্গিত ব্যবহার করুন**", "প্রয়োজনে প্রতিটি প্রশ্নের জন্য একটি সাহায্য"),
                ("প্রতিদিন ফিরে আসুন এবং **আপনার স্ট্রিক বজায় রাখুন**", "দৈনিক স্ট্রিক, র‍্যাঙ্কিং এবং ম্যাচ ইতিহাস")
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
            ],
            "en": [
                ("Test your **Juventus** knowledge", "The ultimate quiz on Scudetti, legends and Vecchia Signora history"),
                ("Questions on **titles, legends and derbies**", "From Del Piero and Buffon to Cristiano Ronaldo and Dybala"),
                ("Challenge a friend **by link**", "Send the match and see who knows Juventus best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **de la Juventus**", "El quiz definitivo sobre Scudetti, ídolos e historia de la Vecchia Signora"),
                ("Preguntas sobre **títulos, ídolos y derbis**", "De Del Piero y Buffon a Cristiano Ronaldo y Dybala"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de la Juventus"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "fr": [
                ("Défiez vos connaissances sur la **Juventus**", "Le quiz ultime sur les Scudetti, les légendes et l'histoire bianconera"),
                ("Questions sur les **titres, légendes et derbys**", "De Del Piero et Buffon à Cristiano Ronaldo et Dybala"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui connaît le mieux la Juventus"),
                ("Votre score à l'instant, **match après match**", "Points, pourcentage de réussite et progression à chaque manche"),
                ("Le plus fort **grimpe au sommet**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ],
            "ar": [
                ("اختبر معلوماتك عن **يوفنتوس**", "الكويز الشامل عن ألقاب سكوديتو، الأساطير وتاريخ السيدة العجوز"),
                ("أسئلة عن **البطولات، الأساطير والديربي**", "من ديل بييرو وبوفون إلى كريستيانو رونالدو وديبالا"),
                ("تحدَّ صديقاً **عبر الرابط**", "أرسل التحدي واكتشف من يعرف يوفنتوس أكثر"),
                ("نتيجتك فوراً، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتطور في كل مباراة"),
                ("من يعرف أكثر **يتصدر الترتيب**", "ترتيب فوري بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة تأتيك **مشروحة**", "كل سؤال يوضح الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحاً**", "مساعدة واحدة لكل سؤال، متى احتجت إليها"),
                ("عد يومياً و**حافظ على سلسلتك**", "سلسلة يومية وترتيب وسجل مبارياتك")
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
            ],
            "nl": [
                ("Test je kennis over **Corinthians**", "De ultieme quiz over de 2 wereldtitels, ongeslagen Libertadores en idolen"),
                ("Vragen over **titels, legendes en derby's**", "Van Sócrates en Rivellino tot Cássio en het huidige elftal"),
                ("Daag een vriend uit **via link**", "Stuur de wedstrijd en ontdek wie Corinthians het beste kent"),
                ("Je score **direct, wedstrijd na wedstrijd**", "Punten, nauwkeurigheid en voortgang in elke ronde"),
                ("Klim naar **de top van het klassement**", "Real-time ranglijst tussen jou en je vrienden"),
                ("Fout? Het antwoord wordt **uitgelegd**", "Elke vraag toont het juiste antwoord en waarom"),
                ("Vastgelopen? **Gebruik een hint**", "Één hulp per vraag, wanneer je het nodig hebt"),
                ("Kom dagelijks terug en **houd je reeks bij**", "Dagelijkse reeks, ranglijst en wedstrijdgeschiedenis")
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
            ],
            "da": [
                ("Test din viden om **Grêmio**", "Den ultimative quiz om VM-titlen 1983, 3 Libertadores og Tricolor-legender"),
                ("Spørgsmål om **titler, legender og derbyer**", "Fra Renato Gaúcho til Ronaldinho Gaúcho og det nuværende hold"),
                ("Udfordr en ven **via link**", "Send kampen og se, hvem der kender Grêmio bedst"),
                ("Din score **med det samme, kamp efter kamp**", "Point, nøjagtighed og fremskridt i hver runde"),
                ("Klatr til **toppen af ranglisten**", "Realtidsrangering mellem dig og dine venner"),
                ("Forkert? Svaret kommer **forklaret**", "Hvert spørgsmål viser det rigtige svar og hvorfor"),
                ("Kørt fast? **Brug et hint**", "Én hjælp per spørgsmål, når du har brug for det"),
                ("Kom tilbage dagligt og **hold din streak**", "Daglig streak, rangering og kamphistorik")
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
            ],
            "en": [
                ("Test your **Bayern** knowledge", "The ultimate quiz on Champions League, Bundesligas and Rekordmeister history"),
                ("Questions on **titles, legends and classics**", "From Beckenbauer and Gerd Müller to Lewandowski and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Bayern best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Bayern**", "El quiz definitivo sobre Champions, Bundesligas e historia del Rekordmeister"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Beckenbauer y Gerd Müller a Lewandowski y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Bayern"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto e evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "fr": [
                ("Testez vos connaissances sur **le Bayern**", "Le quiz sur la Ligue des champions, les Bundesligas et l'histoire du Rekordmeister"),
                ("Questions sur **titres, légendes et classiques**", "De Beckenbauer et Gerd Müller à Lewandowski et l'effectif actuel"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui connaît le mieux le Bayern"),
                ("Votre score en direct, **manche après manche**", "Points, taux de réussite et progression à chaque partie"),
                ("Celui qui en sait le plus **prend la tête**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et le pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Un coup de pouce par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos parties")
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
            ],
            "de": [
                ("Teste dein Wissen **über den FC Barcelona**", "Das ultimative Quiz über Titel, Legenden und Blaugrana-Geschichte"),
                ("Fragen zu **Titeln, Ikonen und Clásicos**", "Von Cruyff bis zu den heutigen Barça-Stars"),
                ("Fordere Freunde **per Link heraus**", "Teile das Spiel und finde heraus, wer Barça am besten kennt"),
                ("Dein Punktestand sofort, **Runde für Runde**", "Punkte, Genauigkeit und Fortschritt in jedem Spiel"),
                ("Wer am meisten weiß, **steht ganz oben**", "Live-Rangliste zwischen dir und deinen Freunden"),
                ("Falsch gelegen? Die Antwort wird **erklärt**", "Jede Frage zeigt die richtige Lösung und warum"),
                ("Kommst du nicht weiter? **Nutz einen Tipp**", "Ein Joker pro Frage, wann immer du ihn brauchst"),
                ("Komm täglich wieder und **halte deine Serie**", "Tägliche Serie, Bestenliste und Spielverlauf")
            ],
            "fr": [
                ("Défiez vos connaissances sur le **FC Barcelone**", "Le quiz ultime sur les titres, les légendes et l'histoire blaugrana"),
                ("Questions sur les **titres, légendes et Clásicos**", "De Cruyff aux stars actuelles du Barça"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui connaît le mieux Barcelone"),
                ("Votre score à l'instant, **match après match**", "Points, pourcentage de réussite et progression à chaque manche"),
                ("Le plus fort **grimpe au sommet**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ],
            "id": [
                ("Uji pengetahuanmu tentang **FC Barcelona**", "Kuis definitif tentang gelar, legenda, dan sejarah Blaugrana") ,
                ("Pertanyaan tentang **gelar, ikon, dan El Clásico**", "Dari Cruyff hingga bintang-bintang Barça saat ini"),
                ("Tantang teman **lewat tautan**", "Kirim pertandingan dan buktikan siapa yang paling tahu tentang Barcelona"),
                ("Skormu langsung muncul, **ronde demi ronde**", "Poin, akurasi, dan progres di setiap putaran"),
                ("Yang paling tahu **berada di puncak**", "Peringkat langsung antara kamu dan teman-temanmu"),
                ("Salah jawab? Jawabannya ada **penjelasannya**", "Setiap soal menampilkan jawaban yang benar beserta alasannya"),
                ("Buntu? **Gunakan petunjuk**", "Satu bantuan per soal saat kamu membutuhkannya"),
                ("Kembali tiap hari dan **jaga rentetanmu**", "Rentetan harian, peringkat, dan riwayat pertandinganmu")
            ],
            "nl": [
                ("Test je kennis over **FC Barcelona**", "De ultieme quiz over titels, legendes en de Blaugrana-historie"),
                ("Vragen over **titels, iconen en Clásicos**", "Van Cruyff tot de huidige Barça-sterren"),
                ("Daag een vriend uit **via een link**", "Deel de match en zie wie Barcelona het beste kent"),
                ("Je score direct in beeld, **ronde na ronde**", "Punten, nauwkeurigheid en voortgang in elk potje"),
                ("Wie het meeste weet, **staat aan de top**", "Realtime klassement tussen jou en je vrienden"),
                ("Fout geantwoord? Het antwoord wordt **uitgelegd**", "Elke vraag toont de juiste keuze en waarom"),
                ("Zit je vast? **Gebruik een hint**", "Eén hulpmiddel per vraag, wanneer je het nodig hebt"),
                ("Kom dagelijks terug en **behoud je reeks**", "Dagelijkse streak, ranglijst en wedstrijdgeschiedenis")
            ],
            "pl": [
                ("Sprawdź swoją wiedzę o **FC Barcelona**", "Ostateczny quiz o tytułach, legendach i historii Blaugrany"),
                ("Pytania o **tytuły, ikony i El Clásico**", "Od Cruyffa po współczesne gwiazdy Barçy"),
                ("Rzuć wyzwanie znajomemu **przez link**", "Wyślij mecz i sprawdź, kto wie więcej o Barcelonie"),
                ("Twój wynik na bieżąco, **runda po rundzie**", "Punkty, celność i postępy w każdym meczu"),
                ("Kto wie najwięcej, **trafia na szczyt**", "Ranking na żywo między Tobą a znajomymi"),
                ("Pomyłka? Odpowiedź ma **wyjaśnienie**", "Każde pytanie pokazuje prawidłową opcję i dlaczego"),
                ("Uknąłeś? **Użyj podpowiedzi**", "Jedna pomoc na pytanie, kiedy jej potrzebujesz"),
                ("Wracaj codziennie i **utrzymuj passę**", "Codzienna passa, ranking i historia Twoich gier")
            ],
            "ar": [
                ("اختبر معلوماتك عن **برشلونة**", "الكويز الشامل عن الألقاب، أساطير البلوغرانا وتاريخ النادي الكتالوني"),
                ("أسئلة عن **البطولات، الأساطير والكلاسيكو**", "من كرويف وميسي إلى نجوم البلوغرانا الحاليين"),
                ("تحدَّ صديقاً **عبر الرابط**", "أرسل التحدي واكتشف من يعرف برشلونة أكثر"),
                ("نتيجتك فوراً، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتطور في كل مباراة"),
                ("من يعرف أكثر **يتصدر الترتيب**", "ترتيب فوري بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة تأتيك **مشروحة**", "كل سؤال يوضح الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحاً**", "مساعدة واحدة لكل سؤال، متى احتجت إليها"),
                ("عد يومياً و**حافظ على سلسلتك**", "سلسلة يومية وترتيب وسجل مبارياتك")
            ],
            "zh": [
                ("测试你对**巴塞罗那**的了解程度", "关于六冠王、传奇球星与红蓝军团历史的终极问答"),
                ("题目涵盖**冠军、传奇球星与国家德比**", "从克鲁伊夫、梅西到当今红蓝军团主力阵容"),
                ("**通过链接**挑战好友", "发送对局链接，看看谁更懂巴萨"),
                ("成绩**即时呈现，一轮接一轮**", "每轮的得分、正确率与进步一目了然"),
                ("登上**排行榜**榜首", "你与好友之间的实时排名"),
                ("答错了？答案**附带解析**", "每道题都会显示正确答案及原因"),
                ("卡住了？**使用提示**", "每题一次提示，随时可用"),
                ("每天回来，**保持连续答题**", "每日连续答题、排行榜与对局历史")
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Chelsea**", "El quiz definitivo sobre títulos, leyendas e historia del Chelsea FC"),
                ("Preguntas sobre **títulos, ídolos y rivalidades**", "De Lampard y Drogba a Hazard y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Chelsea"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "fr": [
                ("Défiez vos connaissances sur **Chelsea**", "Le quiz ultime sur les titres, les légendes et l'histoire de Chelsea FC"),
                ("Questions sur les **titres, légendes et rivalités**", "De Lampard et Drogba à Hazard jusqu'à l'effectif actuel"),
                ("Défiez un ami **par lien**", "Envoyez la partie et voyez qui connaît le mieux Chelsea"),
                ("Votre score à l'instant, **match après match**", "Points, pourcentage de réussite et progression à chaque manche"),
                ("Le plus fort **grimpe au sommet**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ],
            "id": [
                ("Uji pengetahuanmu tentang **Chelsea**", "Kuis definitif tentang gelar, legenda, dan sejarah Chelsea FC"),
                ("Pertanyaan tentang **gelar, ikon, dan rivalitas**", "Dari Lampard dan Drogba hingga Hazard dan skuad saat ini"),
                ("Tantang teman **lewat tautan**", "Kirim pertandingan dan buktikan siapa yang paling tahu tentang Chelsea"),
                ("Skormu langsung muncul, **ronde demi ronde**", "Poin, akurasi, dan progres di setiap putaran"),
                ("Yang paling tahu **berada di puncak**", "Peringkat langsung antara kamu dan teman-temanmu"),
                ("Salah jawab? Jawabannya ada **penjelasannya**", "Setiap soal menampilkan jawaban yang benar beserta alasannya"),
                ("Buntu? **Gunakan petunjuk**", "Satu bantuan per soal saat kamu membutuhkannya"),
                ("Kembali tiap hari dan **jaga rentetanmu**", "Rentetan harian, peringkat, dan riwayat pertandinganmu")
            ],
            "zh": [
                ("测试你对**切尔西**的了解程度", "关于冠军荣誉、传奇球星与切尔西历史的终极问答"),
                ("题目涵盖**冠军、传奇球星与经典对决**", "从兰帕德、德罗巴到阿扎尔与现今阵容"),
                ("**通过链接**挑战好友", "发送对局链接，看看谁更懂切尔西"),
                ("成绩**即时呈现，一轮接一轮**", "每轮的得分、正确率与进步一目了然"),
                ("登上**排行榜**榜首", "你与好友之间的实时排名"),
                ("答错了？答案**附带解析**", "每道题都会显示正确答案及原因"),
                ("卡住了？**使用提示**", "每题一次提示，随时可用"),
                ("每天回来，**保持连续答题**", "每日连续答题、排行榜与对局历史")
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
            ],
            "en": [
                ("Test your **PSG** knowledge", "The ultimate quiz on titles, legends and Paris Saint-Germain history"),
                ("Questions on **titles, legends and classics**", "From Mbappé and Neymar to Marquinhos and today's squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows PSG best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del PSG**", "El quiz definitivo sobre títulos, leyendas e historia del Paris Saint-Germain"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De Mbappé y Neymar a Marquinhos y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del PSG"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "de": [
                ("Teste dein Wissen über **PSG**", "Das ultimative Quiz über Titel, Legenden und die Geschichte von Paris Saint-Germain"),
                ("Fragen zu **Titeln, Ikonen und Klassikern**", "Von Mbappé und Neymar bis Marquinhos und dem aktuellen Kader"),
                ("Fordere Freunde **per Link** heraus", "Sende das Spiel und finde heraus, wer PSG am besten kennt"),
                ("Dein Punktestand sofort, **Runde für Runde**", "Punkte, Genauigkeit und Fortschritt in jedem Spiel"),
                ("Wer am meisten weiß, **steht ganz oben**", "Live-Rangliste zwischen dir und deinen Freunden"),
                ("Falsch geantwortet? Die Antwort wird **erklärt**", "Jede Frage zeigt die richtige Lösung und warum"),
                ("Kommst du nicht weiter? **Nimm einen Tipp**", "Ein Joker pro Frage, wenn du Hilfe brauchst"),
                ("Komm täglich wieder und **halte deine Serie**", "Tägliche Serie, Rangliste und dein Spielverlauf")
            ],
            "id": [
                ("Uji pengetahuanmu tentang **PSG**", "Kuis definitif tentang gelar, legenda, dan sejarah Paris Saint-Germain"),
                ("Pertanyaan tentang **gelar, ikon, dan laga klasik**", "Dari Mbappé dan Neymar hingga Marquinhos dan skuad saat ini"),
                ("Tantang teman **lewat tautan**", "Kirim pertandingan dan buktikan siapa yang paling tahu tentang PSG"),
                ("Skormu langsung muncul, **ronde demi ronde**", "Poin, akurasi, dan progres di setiap putaran"),
                ("Yang paling tahu **berada di puncak**", "Peringkat langsung antara kamu dan teman-temanmu"),
                ("Salah jawab? Jawabannya ada **penjelasannya**", "Setiap soal menampilkan jawaban yang benar beserta alasannya"),
                ("Buntu? **Gunakan petunjuk**", "Satu bantuan per soal saat kamu membutuhkannya"),
                ("Kembali tiap hari dan **jaga rentetanmu**", "Rentetan harian, peringkat, dan riwayat pertandinganmu")
            ],
            "fa": [
                ("اطلاعات خود را درباره **PSG** بسنجید", "کوییز جامع درباره جام‌ها، اسطوره‌ها و تاریخ پاری سن ژرمن"),
                ("سوالات درباره **جام‌ها، اسطوره‌ها و بازی‌های بزرگ**", "از امباپه و نیمار تا مارکینیوس و ترکیب فعلی"),
                ("دوستت را **با لینک** به چالش بکش", "مسابقه را بفرست و ببین چه کسی PSG را بهتر می‌شناسد"),
                ("امتیازت در لحظه، **دور به دور**", "امتیاز، درصد پاسخ درست و پیشرفت در هر مسابقه"),
                ("هر که بیشتر بداند **در صدر جدول است**", "رتبه‌بندی لحظه‌ای بین شما و دوستانتان"),
                ("اشتباه پاسخ دادی؟ جواب **همراه با توضیح** است", "هر سوال گزینه درست و دلیل آن را نشان می‌دهد"),
                ("گیر کردی؟ **از راهنما استفاده کن**", "یک راهنمایی برای هر سوال، هر زمان که نیاز داشتی"),
                ("هر روز برگرد و **روند روزانه‌ات را حفظ کن**", "روند روزانه، جدول امتیازات و سابقه بازی‌ها")
            ],
            "ar": [
                ("اختبر معلوماتك عن **باريس سان جيرمان**", "الكويز الشامل عن الألقاب، الأساطير وتاريخ باريس سان جيرمان"),
                ("أسئلة عن **الألقاب، النجوم والكلاسيكيات**", "من مبابي ونيمار إلى ماركينيوس والتشكيلة الحالية"),
                ("تحدَّ صديقاً **عبر الرابط**", "أرسل التحدي واكتشف من يعرف باريس سان جيرمان أكثر"),
                ("نتيجتك فوراً، **جولة بعد جولة**", "النقاط ونسبة الإجابات الصحيحة والتطور في كل مباراة"),
                ("من يعرف أكثر **يتصدر الترتيب**", "ترتيب فوري بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة تأتيك **مشروحة**", "كل سؤال يوضح الإجابة الصحيحة وسببها"),
                ("توقفت؟ **استخدم تلميحاً**", "مساعدة واحدة لكل سؤال، متى احتجت إليها"),
                ("عد يومياً و**حافظ على سلسلتك**", "سلسلة يومية وترتيب وسجل مبارياتك")
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Liverpool**", "El quiz definitivo sobre títulos, leyendas e historia de los Reds"),
                ("Preguntas sobre **títulos, ídolos y rivalidades**", "De Shankly y Gerrard a Salah y la plantilla actual"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Liverpool"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La resposta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, quando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "de": [
                ("Teste dein Wissen **über den FC Liverpool**", "Das ultimative Quiz über Titel, Legenden und die Geschichte der Reds"),
                ("Fragen zu **Titeln, Ikonen und Derbys**", "Von Shankly und Gerrard bis zu Salah und dem aktuellen Kader"),
                ("Fordere Freunde **per Link heraus**", "Teile das Spiel und finde heraus, wer Liverpool am besten kennt"),
                ("Dein Punktestand sofort, **Runde für Runde**", "Punkte, Genauigkeit und Fortschritt in jedem Spiel"),
                ("Wer am meisten weiß, **steht ganz oben**", "Live-Rangliste zwischen dir und deinen Freunden"),
                ("Falsch gelegen? Die Antwort wird **erklärt**", "Jede Frage zeigt die richtige Lösung und warum"),
                ("Kommst du nicht weiter? **Nutz einen Tipp**", "Ein Joker pro Frage, wann immer du ihn brauchst"),
                ("Komm täglich wieder und **halte deine Serie**", "Tägliche Serie, Bestenliste und Spielverlauf")
            ],
            "id": [
                ("Uji pengetahuanmu tentang **Liverpool FC**", "Kuis definitif tentang gelar, legenda, dan sejarah Anfield"),
                ("Pertanyaan tentang **gelar, ikon, dan rivalitas**", "Dari Shankly dan Gerrard hingga Salah dan skuad saat ini"),
                ("Tantang teman **lewat tautan**", "Kirim pertandingan dan buktikan siapa yang paling tahu tentang Liverpool"),
                ("Skormu langsung muncul, **ronde demi ronde**", "Poin, akurasi, dan progres di setiap putaran"),
                ("Yang paling tahu **berada di puncak**", "Peringkat langsung antara kamu dan teman-temanmu"),
                ("Salah jawab? Jawabannya ada **penjelasannya**", "Setiap soal menampilkan jawaban yang benar beserta alasannya"),
                ("Buntu? **Gunakan petunjuk**", "Satu bantuan per soal saat kamu membutuhkannya"),
                ("Kembali tiap hari dan **jaga rentetanmu**", "Rentetan harian, peringkat, dan riwayat pertandinganmu")
            ],
            "nl": [
                ("Test je kennis over **Liverpool FC**", "De ultieme quiz over titels, legendes en de historie van Anfield"),
                ("Vragen over **titels, iconen en rivaliteiten**", "Van Shankly en Gerrard tot Salah en de huidige selectie"),
                ("Daag een vriend uit **via een link**", "Deel de match en zie wie Liverpool het beste kent"),
                ("Je score direct in beeld, **ronde na ronde**", "Punten, nauwkeurigheid en voortgang in elk potje"),
                ("Wie het meeste weet, **staat aan de top**", "Realtime klassement tussen jou en je vrienden"),
                ("Fout geantwoord? Het antwoord wordt **uitgelegd**", "Elke vraag toont de juiste keuze en waarom"),
                ("Zit je vast? **Gebruik een hint**", "Eén hulpmiddel per vraag, wanneer je het nodig hebt"),
                ("Kom dagelijks terug en **behoud je reeks**", "Dagelijkse streak, ranglijst en wedstrijdgeschiedenis")
            ],
            "ar": [
                ("اختبر معلوماتك **عن ليفربول**", "الكويز الشامل عن الألقاب، الأساطير وتاريخ الأنفيلد"),
                ("أسئلة عن **الألقاب، النجوم والكلاسيكيات**", "من شانكلي وجيرارد إلى صلاح والتشكيلة الحالية"),
                ("تحدَّ صديقك **عبر الرابط**", "أرسل المواجهة واكتشف من يعرف ليفربول أكثر"),
                ("نتيجتك فوراً، **جولة بجولة**", "النقاط، نسبة الدقة وتطور مستواك في كل مباراة"),
                ("الأكثر معرفة **في الصدارة**", "ترتيب فوري بينك وبين أصدقائك"),
                ("أخطأت؟ الإجابة تأتي **مع الشرح**", "كل سؤال يعرض الإجابة الصحيحة مع بيان السبب"),
                ("عالق؟ **استخدم تلميحاً**", "مساعدة واحدة لكل سؤال متى احتجت إليها"),
                ("عد يومياً وحافظ على **سلسلة أيامك**", "سلسلة متواصلة، ترتيب وسجل مواجهاتك")
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
                ("¿Te trabaste? **Usá una pista**", "Una ayuda por pregunta, quando a necesites"),
                ("Volvé todos los días y **mantené tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "en": [
                ("Test your **Boca Juniors** knowledge", "The ultimate quiz on titles, legends and Xeneize history"),
                ("Questions on **titles, legends and Superclásicos**", "From Maradona and Riquelme to the squad at La Bombonera"),
                ("Challenge a friend **by link**", "Send the match and see who knows Boca best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
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
            ],
            "en": [
                ("Test your **River Plate** knowledge", "The ultimate quiz on titles, legends and Millonario history"),
                ("Questions on **titles, legends and Superclásicos**", "From Di Stéfano and Francescoli to the squad at El Monumental"),
                ("Challenge a friend **by link**", "Send the match and see who knows River best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
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
            ],
            "en": [
                ("Test your **Club América** knowledge", "The ultimate quiz on titles, legends and Azulcrema history"),
                ("Questions on **titles, legends and derbies**", "From Cuauhtémoc Blanco to today's squad at Estadio Azteca"),
                ("Challenge a friend **by link**", "Send the match and see who knows América best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
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
                ("¿Te trabaste? **Usa una pista**", "Una ajuda por pregunta, quando a necesites"),
                ("Vuelve todos los días y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "en": [
                ("Test your **Chivas Guadalajara** knowledge", "The ultimate quiz on titles, legends and Rebaño Sagrado history"),
                ("Questions on **titles, legends and Clásicos**", "From Chava Reyes to today's squad at Estadio Akron"),
                ("Challenge a friend **by link**", "Send the match and see who knows Chivas best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Al-Hilal**", "El quiz definitivo sobre el Al-Hilal, sus títulos y su historia"),
                ("Preguntas sobre **títulos, ídolos y el Derbi de Riad**", "De la hegemonía en la AFC Champions League a ídolos como Sami Al-Jaber"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y mira quién sabe más del Al-Hilal"),
                ("Tu marcador al instante, **ronda a ronda**", "Puntuación, porcentaje de aciertos y evolución en cada partida"),
                ("Quien sabe más **llega a la cima**", "Ranking en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta **viene explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te trabaste? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, ranking e historial de tus partidas")
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Al Ahly**", "El quiz definitivo sobre el Club del Siglo, sus títulos y su historia"),
                ("Preguntas sobre **títulos, ídolos y el Derbi de El Cairo**", "De la hegemonía en la CAF Champions League a ídolos como Aboutrika"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Al Ahly"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
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
            ],
            "en": [
                ("Test your **Galatasaray** knowledge", "The ultimate quiz on titles, legends and Cimbom history"),
                ("Questions on **titles, legends and classics**", "From the 2000 UEFA Cup win to today's Aslan squad"),
                ("Challenge a friend **by link**", "Send the match and see who knows Galatasaray best"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Galatasaray**", "El quiz definitivo sobre títulos, ídolos e historia del Cimbom"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De la Copa de la UEFA en 2000 al plantel actual de los Leones"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Galatasaray"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "de": [
                ("Teste dein Wissen über **Galatasaray**", "Das ultimative Quiz über Titel, Ikonen und die Geschichte von Cimbom"),
                ("Fragen zu **Titeln, Legenden und Klassikern**", "Vom UEFA-Pokalsieg 2000 bis zum aktuellen Kader der Löwen"),
                ("Fordere einen Freund **per Link heraus**", "Teile das Spiel und finde heraus, wer Galatasaray am besten kennt"),
                ("Dein Punktestand sofort, **Runde für Runde**", "Punkte, Genauigkeit und Fortschritt in jedem Spiel"),
                ("Wer am meisten weiß, **steht ganz oben**", "Live-Rangliste zwischen dir und deinen Freunden"),
                ("Falsch gelegen? Die Antwort wird **erklärt**", "Jede Frage zeigt die richtige Lösung und warum"),
                ("Kommst du nicht weiter? **Nutz einen Tipp**", "Ein Joker pro Frage, wann immer du ihn brauchst"),
                ("Komm täglich wieder und **halte deine Serie**", "Tägliche Serie, Bestenliste und Spielverlauf")
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
                ("The **football quiz** for Celtic fans", "Trivia on titles, legends and the Hoops' history"),
                ("Questions on **titles, legends and the Old Firm**", "From the 1967 Lisbon Lions to today's clashes with Rangers"),
                ("Challenge a friend **by link**", "Send the match and see who knows more about Celtic"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Climb the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **del Celtic**", "El quiz definitivo sobre títulos, ídolos e historia de los Bhoys"),
                ("Preguntas sobre **títulos, ídolos y clásicos**", "De los Lisbon Lions de 1967 al Old Firm contra el Rangers"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Celtic"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Rangers**", "El quiz completo sobre títulos, ídolos e historia de los Gers"),
                ("Preguntas sobre **títulos, leyendas y el Old Firm**", "De los 55 títulos de liga a la Recopa de 1972 y clásicos ante el Celtic"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Rangers"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
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
            ],
            "es": [
                ("Desafía tus conocimientos **del Al-Nassr**", "El quiz completo sobre títulos, ídolos e historia del Al-Alami"),
                ("Preguntas sobre **títulos, leyendas y el Derbi de Riad**", "De Majed Abdullah a Cristiano Ronaldo y los Caballeros de Najd"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más del Al-Nassr"),
                ("Tu marcador al instante, **partida a partida**", "Puntuación, porcentaje de acierto e evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ]
        }
    },
    "flagsworld": {
        "name": "Quiz Bandeiras do Mundo",
        "colors": [(8, 46, 56), (14, 77, 92), (5, 29, 35)],
        "highlight_color": (232, 145, 45),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Bandeiras**", "O quiz completo sobre bandeiras de todos os países do mundo"),
                ("Bandeiras de **todos os continentes**", "De mais de 250 países e territórios ao redor do planeta"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem reconhece mais bandeiras"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **World Flags** knowledge", "The comprehensive quiz on flags from every country and territory"),
                ("Flags from **every continent**", "Over 250 countries and territories across the globe"),
                ("Challenge a friend **by link**", "Send the match and see who recognizes the most flags"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Pon a prueba tu conocimiento **de Banderas**", "El quiz definitivo sobre banderas de todos los países do mundo"),
                ("Banderas de **todos los continentes**", "De más de 250 países y territorios de todo el planeta"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién reconoce más banderas"),
                ("Tu puntaje al instante, **partida a partida**", "Puntos, precisión y progreso en cada ronda"),
                ("El que sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Atascado? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de partidas")
            ],
            "fr": [
                ("Testez vos connaissances sur les **Drapeaux**", "Le quiz complet sur les drapeaux de tous les pays du monde"),
                ("Drapeaux de **tous les continents**", "Plus de 250 pays et territoires à travers le monde"),
                ("Défiez un ami **par lien**", "Partagez la partie et voyez qui reconnaît le plus de drapeaux"),
                ("Votre score en direct, **manche après manche**", "Points, précision et progression à chaque partie"),
                ("Le plus fort **au sommet**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ],
            "de": [
                ("Teste dein Wissen über **Flaggen der Welt**", "Das umfassende Quiz über Flaggen aller Länder und Gebiete"),
                ("Flaggen aus **allen Kontinenten**", "Über 250 Länder und Territorien rund um den Globus"),
                ("Fordere Freunde **per Link** heraus", "Teile das Spiel und finde heraus, wer die meisten Flaggen kennt"),
                ("Dein Punktestand, **Runde für Runde**", "Punkte, Trefferquote und Fortschritt in jedem Spiel"),
                ("Wer am meisten weiß, **steht ganz oben**", "Echtzeit-Bestenliste unter dir und deinen Freunden"),
                ("Falsch geantwortet? Antwort mit **Erklärung**", "Jede Frage zeigt die richtige Antwort und den Grund"),
                ("Kommst du nicht weiter? **Nimm einen Hinweis**", "Ein Tipp pro Frage, wann immer du Hilfe brauchst"),
                ("Komm täglich wieder und **halte die Serie**", "Tägliche Serie, Rangliste und Spielverlauf")
            ],
            "it": [
                ("Metti alla prova le tue conoscenze sulle **Bandiere**", "Il quiz completo sulle bandiere di tutti i paesi del mondo"),
                ("Bandiere di **tutti i continenti**", "Oltre 250 paesi e territori in tutto il pianeta"),
                ("Sfida un amico **tramite link**", "Invia la partita e scopri chi riconosce più bandiere"),
                ("Il tuo punteggio, **round dopo round**", "Punti, percentuale di successo ed evoluzione in ogni partita"),
                ("Chi sa di più **arriva in cima**", "Classifica in tempo reale tra te e i tuoi amici"),
                ("Hai sbagliato? La risposta è **spiegata**", "Ogni domanda mostra la risposta corretta e il perché"),
                ("Bloccato? **Usa un suggerimento**", "Un aiuto per domanda quando ne hai bisogno"),
                ("Torna ogni giorno e **mantieni la serie**", "Serie giornaliera, classifica e cronologia delle tue partite")
            ],
            "id": [
                ("Uji pengetahuanmu tentang **Bendera Dunia**", "Kuis lengkap tentang bendera semua negara dan wilayah di dunia"),
                ("Bendera dari **semua benua**", "Lebih dari 250 negara dan wilayah di seluruh penjuru dunia"),
                ("Tantang teman **lewat tautan**", "Kirim putaran permainan dan lihat siapa yang mengenali lebih banyak bendera"),
                ("Skor langsung, **ronde demi ronde**", "Poin, akurasi, dan perkembangan di setiap permainan"),
                ("Yang paling tahu **berada di puncak**", "Papan peringkat waktu nyata antara kamu dan teman-temanmu"),
                ("Salah jawab? Ada **penjelasannya**", "Setiap soal menunjukkan jawaban benar dan alasannya"),
                ("Buntu? **Gunakan petunjuk**", "Satu bantuan per soal saat kamu membutuhkannya"),
                ("Main tiap hari dan **jaga rekor streak**", "Streak harian, peringkat, dan riwayat permainanmu")
            ],
            "tr": [
                ("Dünya **Bayrakları** bilginizi test edin", "Dünyadaki tüm ülke ve bölgelerin bayraklarını içeren kapsamlı bilgi yarışması"),
                ("Tüm kıtalardan **bayraklar**", "Gezegenin dört bir yanından 250'den fazla ülke ve bölge"),
                ("Bir arkadaşına **bağlantıyla** meydan oku", "Oyunu gönder ve kimin daha çok bayrak bildiğini gör"),
                ("Puanın anında, **tur tur cebinde**", "Her oyunda puan, doğruluk oranı ve gelişim grafiği"),
                ("En çok bilen **zirveye çıkar**", "Arkadaşlarınla aranda gerçek zamanlı sıralama"),
                ("Bilemedin mi? Cevap **açıklamasıyla** gelir", "Her soruda doğru cevap ve gerekçesi gösterilir"),
                ("Takıldın mı? **İpucu kullan**", "İhtiyaç duyduğunda her soru için bir yardım hakkı"),
                ("Her gün gel و**serini koru**", "Günlük seri, sıralama tablosu وmaç geçmişi")
            ]
        }
    },
    "worldclubs": {
        "name": "Quiz de Clubes do Mundo",
        "colors": [(107, 29, 46), (140, 53, 71), (61, 15, 26)],
        "highlight_color": (232, 184, 48),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Clubes**", "O quiz completo sobre clubes de futebol de mais de 90 países"),
                ("Escudos, estádios **e curiosidades**", "Identidade visual e história dos maiores clubes do mundo"),
                ("Desafie um amigo **por link**", "Envie a partida e veja quem conhece mais clubes"),
                ("Seu placar na hora, **rodada a rodada**", "Pontuação, percentual de acerto e evolução a cada partida"),
                ("Quem sabe mais **fica no topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **World Clubs** knowledge", "The comprehensive quiz on football clubs from over 90 countries"),
                ("Badges, stadiums **and trivia**", "The visual identity and history of the world's biggest clubs"),
                ("Challenge a friend **by link**", "Send the match and see who knows more clubs"),
                ("Your score, **instantly, match after match**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right one and why"),
                ("Stuck? **Use a hint**", "One assist per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **de Clubes**", "El quiz completo sobre clubes de fútbol de más de 90 países"),
                ("Escudos, estadios **y curiosidades**", "Identidad visual e historia de los clubes más grandes del mundo"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién conoce más clubes"),
                ("Tu puntaje al instante, **ronda a ronda**", "Puntuación, porcentaje de acierto y progreso en cada partida"),
                ("Quien sabe más **llega a la cima**", "Ranking en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Atascado? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, ranking e historial de tus partidas")
            ]
        }
    },
    "ufc": {
        "name": "UFC Quiz",
        "colors": [(18, 18, 18), (52, 12, 12), (10, 10, 10)],
        "highlight_color": (230, 30, 30),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de UFC**", "O quiz sobre lutadores, regras, categorias de peso e momentos históricos"),
                ("Perguntas sobre **campeões, finalizações e cinturões**", "Da história das lutas às regras unificadas, rodada após rodada"),
                ("Desafie um amigo **por link**", "Envie a rodada e veja quem entende mais de MMA"),
                ("Seu placar na hora, **round a round**", "Pontuação, percentual de acerto e evolução a cada rodada"),
                ("Quem sabe mais **leva o cinturão**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **UFC knowledge**", "The quiz on fighters, rules, weight classes and historic moments"),
                ("Questions on **champions, submissions and belts**", "From fight history to the unified rules, round after round"),
                ("Challenge a friend **by link**", "Send the round and see who knows MMA best"),
                ("Your score, **instantly, round by round**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right answer and why"),
                ("Stuck? **Use a hint**", "One hint per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **de UFC**", "El quiz sobre peleadores, reglas, categorías de peso y momentos históricos"),
                ("Preguntas sobre **campeones, sumisiones y cinturones**", "De la historia de las peleas a las reglas unificadas, ronda tras ronda"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de MMA"),
                ("Tu marcador al instante, **round a round**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **se lleva el cinturón**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "fr": [
                ("Testez vos connaissances **sur l'UFC**", "Le quiz sur les combattants, les règles, les catégories de poids et les moments historiques"),
                ("Des questions sur **champions, soumissions et ceintures**", "De l'histoire des combats aux règles unifiées, manche après manche"),
                ("Défiez un ami **par lien**", "Envoyez la manche et voyez qui s'y connaît le plus en MMA"),
                ("Votre score en direct, **round après round**", "Points, taux de réussite et progression à chaque manche"),
                ("Celui qui en sait le plus **remporte la ceinture**", "Classement en temps réel entre vous et vos amis"),
                ("Une erreur ? La réponse est **expliquée**", "Chaque question affiche la bonne réponse et le pourquoi"),
                ("Bloqué ? **Utilisez un indice**", "Une aide par question, quand vous en avez besoin"),
                ("Revenez chaque jour et **gardez votre série**", "Série quotidienne, classement et historique de vos manches")
            ]
        }
    },
    "nfl": {
        "name": "NFL Quiz",
        "colors": [(23, 27, 31), (28, 62, 48), (14, 18, 22)],
        "highlight_color": (72, 170, 120),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de NFL**", "O quiz sobre regras, equipes, estrelas e a história do futebol americano"),
                ("Perguntas sobre **times, jogadas e recordes**", "Das regras do jogo aos grandes nomes da liga, rodada após rodada"),
                ("Desafie um amigo **por link**", "Envie a rodada e veja quem entende mais de futebol americano"),
                ("Seu placar na hora, **jogada a jogada**", "Pontuação, percentual de acerto e evolução a cada rodada"),
                ("Quem sabe mais **chega ao topo**", "Ranking em tempo real entre você e seus amigos"),
                ("Errou? A resposta vem **explicada**", "Cada questão mostra a certa e o porquê"),
                ("Travou? **Use uma dica**", "Uma ajuda por questão, quando você precisar"),
                ("Volte todo dia e **mantenha a sequência**", "Streak diária, ranking e histórico das suas rodadas")
            ],
            "en": [
                ("Test your **NFL knowledge**", "The quiz on rules, teams, stars and the history of football"),
                ("Questions on **teams, plays and records**", "From the rules of the game to the league's greats, round after round"),
                ("Challenge a friend **by link**", "Send the round and see who knows football best"),
                ("Your score, **instantly, play by play**", "Points, accuracy and progress in every round"),
                ("Top the **leaderboard**", "Real-time ranking between you and your friends"),
                ("Got it wrong? The answer comes **explained**", "Every question shows the right answer and why"),
                ("Stuck? **Use a hint**", "One hint per question, whenever you need it"),
                ("Come back daily and **keep your streak**", "Daily streak, ranking and match history")
            ],
            "es": [
                ("Desafía tus conocimientos **de NFL**", "El quiz sobre reglas, equipos, estrellas e historia del fútbol americano"),
                ("Preguntas sobre **equipos, jugadas y récords**", "De las reglas del juego a los grandes nombres de la liga, ronda tras ronda"),
                ("Desafía a un amigo **por enlace**", "Envía la partida y descubre quién sabe más de fútbol americano"),
                ("Tu marcador al instante, **jugada a jugada**", "Puntuación, porcentaje de acierto y evolución en cada ronda"),
                ("Quien sabe más **llega a la cima**", "Clasificación en tiempo real entre tú y tus amigos"),
                ("¿Fallaste? La respuesta viene **explicada**", "Cada pregunta muestra la correcta y el porqué"),
                ("¿Te atascas? **Usa una pista**", "Una ayuda por pregunta, cuando la necesites"),
                ("Vuelve cada día y **mantén tu racha**", "Racha diaria, clasificación e historial de tus partidas")
            ],
            "de": [
                ("Testen Sie Ihr **NFL-Wissen**", "Das Quiz zu Regeln, Teams, Stars und zur Geschichte des American Football"),
                ("Fragen zu **Teams, Spielzügen und Rekorden**", "Von den Spielregeln bis zu den größten Namen der Liga, Runde für Runde"),
                ("Fordern Sie Freunde **per Link heraus**", "Senden Sie eine Runde und finden Sie heraus, wer sich im Football besser auskennt"),
                ("Ihr Punktestand, **Spielzug für Spielzug**", "Punkte, Trefferquote und Fortschritt in jeder Runde"),
                ("Klettern Sie in der **Rangliste nach oben**", "Vergleichen Sie sich in Echtzeit mit Ihren Freunden"),
                ("Falsch beantwortet? Die Lösung wird **erklärt**", "Zu jeder Frage sehen Sie die richtige Antwort und die Erklärung"),
                ("Keine Ahnung? **Nutzen Sie einen Hinweis**", "Ein Hinweis pro Frage, wann immer Sie ihn brauchen"),
                ("Kommen Sie täglich zurück und **halten Sie Ihre Serie am Laufen**", "Tägliche Serie, Rangliste und Verlauf Ihrer Spielrunden")
            ]
        }
    },
    "dinokids": {
        "name": "Dino Kids Quiz",
        "colors": [(10, 40, 70), (18, 66, 118), (6, 24, 48)],
        "highlight_color": (255, 111, 89),
        "slides_by_locale": {
            "pt": [
                ("Descubra o mundo **dos Dinossauros**", "Quiz de dinossauros pra crianças, com fatos reais de paleontologia"),
                ("Perguntas sobre **dieta, silhuetas e curiosidades**", "Espécies, tamanhos e hábitos de um jeito fácil de entender"),
                ("Chame um amigo **pra brincar junto**", "Manda o link do desafio e descubra quem conhece mais dinossauros"),
                ("Veja seu placar **na hora**", "Cada resposta certa conta na hora, rodada após rodada"),
                ("Suba no **topo do ranking**", "Compare sua pontuação com a dos amigos em tempo real"),
                ("Errou a resposta? **Sem problema**", "A explicação certinha aparece na hora, pra aprender brincando"),
                ("Ficou em dúvida? **Peça uma dica**", "Uma ajudinha disponível sempre que precisar"),
                ("Não perca nenhum dia **de descoberta**", "Cada rodada fica guardada no seu histórico, com uma sequência especial pra comemorar")
            ]
        }
    },
    "dinosaurs": {
        "name": "Dinosaurs Quiz",
        "colors": [(20, 27, 22), (40, 52, 45), (12, 16, 13)],
        "highlight_color": (215, 162, 58),
        "slides_by_locale": {
            "pt": [
                ("Desafie seus conhecimentos **de Dinossauros**", "O quiz definitivo de paleontologia, espécie por espécie"),
                ("Perguntas sobre **tempo geológico e descobertas**", "Espécies, períodos e curiosidades da paleontologia real"),
                ("Desafie um colega **por link**", "Compartilhe a partida e veja quem domina mais a paleontologia"),
                ("Acompanhe sua evolução **desafio após desafio**", "Pontuação e percentual de acerto atualizados em tempo real"),
                ("Assuma a liderança **do ranking**", "Compare seu desempenho com o de outros jogadores"),
                ("Resposta errada? **Entenda o porquê**", "Toda questão vem com a explicação da resposta correta"),
                ("Precisa de ajuda? **Use uma dica**", "Um recurso disponível quando o desafio for difícil"),
                ("Sua constância **também conta pontos**", "Um contador de sequência diária acompanha cada partida registrada")
            ],
            "en": [
                ("Test your knowledge **of Dinosaurs**", "A paleontology quiz, species by species"),
                ("Questions on **geological time and discoveries**", "Species, periods and curiosities from real paleontology"),
                ("Challenge a friend **by link**", "Share the match and see who knows paleontology better"),
                ("Track your progress **challenge after challenge**", "Score and accuracy rate updated in real time"),
                ("Take the lead **on the leaderboard**", "Compare your performance with other players"),
                ("Wrong answer? **Understand why**", "Every question comes with an explanation of the correct answer"),
                ("Need help? **Use a hint**", "A tool available when the challenge gets tough"),
                ("Your consistency **counts too**", "A daily streak counter tracks every match you play")
            ],
            "es": [
                ("Pon a prueba tus conocimientos **de Dinosaurios**", "El quiz de paleontología, especie por especie"),
                ("Preguntas sobre **tiempo geológico y descubrimientos**", "Especies, períodos y curiosidades de la paleontología real"),
                ("Reta a un amigo **con un enlace**", "Comparte la partida y mira quién domina más la paleontología"),
                ("Sigue tu evolución **desafío tras desafío**", "Puntuación y porcentaje de aciertos actualizados en tiempo real"),
                ("Toma la delantera **del ranking**", "Compara tu rendimiento con el de otros jugadores"),
                ("¿Respuesta incorrecta? **Entiende por qué**", "Cada pregunta incluye la explicación de la respuesta correcta"),
                ("¿Necesitas ayuda? **Usa una pista**", "Un recurso disponible cuando el desafío se complica"),
                ("Tu constancia **también suma puntos**", "Un contador de racha diaria acompaña cada partida registrada")
            ]
        }
    }
}

ALEFLY_SEEDS = os.environ.get("ALEFLY_SEEDS", os.path.join(ALEFLY_REPO_ROOT, "infra/firebase/seeds/tenants"))


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
    0: {"scale": ZOOM_WIDE, "ios_scale": 0.86, "angle": 0, "x_off": 0},
    1: {"scale": ZOOM_WIDE, "ios_scale": 0.88, "angle": 0, "x_off": 0},
    2: {"scale": ZOOM_TALL, "ios_scale": 0.80, "angle": 0, "x_off": 0},
    3: {"scale": ZOOM_TALL, "ios_scale": 0.84, "angle": 0, "x_off": 0},
    4: {"scale": ZOOM_TALL, "ios_scale": 0.78, "angle": 0, "x_off": 0},
    5: {"scale": ZOOM_TALL, "ios_scale": 0.86, "angle": 0, "x_off": 0},
    6: {"scale": ZOOM_WIDE, "ios_scale": 0.88, "angle": 0, "x_off": 0},
    7: {"scale": ZOOM_TALL, "ios_scale": 0.80, "angle": 0, "x_off": 0},
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
# TODO (2026-09-23, ~/Projetos/alefly's CLAUDE.md TODO section has the full research):
# reorder to lead with real gameplay (slot 1 = question, not home) and the challenge
# differentiator (slot 2), mirroring the now-approved alefly promo-video beat order. NOT a
# safe drop-in reorder of this array alone -- `slides`/`slides_by_locale` below is a
# PER-TENANT, PER-LOCALE, POSITION-INDEXED caption list (matched to SLIDE_SOURCES by
# `enumerate()` index, not by content), hardcoded for dozens of tenant/locale
# combinations. Reordering SLIDE_SOURCES without reordering every one of those caption
# arrays in lockstep silently misaligns captions to the wrong screenshot across the whole
# fleet -- confirmed by reading process_screenshot()'s indexing before attempting this the
# first time, reverted before it shipped. Needs a proper task: a script that reorders
# every tenant's caption array programmatically alongside this one, not a hand edit.
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

STORE_SCENES_PATH = os.path.join(os.path.dirname(__file__), "store-scenes.json")
STORE_SCENE_LIMIT = 8


def select_store_scenes(manifest, tenant=None, locale=None):
    """Resolve localized Android scenes by active game ID and editorial priority."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    if tenant and manifest.get("tenantId") != tenant:
        raise ValueError(f"manifest tenantId '{manifest.get('tenantId')}' does not match --tenant '{tenant}'")
    if locale and manifest.get("contentLocale") != locale:
        raise ValueError(
            f"manifest contentLocale '{manifest.get('contentLocale')}' does not match --locale '{locale}'"
        )

    game_ids = manifest.get("activeGameIds")
    if (not isinstance(game_ids, list) or not game_ids
            or any(not isinstance(game_id, str) or not game_id for game_id in game_ids)):
        raise ValueError("manifest activeGameIds must be a non-empty list of game IDs")
    if len(set(game_ids)) != len(game_ids):
        raise ValueError("manifest activeGameIds must be a non-empty list of unique game IDs")

    with open(STORE_SCENES_PATH, encoding="utf-8") as fh:
        catalog = json.load(fh)
    content_locale = manifest.get("contentLocale")
    candidates = []
    for scene in catalog:
        if scene["gameId"] is not None and scene["gameId"] not in game_ids:
            continue
        localized = scene.get("copy", {}).get(content_locale)
        if not localized:
            continue
        candidates.append({
            **scene,
            "headline": localized["headline"],
            "subheadline": localized["subheadline"],
            "action": localized.get("action"),
        })

    catalog_game_ids = {scene["gameId"] for scene in catalog if scene["gameId"] is not None}
    unsupported = set(game_ids) - catalog_game_ids
    if unsupported:
        raise ValueError(f"no screenshot scenes for active game IDs: {', '.join(sorted(unsupported))}")

    mandatory_ids = {"quiz-question"} if "quiz" in game_ids else set()
    if "profile" in game_ids:
        mandatory_ids.update({"profile-lobby", "profile-hints"})
    by_id = {scene["sceneId"]: scene for scene in candidates}
    missing = mandatory_ids - by_id.keys()
    if missing:
        raise ValueError(f"missing localized copy for required scenes: {', '.join(sorted(missing))}")

    selected = [by_id[scene_id] for scene_id in mandatory_ids]
    selected_ids = {scene["sceneId"] for scene in selected}
    selected.extend(
        scene for scene in sorted(candidates, key=lambda item: item["priority"])
        if scene["sceneId"] not in selected_ids and len(selected) < STORE_SCENE_LIMIT
    )
    if len(selected) > STORE_SCENE_LIMIT:
        raise ValueError(f"required game scenes exceed Android limit of {STORE_SCENE_LIMIT}")
    return sorted(selected, key=lambda item: item["priority"])


def validate_scene_captures(scenes, capture_dir):
    """Return selected capture paths only when every required scene is available."""
    paths = [os.path.join(capture_dir, scene["sourceFile"]) for scene in scenes]
    missing = [path for path in paths if not os.path.isfile(path)]
    if missing:
        raise FileNotFoundError(f"required scene capture missing: {missing[0]}")
    return paths


def remove_stale_slide_outputs(output_dir, selected_count):
    if not os.path.isdir(output_dir):
        return
    for filename in os.listdir(output_dir):
        match = re.fullmatch(r"slide_(\d+)\.png", filename)
        path = os.path.join(output_dir, filename)
        if match and int(match.group(1)) > selected_count and os.path.isfile(path):
            os.remove(path)


def candidates_for_tenant(tenant, platform, locale):
    sub = ("android", "screenshots") if platform == "android" else (
        "ios", "screenshots", "ipad" if platform == "ipad" else "iphone"
    )
    return [
        os.path.join(ALEFLY_RAW_CAPTURES, tenant, *sub, locale),
        os.path.join(ALEFLY_RAW_CAPTURES, tenant, *sub),
        os.path.join(ALEFLY_RAW_CAPTURES, tenant, *sub, "pt"),
    ]

# Four-caption tenants (not yet on the eight-slot spec above) map captions positionally
# onto these captures. Deliberately a different order from SLIDE_SOURCES: slot 3 there is
# the share sheet, here it is the answer feedback. Retire together with the last legacy tenant.
LEGACY_SLIDE_FILES = ["01-home.png", "02-question.png", "03-answer-feedback.png", "04-result-summary.png"]

# Locales written right-to-left. Nunito carries no Arabic glyphs at all — an "ar"
# slide rendered with it comes out as a row of .notdef boxes, which measures a normal
# width so only looking at the image catches it.
RTL_LOCALES = {"ar", "fa", "ur"}
ARABIC_FONTS = ("/System/Library/Fonts/SFArabic.ttf", "/System/Library/Fonts/GeezaPro.ttc")

# Same .notdef-box failure as Arabic: Nunito carries no CJK glyphs.
CJK_LOCALES = {"zh", "ja"}
CJK_FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"

KOREAN_LOCALES = {"ko"}
KOREAN_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

DEVANAGARI_LOCALES = {"hi"}
DEVANAGARI_FONTS = (
    "/System/Library/Fonts/Supplemental/ITFDevanagari.ttc",
    "/System/Library/Fonts/Supplemental/DevanagariMT.ttc"
)


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
    if locale in KOREAN_LOCALES and os.path.exists(KOREAN_FONT):
        # index 6/0 = Bold / Regular in AppleSDGothicNeo.ttc
        head = ImageFont.truetype(KOREAN_FONT, size_h, index=6)
        return Fonts(head, head, ImageFont.truetype(KOREAN_FONT, size_s, index=0))
    if locale in DEVANAGARI_LOCALES:
        devanagari = next((f for f in DEVANAGARI_FONTS if os.path.exists(f)), None)
        if devanagari:
            # index 1/0 = Bold / Book in ITFDevanagari.ttc
            idx_b = 1 if "ITF" in devanagari else 0
            head = ImageFont.truetype(devanagari, size_h, index=idx_b)
            return Fonts(head, head, ImageFont.truetype(devanagari, size_s, index=0))
    return Fonts(_nunito(size_h, HEADLINE_WEIGHT), _nunito(size_h, HIGHLIGHT_WEIGHT),
                 _nunito(size_s, SUBHEAD_WEIGHT))

# CJK Unified Ideographs, Hiragana, Katakana + common fullwidth punctuation.
# These scripts carry no spaces between words, so wrapping has to break per character.
CJK_RE = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF\u3000-\u303F\uFF00-\uFFEF]')

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


def process_screenshot(tenant_key, idx, headline, subheadline, input_path, output_path, platform="android", use_slide_sources=False, locale="pt", action=None):
    config = TENANT_CONFIGS[tenant_key]
    if platform == "ipad":
        cw, ch = 2048, 2732
    elif platform == "android":
        cw, ch = ANDROID_WIDTH, ANDROID_HEIGHT
    else:
        cw, ch = WIDTH, HEIGHT
    canvas = Image.new('RGB', (cw, ch))
    palette = derive_palette(tenant_key)
    if action:
        subheadline = f"{subheadline} **{action}**"
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
        if platform == "ipad":
            target_w = int(cw * 0.82)
        elif platform == "ios":
            target_w = int(cw * conf.get("ios_scale", 0.86))
        else:
            target_w = int(cw * conf["scale"])
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
                island_w = int(target_w * 0.29)
                island_h = int(island_w * 0.28)
                island_y = pad + int(target_h * 0.014)
                island_r = island_h // 2
                ImageDraw.Draw(device_layer).rounded_rectangle(
                    [cam_x - (island_w // 2), island_y, cam_x + (island_w // 2), island_y + island_h],
                    radius=island_r, fill=(10, 10, 10))

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
    "cars": {"pt": "pt-BR", "en": "en-US", "es": ["es-419", "es-ES"], "it": "it-IT", "de": "de-DE"},
    "cricketindia": {"pt": "pt-BR", "en": "en-US", "hi": "hi-IN"},
    "animals": {"pt": "pt-BR", "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN"], "es": ["es-419", "es-ES", "es-US"]},
    "nba": {"pt": "pt-BR", "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-PH", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"]},
    "f1": {"pt": "pt-BR", "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "it": "it-IT", "de": "de-DE"},
    "emoji": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU"], "es": ["es-419", "es-ES", "es-US"]},
    "flamengo": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"]},
    "bible": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU"], "es": ["es-419", "es-ES", "es-US"]},
    "corinthians": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "nl": "nl-NL"},
    "saopaulo": {"pt": ["pt-BR", "pt-PT"], "en": "en-US", "es": "es-419"},
    "palmeiras": {"pt": ["pt-BR", "pt-PT"], "en": "en-US", "es": "es-419"},
    "santos": {"pt": ["pt-BR", "pt-PT"], "en": "en-US", "es": "es-419"},
    "vasco": {"pt": ["pt-BR", "pt-PT"], "en": "en-US", "es": "es-419"},
    "botafogo": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "fr": ["fr-FR", "fr-CA"], "ar": "ar"},
    "fluminense": {"pt": ["pt-BR", "pt-PT"], "en": "en-US", "es": ["es-419", "es-ES", "es-US"]},
    "bocajuniors": {"es": "es-419"},
    "riverplate": {"es": "es-419"},
    "clubamerica": {"es": "es-419"},
    "chivas": {"es": "es-419"},
    "atleticomg": {"es": "es-419"},
    "cruzeiro": {"es": "es-419"},
    "internacional": {"es": "es-419"},
    "flagsworld": {"pt": "pt-BR", "en": ["en-US", "en-GB", "en-IN"], "es": ["es-419", "es-ES", "es-US"], "fr": ["fr-FR", "fr-CA"], "de": "de-DE", "id": "id", "it": "it-IT", "tr": "tr"},
    "worldclubs": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"]},
    "realmadrid": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "fr": ["fr-FR", "fr-CA"], "de": "de-DE", "id": "id", "ar": "ar", "hr": "hr", "tr": ["tr", "tr-TR"], "zh": "zh-CN", "ca": "ca"},
    "psg": {"pt": ["pt-BR", "pt-PT"], "en": "en-US", "fr": ["fr-FR", "fr-CA"], "es": ["es-419", "es-ES", "es-US"], "de": "de-DE", "id": "id", "fa": "fa"},
    "chelsea": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "fr": ["fr-FR", "fr-CA"], "id": "id"},
    "manchesterunited": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "id": "id", "ar": "ar", "zh": "zh-CN", "hi": "hi-IN", "ko": "ko-KR", "ja": "ja-JP", "ur": "ur"},
    "manchestercity": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "no": "no-NO", "ar": "ar"},
    "liverpool": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "de": "de-DE", "id": "id", "nl": "nl-NL", "ar": "ar"},
    "barcelona": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "ca": "ca", "de": "de-DE", "fr": ["fr-FR", "fr-CA"], "id": "id", "nl": "nl-NL", "pl": "pl-PL", "ar": "ar", "zh": "zh-CN"},
    "celtic": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"]},
    "rangers": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"]},
    "alahly": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "ar": "ar"},
    "alnassr": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "ar": "ar"},
    "galatasaray": {"tr": ["tr", "tr-TR"], "pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "de": "de-DE"},
    "alhilal": {"pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "ar": "ar"},
    "juventus": {"it": "it-IT", "pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"], "fr": ["fr-FR", "fr-CA"], "ar": "ar"},
    "bayern": {"de": "de-DE", "pt": ["pt-BR", "pt-PT"], "en": ["en-US", "en-GB", "en-CA", "en-AU", "en-IN", "en-SG", "en-ZA"], "es": ["es-419", "es-ES", "es-US"]},
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
    "nl": "nl-NL",
    "da": "da-DK",
    "no": "no-NO",
    "pl": "pl-PL",
    "ja": "ja-JP",
    "ur": "ur",
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

def dump_locales(tenant: str) -> dict:
    """JSON-serializable map of every content locale this tenant supports to its
    resolved store locales and whether slide copy exists for it. Consumed by
    alefly's CI (scripts/ci/store-assets-gap.mjs) so the store-locale map and
    slide-copy availability never get duplicated in JS."""
    if tenant not in TENANT_CONFIGS:
        raise KeyError(tenant)
    config = TENANT_CONFIGS[tenant]
    is_multi_locale = "slides_by_locale" in config
    content_locales = list(config["slides_by_locale"].keys()) if is_multi_locale else ["pt"]

    with open(os.path.join(ALEFLY_SEEDS, f"{tenant}.json"), encoding="utf-8") as fh:
        seed = json.load(fh)
    seed_locales = seed.get("supportedLocales") or ["pt"]

    result = {}
    for locale in seed_locales:
        result[locale] = {
            "storeLocales": resolve_store_locales(tenant, locale),
            "hasSlides": locale in content_locales,
        }
    return result

def run_factory(target_tenant=None, target_platform="all", target_locale=None, manifest_data=None):
    if manifest_data is not None:
        if not isinstance(manifest_data, dict):
            raise ValueError("manifest must be a JSON object")
        if target_platform != "android" or not target_tenant or not target_locale:
            raise ValueError("--manifest requires --tenant, --locale and --platform android")
        if manifest_data.get("tenantId") != target_tenant:
            raise ValueError("manifest tenantId does not match --tenant")
        if manifest_data.get("contentLocale") != target_locale:
            raise ValueError("manifest contentLocale does not match --locale")
        game_ids = manifest_data.get("activeGameIds")
        if not isinstance(game_ids, list) or not game_ids or any(not isinstance(game_id, str) for game_id in game_ids):
            raise ValueError("manifest activeGameIds must be a non-empty list of game IDs")
        if len(set(game_ids)) != len(game_ids):
            raise ValueError("manifest activeGameIds must not contain duplicates")
        if manifest_data.get("storeLocale") not in resolve_store_locales(target_tenant, target_locale):
            raise ValueError("manifest storeLocale is not configured for this tenant and locale")
    use_dynamic_scenes = bool(manifest_data is not None and "profile" in manifest_data["activeGameIds"])
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
            if use_dynamic_scenes:
                locales = [target_locale]
            elif is_multi_locale:
                locales = [target_locale] if target_locale else list(config["slides_by_locale"].keys())
            else:
                if target_locale and target_locale != "pt":
                    print(f"  ⚠️ Tenant '{tenant}' only has pt slides — ignoring --locale {target_locale}.")
                locales = ["pt"]

            for locale in locales:
                if use_dynamic_scenes:
                    try:
                        scenes = select_store_scenes(manifest_data, tenant=tenant, locale=locale)
                        required_paths = None
                        capture_dir = None
                        for candidate_dir in candidates_for_tenant(tenant, platform, locale):
                            try:
                                required_paths = validate_scene_captures(scenes, candidate_dir)
                                capture_dir = candidate_dir
                                break
                            except FileNotFoundError:
                                continue
                        if capture_dir is None:
                            validate_scene_captures(scenes, candidates_for_tenant(tenant, platform, locale)[0])
                        store_locales = [manifest_data["storeLocale"]]
                        for store_locale in store_locales:
                            output_dir = os.path.join(
                                ALEFLY_STORE_ASSETS, tenant, store_locale, "screenshots", "android"
                            )
                            remove_stale_slide_outputs(output_dir, len(scenes))
                            os.makedirs(output_dir, exist_ok=True)
                            raw_persist_dir = os.path.join(output_dir, "raw")
                            os.makedirs(raw_persist_dir, exist_ok=True)
                            for scene, input_file in zip(scenes, required_paths):
                                shutil.copyfile(input_file, os.path.join(raw_persist_dir, scene["sourceFile"]))
                            for idx, (scene, input_file) in enumerate(zip(scenes, required_paths)):
                                process_screenshot(
                                    tenant, idx, scene["headline"], scene["subheadline"], input_file,
                                    os.path.join(output_dir, f"slide_{idx + 1}.png"),
                                    platform="android", use_slide_sources=False, locale=locale,
                                    action=scene.get("action"),
                                )
                    except Exception as exc:
                        failures.append(f"{tenant}/{locale}/android dynamic scenes: {exc!r}")
                        print(f"    ❌ Failed to render dynamic scenes ({locale}): {exc!r}")
                    continue

                slides = config["slides_by_locale"][locale] if is_multi_locale else config["slides"]
                store_locales = resolve_store_locales(tenant, locale)

                sub = ("android", "screenshots") if platform == "android" else ("ios", "screenshots", "ipad" if platform == "ipad" else "iphone")
                # Per-locale folder first; then the unsuffixed legacy folder (a tenant that
                # became multi-locale after its captures were taken — 14 clubs on 2026-09-03
                # were silently skipped here); then the "pt" folder (single-locale tenants,
                # or a locale whose own capture hasn't been re-run yet). No cross-platform
                # (ios<->android) fallback anymore -- that silently produced a platform's
                # published screenshots from the OTHER platform's raw capture (real risk:
                # the wrong device frame/status-bar baked into a "final" image), removed as
                # part of the 2026-09-23 raw-captures reorg rather than kept as a safety net.
                candidates = [os.path.join(ALEFLY_RAW_CAPTURES, tenant, *sub, locale),
                              os.path.join(ALEFLY_RAW_CAPTURES, tenant, *sub),
                              os.path.join(ALEFLY_RAW_CAPTURES, tenant, *sub, "pt")]
                # Prefer candidate that has at least 8 files (the full 8-slide set)
                raw_screenshots_dir = next((d for d in candidates if len(glob.glob(f"{d}/*.png")) >= len(SLIDE_SOURCES)), None)
                if not raw_screenshots_dir:
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

                    # Persist the raw (pre-framed) captures alongside the framed store-listing
                    # slides -- the promo-video pipeline (alefly's render-promo-frames.mjs)
                    # composes directly from these, not from the framed slide_N.png (which has
                    # a device bezel baked in, wrong for that renderer's own phone-mockup frame).
                    # Android + eight-slot tenants only: PROMO_VIDEO_BEATS needs the full named
                    # set (01-home.png..08-challenge-share.png), which only exists for tenants
                    # already migrated to SLIDE_SOURCES naming (use_slide_sources).
                    if platform == "android" and use_slide_sources:
                        raw_persist_dir = os.path.join(output_dir, "raw")
                        os.makedirs(raw_persist_dir, exist_ok=True)
                        for slide_source in SLIDE_SOURCES:
                            src = os.path.join(raw_screenshots_dir, slide_source["file"])
                            if os.path.exists(src):
                                shutil.copyfile(src, os.path.join(raw_persist_dir, slide_source["file"]))

                    for i, (headline, subheadline) in enumerate(slides):
                        if use_slide_sources:
                            # Never fall back to "whichever PNG happens to be Nth alphabetically"
                            # for named slots -- confirmed live (realmadrid, 2026-09-22) that this
                            # silently substitutes an unrelated screen (challenge-share) for a
                            # named one (hint-used) whenever its own Maestro step failed to fire,
                            # with no failure signal anywhere: the workflow's own "8 PNGs present"
                            # check still passes, since a file did get written, just the wrong one.
                            candidate = os.path.join(raw_screenshots_dir, SLIDE_SOURCES[i]["file"])
                            input_file = candidate if os.path.exists(candidate) else None
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

    # ALEFLY_SEEDS env override (path-bug fix)
    assert "ALEFLY_SEEDS" in globals() and ALEFLY_SEEDS.endswith("infra/firebase/seeds/tenants"), \
        "ALEFLY_SEEDS must resolve relative to ALEFLY_REPO_ROOT, not a hardcoded path"

    # dump_locales: known tenant returns the expected shape
    realmadrid_dump = dump_locales("realmadrid")
    assert realmadrid_dump["pt"]["storeLocales"] == ["pt-BR", "pt-PT"], realmadrid_dump["pt"]
    assert realmadrid_dump["pt"]["hasSlides"] is True
    print("✅ dump_locales: realmadrid pt -> pt-BR/pt-PT, hasSlides true")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default=None, help="Tenant específico para gerar (ex: flamengo, vasco, worldcup, etc)")
    parser.add_argument("--platform", choices=["android", "ios", "ipad", "all"], default="all")
    parser.add_argument("--locale", default=None, help="Locale específico (pt/es/ca) para tenants multi-idioma; default processa todos os locales do tenant")
    parser.add_argument("--manifest", default=None, help="Manifesto de jogos ativos para screenshots Android")
    parser.add_argument("--selfcheck", action="store_true", help="Assert text contrast on every tenant seed and exit")
    parser.add_argument("--dump-locales", metavar="TENANT", default=None, help="Print {contentLocale: {storeLocales, hasSlides}} as JSON for TENANT and exit")
    args = parser.parse_args()

    if args.dump_locales:
        try:
            print(json.dumps(dump_locales(args.dump_locales)))
        except KeyError:
            print(json.dumps({"error": f"tenant '{args.dump_locales}' not found in TENANT_CONFIGS or has no seed file"}), file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(json.dumps({"error": f"no seed file for tenant '{args.dump_locales}' at {ALEFLY_SEEDS}"}), file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if args.selfcheck:
        _selfcheck()
    else:
        manifest_data = None
        if args.manifest:
            try:
                with open(args.manifest, encoding="utf-8") as fh:
                    manifest_data = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                parser.error(f"cannot read --manifest: {exc}")
        try:
            run_factory(
                target_tenant=args.tenant, target_platform=args.platform,
                target_locale=args.locale, manifest_data=manifest_data,
            )
        except ValueError as exc:
            parser.error(str(exc))
