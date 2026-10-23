import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import engine
from PIL import Image


def manifest(tenant="bible", games=("quiz", "profile"), locale="pt"):
    return {
        "tenantId": tenant,
        "storeLocale": "pt-BR",
        "contentLocale": locale,
        "activeGameIds": list(games),
        "games": {},
    }


class StoreSceneSelectionTest(unittest.TestCase):
    def test_realmadrid_top5_scenes_cover_every_supported_locale_and_follow_quiz_scenes(self):
        locales = ("ar", "ca", "de", "en", "es", "fr", "hr", "id", "it", "pt", "ru", "tr", "zh")
        for locale in locales:
            with self.subTest(locale=locale):
                selected = engine.select_store_scenes(
                    manifest("realmadrid", ("quiz", "top5"), locale),
                    tenant="realmadrid",
                    locale=locale,
                )
                top5_scenes = [scene for scene in selected if scene["gameId"] == "top5"]

                self.assertEqual([scene["sceneId"] for scene in top5_scenes], [
                    "top5-lobby", "top5-round",
                ])
                self.assertEqual([scene["sourceFile"] for scene in top5_scenes], [
                    "11-top5-lobby.png", "12-top5-round.png",
                ])
                self.assertEqual([scene["sceneId"] for scene in selected[-2:]], [
                    "top5-lobby", "top5-round",
                ])

    def test_selfcheck_accepts_current_multilocale_storefronts(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            engine._selfcheck()

    def test_profile_manifest_reserves_quiz_and_profile_scenes_and_caps_at_eight(self):
        selected = engine.select_store_scenes(manifest())

        self.assertEqual(len(selected), 8)
        self.assertEqual(
            [scene["sceneId"] for scene in selected],
            [
                "game-list",
                "quiz-question",
                "quiz-share",
                "quiz-result",
                "quiz-ranking",
                "quiz-hint",
                "profile-lobby",
                "profile-hints",
            ],
        )

    def test_top5_scenes_follow_the_quiz_and_use_tenant_independent_screens(self):
        for locale, store_locale in (("pt", "pt-BR"), ("en", "en-US")):
            data = manifest("f1", ("quiz", "top5"), locale)
            data["storeLocale"] = store_locale
            selected = engine.select_store_scenes(data)
            scene_ids = {scene["sceneId"] for scene in selected}
            top5_scenes = [scene for scene in selected if scene["gameId"] == "top5"]

            self.assertIn("top5-lobby", scene_ids)
            self.assertIn("top5-round", scene_ids)
            self.assertNotIn("top5-answers", scene_ids)
            self.assertEqual([scene["sceneId"] for scene in top5_scenes], ["top5-lobby", "top5-round"])
            self.assertEqual([scene["sceneId"] for scene in selected[-2:]], [
                "top5-lobby", "top5-round",
            ])
            self.assertEqual(sum(1 for scene in selected if scene["gameId"] == "top5"), 2)
            self.assertLessEqual(len(selected), engine.STORE_SCENE_LIMIT)

    def test_realmadrid_italian_and_russian_locales_have_store_mapping_and_slide_copy(self):
        cases = (("it", "it-IT", "domande"), ("ru", "ru-RU", "вопрос"))
        with tempfile.TemporaryDirectory() as seed_dir:
            with open(os.path.join(seed_dir, "realmadrid.json"), "w", encoding="utf-8") as fh:
                json.dump({"supportedLocales": ["it", "ru"]}, fh)
            with patch.object(engine, "ALEFLY_SEEDS", seed_dir):
                locales = engine.dump_locales("realmadrid")

        for locale, store_locale, translated_word in cases:
            self.assertEqual(locales[locale]["storeLocales"], [store_locale])
            self.assertTrue(locales[locale]["hasSlides"])
            data = manifest("realmadrid", ("quiz",), locale)
            data["storeLocale"] = store_locale
            scenes = engine.select_store_scenes(data)
            self.assertEqual(len(scenes), 8)
            question = next(scene for scene in scenes if scene["sceneId"] == "quiz-question")
            self.assertIn(translated_word, question["headline"].lower())

    def test_top5_captures_resolve_from_the_staged_store_screenshot_folder(self):
        selected = engine.select_store_scenes(manifest("f1", ("quiz", "top5"), "pt"))
        with tempfile.TemporaryDirectory() as temp_dir:
            standard_dir = os.path.join(temp_dir, "f1", "android", "screenshots", "pt")
            os.makedirs(standard_dir)
            for scene in selected:
                open(os.path.join(standard_dir, scene["sourceFile"]), "wb").close()

            with patch.object(engine, "ALEFLY_RAW_CAPTURES", temp_dir):
                paths = engine.validate_scene_captures(
                    selected, standard_dir, tenant="f1", locale="pt"
                )

        self.assertEqual([os.path.basename(path) for path in paths if "top5" in path], [
            "11-top5-lobby.png", "12-top5-round.png",
        ])

    def test_profile_selection_depends_on_game_ids_not_tenant_name(self):
        selected = engine.select_store_scenes(manifest("another-tenant"))

        self.assertEqual(selected[-2]["gameId"], "profile")
        self.assertEqual(selected[-1]["sourceFile"], "10-profile-hints.png")

    def test_game_list_headline_highlights_tenant_accent_for_multi_game_tenants(self):
        selected = engine.select_store_scenes(manifest())
        scene = next(scene for scene in selected if scene["sceneId"] == "game-list")

        self.assertEqual(scene["headline"], "Escolha seu **próximo jogo**")

    def test_bible_scene_headlines_mark_key_phrases_for_brand_emphasis(self):
        for scene in engine.select_store_scenes(manifest()):
            with self.subTest(scene=scene["sceneId"]):
                self.assertRegex(scene["headline"], r"\*\*[^*]+\*\*")

    def test_single_game_home_copy_adapts_to_active_game_and_highlights_it(self):
        selected = engine.select_store_scenes(manifest("botafogo", ("quiz",)))
        scene = next(scene for scene in selected if scene["sceneId"] == "game-list")

        self.assertEqual(scene["headline"], "Jogue o **quiz**")
        self.assertNotIn("próximo jogo", scene["headline"])

    def test_game_list_copy_stays_localized_outside_portuguese(self):
        catalog = [
            {"sceneId": "game-list", "gameId": None, "sourceFile": "01-home.png", "priority": 10,
             "copy": {"en": {"headline": "Choose your **next game**", "subheadline": "Pick a challenge."}}},
            {"sceneId": "quiz-question", "gameId": "quiz", "sourceFile": "02-question.png", "priority": 20,
             "copy": {"en": {"headline": "Try the quiz", "subheadline": "Answer a question."}}},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "store-scenes.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(catalog, fh)
            with patch.object(engine, "STORE_SCENES_PATH", path):
                selected = engine.select_store_scenes(manifest(games=("quiz",), locale="en"))

        scene = next(scene for scene in selected if scene["sceneId"] == "game-list")
        self.assertEqual(scene["headline"], "Choose your **next game**")

    def test_scene_order_is_priority_based_not_capture_file_order(self):
        selected = engine.select_store_scenes(manifest())

        self.assertEqual([scene["priority"] for scene in selected], sorted(
            scene["priority"] for scene in selected
        ))
        self.assertNotEqual(selected[0]["sourceFile"], "01-answer-feedback.png")

        with tempfile.TemporaryDirectory() as temp_dir:
            for scene in reversed(selected):
                open(os.path.join(temp_dir, scene["sourceFile"]), "wb").close()
            paths = engine.validate_scene_captures(selected, temp_dir)
            self.assertEqual([os.path.basename(path) for path in paths], [
                scene["sourceFile"] for scene in selected
            ])

    def test_profile_round_copy_uses_hints_and_next_hint_action(self):
        selected = engine.select_store_scenes(manifest())
        round_scene = next(scene for scene in selected if scene["sceneId"] == "profile-hints")

        self.assertEqual(round_scene["headline"], "Revele **pistas** e encontre a resposta")
        self.assertIn("pistas", round_scene["subheadline"])
        self.assertEqual(round_scene["action"], "Revelar próxima dica")
        self.assertNotIn("profile-answer", [scene["sceneId"] for scene in selected])
        self.assertNotIn("profile-result", [scene["sceneId"] for scene in selected])

    def test_profile_only_manifest_selects_only_profile_game_scenes(self):
        selected = engine.select_store_scenes(manifest("other", ("profile",)))

        self.assertLessEqual(len(selected), 8)
        self.assertEqual({scene["gameId"] for scene in selected}, {None, "profile"})

    def test_manifest_tenant_and_content_locale_must_match_renderer_arguments(self):
        with self.assertRaisesRegex(ValueError, "tenantId"):
            engine.select_store_scenes(manifest("bible"), tenant="flamengo")
        with self.assertRaisesRegex(ValueError, "contentLocale"):
            engine.select_store_scenes(manifest(locale="pt"), locale="es")

    def test_manifest_must_be_a_json_object(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            engine.select_store_scenes([])

    def test_missing_localized_scene_fails_selection(self):
        with self.assertRaisesRegex(ValueError, "localized copy"):
            engine.select_store_scenes(manifest(locale="es"))

    def test_missing_required_capture_fails_before_output_directory_is_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            selected = engine.select_store_scenes(manifest())
            raw_capture_root = os.path.join(temp_dir, "raw")
            captures = os.path.join(raw_capture_root, "bible", "android", "screenshots", "pt")
            os.makedirs(captures)
            for scene in selected[:-1]:
                open(os.path.join(captures, scene["sourceFile"]), "wb").close()
            output_root = os.path.join(temp_dir, "store-assets")
            output = os.path.join(output_root, "bible", "pt-BR", "screenshots", "android")
            os.makedirs(output)
            with open(os.path.join(output, "slide_9.png"), "wb") as fh:
                fh.write(b"stale")
            with patch.object(engine, "ALEFLY_RAW_CAPTURES", raw_capture_root), \
                    patch.object(engine, "ALEFLY_STORE_ASSETS", output_root), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaises(SystemExit):
                engine.run_factory(
                    target_tenant="bible", target_platform="android", target_locale="pt",
                    manifest_data=manifest(),
                )
            self.assertTrue(os.path.exists(os.path.join(output, "slide_9.png")))

    def test_successful_profile_render_removes_only_stale_numbered_slides(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_manifest = manifest("bible", ("profile",))
            selected = engine.select_store_scenes(profile_manifest)
            raw_capture_root = os.path.join(temp_dir, "raw")
            captures = os.path.join(raw_capture_root, "bible", "android", "screenshots", "pt")
            os.makedirs(captures)
            for scene in selected:
                open(os.path.join(captures, scene["sourceFile"]), "wb").close()
            output_root = os.path.join(temp_dir, "store-assets")
            output = os.path.join(output_root, "bible", "pt-BR", "screenshots", "android")
            os.makedirs(output)
            for name in ("slide_1.png", "slide_5.png", "slide_8.png", "slide_9.png", "slide_notes.png"):
                with open(os.path.join(output, name), "wb") as fh:
                    fh.write(b"old")
            raw_output = os.path.join(output, "raw")
            os.makedirs(raw_output)
            with open(os.path.join(raw_output, "legacy-capture.png"), "wb") as fh:
                fh.write(b"keep")
            calls = []

            def render(*args, **kwargs):
                calls.append(kwargs)
                with open(args[5], "wb") as fh:
                    fh.write(b"rendered")

            with patch.object(engine, "ALEFLY_RAW_CAPTURES", raw_capture_root), \
                    patch.object(engine, "ALEFLY_STORE_ASSETS", output_root), \
                    patch.object(engine, "process_screenshot", side_effect=render), \
                    contextlib.redirect_stdout(io.StringIO()):
                engine.run_factory(
                    target_tenant="bible", target_platform="android", target_locale="pt",
                    manifest_data=profile_manifest,
                )

            self.assertEqual(len(calls), len(selected))
            self.assertIn("Revelar próxima dica", [call.get("action") for call in calls])
            self.assertTrue(os.path.exists(os.path.join(output, "slide_4.png")))
            self.assertFalse(os.path.exists(os.path.join(output, "slide_5.png")))
            self.assertFalse(os.path.exists(os.path.join(output, "slide_8.png")))
            self.assertFalse(os.path.exists(os.path.join(output, "slide_9.png")))
            self.assertTrue(os.path.exists(os.path.join(output, "slide_notes.png")))
            self.assertTrue(os.path.exists(os.path.join(raw_output, "legacy-capture.png")))

    def test_action_is_included_in_the_text_block_drawn_by_renderer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = os.path.join(temp_dir, "capture.png")
            output = os.path.join(temp_dir, "slide.png")
            Image.new("RGB", (120, 180), "white").save(source)
            profile_round = next(
                scene for scene in engine.select_store_scenes(manifest())
                if scene["sceneId"] == "profile-hints"
            )
            with patch.object(engine, "draw_text_block", wraps=engine.draw_text_block) as draw:
                engine.process_screenshot(
                    "bible", 0, profile_round["headline"], profile_round["subheadline"],
                    source, output, platform="android", action=profile_round["action"],
                )

            text_lines = draw.call_args.args[1].s_lines
            rendered_copy = " ".join(text_lines).replace("**", "")
            self.assertIn("Revelar próxima dica", rendered_copy)


if __name__ == "__main__":
    unittest.main()
