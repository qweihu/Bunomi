import unittest

from bunomi.core import ReadingToken, SudachiEngine, annotate_text, detect_language, validate_annotation
from bunomi.engine import ReadingToken as PublicReadingToken, create_engine
from japanese_language_core.reading import ReadingToken as SharedReadingToken


class FakeEngine:
    def tokens(self, text):
        yield ReadingToken("食べる", "たべる", "taberu")
        yield ReadingToken("と", "と", "to")
        yield ReadingToken("日本語", "にほんご", "nihongo")


class MixedEngine:
    def tokens(self, text):
        yield ReadingToken("Hello ")
        yield ReadingToken("日本語", "にほんご", "nihongo")
        yield ReadingToken("です")


class CoreTests(unittest.TestCase):
    def test_public_shared_engine_boundary_preserves_source(self):
        engine = create_engine("sudachi")
        tokens = tuple(engine.tokens("雨が降り止む"))
        self.assertTrue(all(isinstance(token, PublicReadingToken) for token in tokens))
        self.assertTrue(all(isinstance(token, SharedReadingToken) for token in tokens))
        self.assertEqual("".join(token.orig for token in tokens), "雨が降り止む")

    def test_detects_japanese(self):
        result = detect_language("これは日本語です。")
        self.assertEqual(result.label, "ja")
        self.assertGreater(result.score, 0.9)

    def test_rejects_cjk_only_as_ambiguous(self):
        self.assertEqual(detect_language("日本語").label, "ambiguous")
        self.assertEqual(detect_language("hello").label, "non-ja")

    def test_keeps_okurigana_outside_ruby(self):
        result = annotate_text("食べると日本語", engine=FakeEngine())
        self.assertEqual(
            result.annotated,
            "<ruby>食<rt>た</rt></ruby>べると<ruby>日本語<rt>にほんご</rt></ruby>",
        )
        self.assertTrue(result.validation.ok)

    def test_keeps_repeated_okurigana_outside_ruby(self):
        class SingingEngine:
            def tokens(self, text):
                yield ReadingToken("歌う", "うたう", "utau")

        result = annotate_text("歌う", engine=SingingEngine())
        self.assertEqual(result.annotated, "<ruby>歌<rt>うた</rt></ruby>う")

    def test_romaji_wraps_japanese_surface(self):
        result = annotate_text("食べると日本語", mode="romaji", engine=FakeEngine())
        self.assertEqual(
            result.annotated,
            "<ruby>食べる<rt>taberu</rt></ruby><ruby>と<rt>to</rt></ruby><ruby>日本語<rt>nihongo</rt></ruby>",
        )

    def test_mixed_text_is_preserved(self):
        result = annotate_text("Hello 日本語です", engine=MixedEngine())
        self.assertEqual(result.detection.label, "mixed")
        self.assertEqual(result.annotated, "Hello <ruby>日本語<rt>にほんご</rt></ruby>です")
        self.assertTrue(result.warnings)

    def test_validation_detects_unannotated_kanji(self):
        result = validate_annotation("日本語です", "日本語です")
        self.assertFalse(result.ok)
        self.assertEqual(result.unannotated_kanji, "日本語")

    def test_sudachi_handles_contextual_compound(self):
        result = annotate_text("雨が降り止むまでは帰れない", engine=SudachiEngine())
        self.assertEqual(
            result.annotated,
            "<ruby>雨<rt>あめ</rt></ruby>が<ruby>降<rt>ふ</rt></ruby>り<ruby>止<rt>や</rt></ruby>むまでは<ruby>帰<rt>かえ</rt></ruby>れない",
        )

    def test_audited_override_is_reported(self):
        result = annotate_text("降り止む")
        self.assertIn("context-furiyamu", result.overrides_applied)
        self.assertIn("<ruby>降<rt>ふ</rt></ruby>", result.annotated)


if __name__ == "__main__":
    unittest.main()
