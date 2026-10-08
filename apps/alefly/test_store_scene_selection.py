import contextlib
import io
import os
import tempfile
import unittest
from unittest.mock import patch

import engine


def manifest(tenant="bible", games=("quiz", "profile"), locale="pt"):
    return {
        "tenantId": tenant,
        "storeLocale": "pt-BR",
        "contentLocale": locale,
        "activeGameIds": list(games),
        "games": {},
    }


class StoreSceneSelectionTest(unittest.TestCase):
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

    def test_profile_selection_depends_on_game_ids_not_tenant_name(self):
        selected = engine.select_store_scenes(manifest("another-tenant"))

        self.assertEqual(selected[-2]["gameId"], "profile")
        self.assertEqual(selected[-1]["sourceFile"], "10-profile-hints.png")

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

    def test_profile_round_copy_uses_four_hints_and_next_hint_action(self):
        selected = engine.select_store_scenes(manifest())
        round_scene = next(scene for scene in selected if scene["sceneId"] == "profile-hints")

        self.assertEqual(round_scene["headline"], "Revele pistas e encontre a resposta")
        self.assertIn("4 pistas", round_scene["subheadline"])
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
            captures = os.path.join(temp_dir, "captures")
            os.makedirs(captures)
            selected = engine.select_store_scenes(manifest())
            for scene in selected[:-1]:
                open(os.path.join(captures, scene["sourceFile"]), "wb").close()
            raw_capture_root = os.path.join(temp_dir, "raw")
            os.makedirs(os.path.join(raw_capture_root, "bible", "android", "screenshots", "pt"))
            output_root = os.path.join(temp_dir, "store-assets")
            output = os.path.join(output_root, "bible", "pt-BR", "screenshots", "android")
            with patch.object(engine, "ALEFLY_RAW_CAPTURES", raw_capture_root), \
                    patch.object(engine, "ALEFLY_STORE_ASSETS", output_root), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaises(SystemExit):
                engine.run_factory(
                    target_tenant="bible", target_platform="android", target_locale="pt",
                    manifest_data=manifest(),
                )
            self.assertFalse(os.path.exists(output))


if __name__ == "__main__":
    unittest.main()
