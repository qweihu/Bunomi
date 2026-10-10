import io
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

    def test_only_user_facing_formats_are_available(self):
        with self.assertRaises(SystemExit):
            self.invoke(["日本語を読む", "--format", "json"])
        with self.assertRaises(SystemExit):
            self.invoke(["日本語を読む", "--engine", "sudachi"])

    def test_file_input_writes_timestamped_sibling_html(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "lesson.txt"
            source.write_text("日本語を読む", encoding="utf-8")
            status, _, stderr = self.invoke(["--file", str(source)])
            self.assertEqual(status, 0)
            outputs = [path for path in Path(directory).iterdir() if path != source]
            self.assertEqual(len(outputs), 1)
            target = outputs[0]
            self.assertRegex(target.name, r"^lesson\.\d{8}-\d{6}(?:-\d+)?\.html$")
            self.assertIn("<!doctype html>", target.read_text(encoding="utf-8"))
            self.assertEqual(source.read_text(encoding="utf-8"), "日本語を読む")
            self.assertIn(str(target), stderr)

    def test_input_sources_cannot_be_combined(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write("日本語")
            handle.flush()
            status, _, stderr = self.invoke(["日本語", "--file", handle.name])
        self.assertEqual(status, 2)
        self.assertIn("不能同时使用", stderr)

    def test_cjk_only_text_requires_confirmation_then_warns(self):
        status, _, stderr = self.invoke(["日本語"])
        self.assertEqual(status, 2)
        self.assertIn("日语信号不足", stderr)

        status, result, stderr = self.invoke(["--assume-japanese", "日本語"])
        self.assertEqual(status, 0)
        self.assertIn("<ruby>日本語<rt>にほんご</rt></ruby>", result)
        self.assertIn("已绕过日语检测", stderr)


if __name__ == "__main__":
    unittest.main()
