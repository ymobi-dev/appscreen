import re
import unittest

import engine

# Words that would read as Brazilian Portuguese on a Portugal-first listing.
BRAZILIAN_WORDS = re.compile(r"\b(time|times|gol|gols|torcedor|torcedores|tela|celular|goleiro|equipe)\b", re.IGNORECASE)


PORTUGUESE_CLUBS = ("sporting", "benfica", "porto")


class PortugueseClubsCoverageTest(unittest.TestCase):
    def test_each_club_has_eight_portuguese_slides(self):
        for tenant in PORTUGUESE_CLUBS:
            slides = engine.TENANT_CONFIGS[tenant]["slides_by_locale"]["pt"]
            self.assertEqual(8, len(slides), tenant)
            for headline, subheadline in slides:
                self.assertGreaterEqual(headline.count("**"), 2, headline)
                self.assertTrue(subheadline.strip())

    def test_club_copy_has_no_brazilianisms_or_official_claims(self):
        for tenant in PORTUGUESE_CLUBS:
            for headline, subheadline in engine.TENANT_CONFIGS[tenant]["slides_by_locale"]["pt"]:
                text = f"{headline} {subheadline}"
                self.assertIsNone(BRAZILIAN_WORDS.search(text), f"{tenant}: {text}")
                self.assertNotIn("oficial", text.lower(), f"{tenant}: {text}")

    def test_store_locales_put_portugal_first(self):
        for tenant in PORTUGUESE_CLUBS:
            self.assertEqual(["pt-PT", "pt-BR"], engine.TENANT_STORE_LOCALE_OVERRIDES[tenant]["pt"], tenant)


if __name__ == "__main__":
    unittest.main()
