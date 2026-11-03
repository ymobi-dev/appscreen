import json
import os
import tempfile
import unittest
from unittest.mock import patch

import engine


class ManchesterCityRussianSlidesTest(unittest.TestCase):
    def test_ru_locale_resolves_to_ru_ru_and_has_eight_localized_slides(self):
        with tempfile.TemporaryDirectory() as seed_dir:
            with open(os.path.join(seed_dir, "manchestercity.json"), "w", encoding="utf-8") as fh:
                json.dump({"supportedLocales": ["ru"]}, fh)
            with patch.object(engine, "ALEFLY_SEEDS", seed_dir):
                locales = engine.dump_locales("manchestercity")

        self.assertEqual(locales["ru"]["storeLocales"], ["ru-RU"])
        self.assertTrue(locales["ru"]["hasSlides"])
        slides = engine.TENANT_CONFIGS["manchestercity"]["slides_by_locale"]["ru"]
        self.assertEqual(len(slides), 8)
        self.assertIn("Манчестер Сити", " ".join(headline for headline, _ in slides))


if __name__ == "__main__":
    unittest.main()
