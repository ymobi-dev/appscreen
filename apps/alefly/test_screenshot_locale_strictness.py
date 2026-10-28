import os
import tempfile
import unittest
from unittest.mock import patch

import engine
from PIL import Image


class ScreenshotLocaleStrictnessTest(unittest.TestCase):
    def test_myanmar_locale_uses_a_myanmar_typeface(self):
        fonts = engine.get_fonts(platform="android", locale="my")

        self.assertIn("Myanmar Sangam MN", fonts.headline.getname()[0])

    def test_asian_locales_keep_their_script_typefaces(self):
        for locale, family in (("ar", "Arial Unicode MS"), ("ko", "Apple SD Gothic Neo"), ("ja", "Hiragino"), ("th", "Thonburi"), ("zh", "Hiragino")):
            with self.subTest(locale=locale):
                fonts = engine.get_fonts(platform="android", locale=locale)
                self.assertIn(family, fonts.headline.getname()[0])

    def test_script_locales_fail_when_their_typeface_is_missing(self):
        with patch.object(engine.os.path, "exists", return_value=False):
            for locale in ("ar", "hi", "ja", "ko", "my", "th", "zh"):
                with self.subTest(locale=locale), self.assertRaisesRegex(FileNotFoundError, locale):
                    engine.get_fonts(platform="android", locale=locale)

    def test_thai_copy_wraps_without_whitespace_between_words(self):
        headline, subheadline = engine.TENANT_CONFIGS["ufc"]["slides_by_locale"]["th"][5]
        canvas = engine.Image.new("RGB", (engine.ANDROID_WIDTH, engine.ANDROID_HEIGHT))

        layout = engine.layout_text_block(canvas, headline, subheadline, platform="android", locale="th")

        self.assertLessEqual(len(layout.s_lines), engine.MAX_SUBHEAD_LINES)

    def test_requested_locale_does_not_use_another_locales_raw_screenshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_root = os.path.join(temp_dir, "raw-captures")
            output_root = os.path.join(temp_dir, "store-assets")
            portuguese = os.path.join(raw_root, "ufc", "android", "screenshots", "pt")
            os.makedirs(portuguese)
            for source in engine.SLIDE_SOURCES:
                Image.new("RGB", (360, 640), "white").save(
                    os.path.join(portuguese, source["file"])
                )

            with patch.object(engine, "ALEFLY_RAW_CAPTURES", raw_root), patch.object(
                engine, "ALEFLY_STORE_ASSETS", output_root
            ):
                with self.assertRaisesRegex(SystemExit, "1"):
                    engine.run_factory(
                        target_tenant="ufc",
                        target_platform="android",
                        target_locale="my",
                    )

            self.assertFalse(os.path.exists(os.path.join(output_root, "ufc", "my-MM")))


if __name__ == "__main__":
    unittest.main()
