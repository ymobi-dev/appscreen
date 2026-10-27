import re
import unittest

import engine

# Words that would read as Brazilian Portuguese on a Portugal-first listing.
BRAZILIAN_WORDS = re.compile(r"\b(time|times|gol|gols|torcedor|torcedores|tela|celular|goleiro|equipe)\b", re.IGNORECASE)


class SportingCoverageTest(unittest.TestCase):
    def test_sporting_has_eight_portuguese_slides(self):
        slides = engine.TENANT_CONFIGS["sporting"]["slides_by_locale"]["pt"]
        self.assertEqual(8, len(slides))
        for headline, subheadline in slides:
            self.assertGreaterEqual(headline.count("**"), 2, headline)
            self.assertTrue(subheadline.strip())

    def test_sporting_copy_has_no_brazilianisms_or_official_claims(self):
        for headline, subheadline in engine.TENANT_CONFIGS["sporting"]["slides_by_locale"]["pt"]:
            text = f"{headline} {subheadline}"
            self.assertIsNone(BRAZILIAN_WORDS.search(text), text)
            self.assertNotIn("oficial", text.lower(), text)

    def test_sporting_store_locales_put_portugal_first(self):
        self.assertEqual(["pt-PT", "pt-BR"], engine.TENANT_STORE_LOCALE_OVERRIDES["sporting"]["pt"])


if __name__ == "__main__":
    unittest.main()
