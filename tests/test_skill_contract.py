from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_skill_declares_simple_default_workflow(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        prompt = (ROOT / "PROMPT.md").read_text(encoding="utf-8")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("self-contained HTML", skill)
        self.assertIn("Do not ask the user to choose", skill)
        self.assertIn("Markdown", prompt)
        self.assertIn("HTML", metadata)

    def test_skill_keeps_lyrics_out_of_scope(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("$utayomi", skill)
        self.assertIn("lyric-specific", skill)


if __name__ == "__main__":
    unittest.main()
