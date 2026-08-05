import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest

from bunomi.cli import main


class CLITests(unittest.TestCase):
    def invoke(self, args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(args)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_output_formats(self):
        status, markdown, stderr = self.invoke(["日本語を読む"])
        self.assertEqual(status, 0)
        self.assertIn("<ruby>日本語<rt>にほんご</rt></ruby>", markdown)
        self.assertEqual(stderr, "")

        status, html, _ = self.invoke(["日本語を読む", "--format", "html"])
        self.assertEqual(status, 0)
        self.assertIn("<!doctype html>", html)
        self.assertIn('<main class="bunomi">', html)

        status, raw_json, _ = self.invoke(["日本語を読む", "--format", "json"])
        self.assertEqual(status, 0)
        payload = json.loads(raw_json)
        self.assertEqual(payload["language"]["label"], "ja")
        self.assertEqual(payload["ruby_count"], 2)

        status, raw_json, _ = self.invoke(["降り止む", "--engine", "sudachi", "--format", "json"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(raw_json)["engine"], "sudachi")

        status, raw_json, _ = self.invoke(["日本語", "--force", "--engine", "pykakasi", "--format", "json"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(raw_json)["engine"], "pykakasi")

    def test_json_contains_token_metadata(self):
        status, raw_json, _ = self.invoke(
            ["降り止む", "--engine", "sudachi", "--format", "json"]
        )
        self.assertEqual(status, 0)
        payload = json.loads(raw_json)
        tokens = payload["tokens"]
        self.assertTrue(tokens)
        for token in tokens:
            self.assertIn("part_of_speech", token)
            self.assertIn("dictionary_form", token)
            self.assertIn("normalized_form", token)

    def test_json_conjugations(self):
        status, raw_json, _ = self.invoke(
            ["食べる", "--engine", "sudachi", "--format", "json", "--conjugations"]
        )
        self.assertEqual(status, 0)
        payload = json.loads(raw_json)
        forms = [
            token.get("conjugations")
            for token in payload["tokens"]
            if token.get("dictionary_form")
        ]
        self.assertTrue(any("polite" in item for item in forms if item))

    def test_json_examples(self):
        with tempfile.TemporaryDirectory() as directory:
            sentences = Path(directory) / "sentences.tsv"
            links = Path(directory) / "links.tsv"
            sentences.write_text(
                "1\tjpn\t日本語を勉強する。\n2\tcmn\t学习日语。\n",
                encoding="utf-8",
            )
            links.write_text("1\t2\n", encoding="utf-8")
            status, raw_json, _ = self.invoke(
                [
                    "日本語を勉強する。",
                    "--engine",
                    "sudachi",
                    "--format",
                    "json",
                    "--sentences",
                    str(sentences),
                    "--sentence-links",
                    str(links),
                ]
            )
            self.assertEqual(status, 0)
            payload = json.loads(raw_json)
            self.assertIn("examples", payload)
            self.assertIn("日本語", payload["examples"])
            example = payload["examples"]["日本語"][0]
            self.assertEqual("日本語を勉強する。", example["text"])
            self.assertEqual("学习日语。", example["translations"][0])

    def test_export_requires_explicit_parent_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "lesson.md"
            status, _, stderr = self.invoke(["日本語を読む", "--output", str(target)])
            self.assertEqual(status, 2)
            self.assertIn("输出目录不存在", stderr)
            self.assertFalse(target.exists())

            status, _, stderr = self.invoke(
                ["日本語を読む", "--output", str(target), "--create-parent"]
            )
            self.assertEqual(status, 0)
            self.assertTrue(target.exists())
            self.assertIn(str(target), stderr)

            status, _, stderr = self.invoke(["日本語を読む", "--output", str(target)])
            self.assertEqual(status, 2)
            self.assertIn("输出文件已存在", stderr)

    def test_input_sources_cannot_be_combined(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write("日本語")
            handle.flush()
            status, _, stderr = self.invoke(["日本語", "--file", handle.name])
        self.assertEqual(status, 2)
        self.assertIn("不能同时使用", stderr)


if __name__ == "__main__":
    unittest.main()
