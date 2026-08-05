import json
from pathlib import Path
import tempfile
import unittest

from bunomi.core import ReadingToken, annotate_text
from bunomi.yomitan import load_yomitan_dictionary


class FakeEngine:
    def tokens(self, text):
        yield ReadingToken("日本語", "にほんご", "nihongo")


class YomitanTests(unittest.TestCase):
    def test_loads_term_bank_and_audits_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "extracted"
            (root / "JMdict").mkdir(parents=True)
            (root / "JMdict" / "index.json").write_text(
                json.dumps({"title": "JMdict test", "format": 3}),
                encoding="utf-8",
            )
            (root / "JMdict" / "term_bank_1.json").write_text(
                json.dumps(
                    [
                        ["日本語", "にほんご", "", "", 0, ["にっぽんご"]],
                        ["生ビール", "なまビール", "n", "", 0, ["draft beer"]],
                    ]
                ),
                encoding="utf-8",
            )
            dictionary = load_yomitan_dictionary(root)
            self.assertEqual(2, dictionary.term_count)
            audit = dictionary.audit("生ビール", "なまびーる")
            self.assertIsNotNone(audit)
            self.assertTrue(audit.exact_reading_match)
            self.assertEqual("match", audit.as_dict()["reading_status"])
            result = annotate_text(
                "日本語",
                engine=FakeEngine(),
                dictionary=dictionary,
                force=True,
            )
            self.assertEqual(1, len(result.dictionary_matches))
            self.assertEqual(("JMdict test",), result.dictionary_sources)
            self.assertEqual(2, result.dictionary_term_count)

    def test_loads_kanjidic_character_bank(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "extracted"
            (root / "KANJIDIC").mkdir(parents=True)
            (root / "KANJIDIC" / "index.json").write_text(
                json.dumps({"title": "KANJIDIC test", "format": 3}),
                encoding="utf-8",
            )
            (root / "KANJIDIC" / "kanji_bank_1.json").write_text(
                json.dumps(
                    [
                        [
                            "学",
                            "ガク",
                            "まな.ぶ",
                            "jouyou",
                            ["study", "learning"],
                            {"freq": "42", "strokes": "8", "grade": "1"},
                        ]
                    ]
                ),
                encoding="utf-8",
            )
            dictionary = load_yomitan_dictionary(root)
            self.assertEqual(0, dictionary.term_count)
            self.assertEqual(1, dictionary.kanji_count)
            kanji = dictionary.kanji_lookup("学")
            self.assertEqual(("ガク",), kanji[0].onyomi)
            self.assertEqual(("まな.ぶ",), kanji[0].kunyomi)
            self.assertEqual(42, kanji[0].frequency)
            self.assertEqual(8, kanji[0].stroke_count)

            class KanjiEngine:
                def tokens(self, text):
                    yield ReadingToken("学ぶ", "まなぶ", "manabu")

            result = annotate_text(
                "学ぶ",
                engine=KanjiEngine(),
                dictionary=dictionary,
            )
            self.assertEqual(1, result.dictionary_kanji_count)
            self.assertEqual("学", result.dictionary_kanji_matches[0]["character"])


if __name__ == "__main__":
    unittest.main()
