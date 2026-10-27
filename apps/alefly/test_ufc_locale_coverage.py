import json
import os
import unittest

import engine


class UfcLocaleCoverageTest(unittest.TestCase):
    def test_slides_cover_every_supported_locale(self):
        with open(os.path.join(engine.ALEFLY_SEEDS, "ufc.json"), encoding="utf-8") as seed_file:
            locales = json.load(seed_file)["supportedLocales"]

        slides_by_locale = engine.TENANT_CONFIGS["ufc"]["slides_by_locale"]
        self.assertEqual(set(slides_by_locale), set(locales))
        for locale in locales:
            with self.subTest(locale=locale):
                self.assertEqual(len(slides_by_locale[locale]), 8)

    def test_new_locales_use_their_google_play_locale_and_script(self):
        locale_data = engine.dump_locales("ufc")
        for locale, store_locale in (("my", "my-MM"), ("th", "th")):
            with self.subTest(locale=locale):
                self.assertEqual(locale_data[locale]["storeLocales"], [store_locale])
                self.assertTrue(locale_data[locale]["hasSlides"])

        for headline, subheadline in engine.TENANT_CONFIGS["ufc"]["slides_by_locale"]["my"]:
            with self.subTest(headline=headline):
                self.assertRegex(f"{headline} {subheadline}", r"[\u1000-\u109f]")
