"""Scenes handed over by the store screenshot plan (manifest "scenes") and the F1 French store locale."""
import unittest

import engine

HOME = {"sceneId": "game-list"}


def custom(scene_id="quiz-question", source="slide-2.png", headline="Você **reconhece** esse piloto?", sub="Pelas imagens."):
    return {"sceneId": scene_id, "sourceFile": source, "headline": headline, "subheadline": sub}


def manifest(scenes, locale="pt"):
    return {"tenantId": "f1", "storeLocale": "pt-BR", "contentLocale": locale, "activeGameIds": ["quiz"], "scenes": scenes}


class PlanScenesTest(unittest.TestCase):
    def select(self, scenes, locale="pt"):
        return engine.select_store_scenes(manifest(scenes, locale), tenant="f1", locale=locale)

    def test_custom_scenes_come_back_in_plan_order_with_their_own_text_and_capture(self):
        out = self.select([HOME, custom(), custom("plan-slide-3", "slide-3.png", "Capacete", "Lendário")])
        self.assertEqual([s["sceneId"] for s in out], ["game-list", "quiz-question", "plan-slide-3"])
        self.assertEqual(out[1]["headline"], "Você **reconhece** esse piloto?")
        self.assertEqual(out[1]["subheadline"], "Pelas imagens.")
        self.assertEqual(out[2]["sourceFile"], "slide-3.png")

    def test_a_catalog_scene_reference_takes_its_capture_and_localized_copy_from_the_catalog(self):
        home = self.select([HOME, custom()])[0]
        self.assertEqual(home["sourceFile"], "01-home.png")
        self.assertTrue(home["headline"])

    def test_a_catalog_scene_without_catalog_copy_in_the_locale_uses_the_tenants_positional_caption(self):
        """es/de/fr home, result and share: the catalog only carries pt/en/it/ru; the tenant slide list covers the rest."""
        for locale in ("es", "de", "fr"):
            with self.subTest(locale=locale):
                home = self.select([HOME, custom()], locale)[0]
                expected = engine.TENANT_CONFIGS["f1"]["slides_by_locale"][locale][0]
                self.assertEqual((home["headline"], home["subheadline"]), expected)

    def test_the_plan_order_is_kept_not_the_catalog_priority(self):
        out = self.select([custom(), HOME])
        self.assertEqual([s["sceneId"] for s in out], ["quiz-question", "game-list"])

    def test_more_scenes_than_the_store_allows_is_rejected(self):
        scenes = [custom(f"s{i}", f"slide-{i}.png") for i in range(1, engine.STORE_SCENE_LIMIT + 2)]
        with self.assertRaisesRegex(ValueError, "at most"):
            self.select(scenes)

    def test_duplicate_scene_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.select([custom(), custom()])

    def test_empty_headline_or_subheadline_is_rejected(self):
        for bad in (custom(headline=""), custom(sub="  ")):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "headline|subheadline"):
                self.select([bad])

    def test_a_capture_name_cannot_leave_the_capture_folder(self):
        for source in ("../x.png", "a/b.png", "slide-2.jpg", "", ".png/../x"):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "sourceFile"):
                self.select([custom(source=source)])

    def test_an_unknown_catalog_scene_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown scene"):
            self.select([{"sceneId": "does-not-exist"}])

    def test_a_catalog_scene_without_copy_in_the_locale_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "copy"):
            self.select([HOME, custom()], locale="xx")

    def test_scenes_must_be_a_non_empty_list(self):
        for bad in ([], "x", {"a": 1}):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "scenes"):
                self.select(bad)

    def test_manifest_scenes_switch_the_factory_to_the_scene_driven_path(self):
        self.assertTrue(engine.uses_scene_driven_path(manifest([custom()])))
        self.assertFalse(engine.uses_scene_driven_path({"activeGameIds": ["quiz"]}))
        self.assertTrue(engine.uses_scene_driven_path({"activeGameIds": ["quiz", "profile"]}))
        self.assertFalse(engine.uses_scene_driven_path(None))


if __name__ == "__main__":
    unittest.main()
