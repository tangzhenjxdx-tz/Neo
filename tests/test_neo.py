import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neo.cli import main  # noqa: E402
from neo.rules import ERROR, WARN, check_text  # noqa: E402
from neo.scaffold import render  # noqa: E402


def codes(text):
    return [finding.code for finding in check_text(text)]


def build(**kwargs):
    options = {"slug": "demo-bot", "name": "演示", "job": "把一件事做完。"}
    options.update(kwargs)
    return render(**options)


class GoodExamples(unittest.TestCase):
    def test_every_example_is_clean(self):
        paths = sorted((ROOT / "examples" / "good").glob("*.md"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=path.name):
                errors = [f for f in check_text(path.read_text(encoding="utf-8")) if f.level == ERROR]
                self.assertEqual([], [f"{f.code} {f.message}" for f in errors])


class BadExamples(unittest.TestCase):
    expected = {
        "no-anti-jobs.md": "D002",
        "vague-done-test.md": "D005",
        "readonly-writes.md": "D006",
        "wrong-botmrr.md": "N003",
    }

    def test_each_bad_example_fails_for_one_reason(self):
        for name, code in self.expected.items():
            with self.subTest(name=name):
                found = check_text((ROOT / "examples" / "bad" / name).read_text(encoding="utf-8"))
                errors = [f.code for f in found if f.level == ERROR]
                self.assertEqual([code], errors)


class Scaffold(unittest.TestCase):
    def test_generated_bot_passes(self):
        self.assertEqual([], [f for f in check_text(build()) if f.level == ERROR])

    def test_generated_bot_with_cron_passes(self):
        text = build(cron="30 8 * * 1-5")
        self.assertEqual([], [f for f in check_text(text) if f.level == ERROR])
        self.assertIn("timeZone", text)

    def test_rejects_bad_slug(self):
        with self.assertRaises(ValueError):
            build(slug="Demo Bot")

    def test_rejects_bad_cron(self):
        with self.assertRaises(ValueError):
            build(cron="every morning")


class FormatRules(unittest.TestCase):
    def assert_code(self, text, code, level=ERROR):
        findings = check_text(text)
        self.assertIn(code, [f.code for f in findings if f.level == level], [f.code for f in findings])

    def test_no_frontmatter(self):
        self.assert_code("就是一段话", "N001")

    def test_invalid_yaml(self):
        self.assert_code("---\nbotmrr: [1\n---\n", "N002")

    def test_wrong_botmrr(self):
        self.assert_code(build().replace("botmrr: 1", "botmrr: 2"), "N003")

    def test_missing_field(self):
        self.assert_code(build().replace('license: "Apache-2.0"\n', ""), "N004")

    def test_bad_id(self):
        self.assert_code(build().replace('id: "demo-bot"', 'id: "Demo Bot"'), "N005")

    def test_bad_release(self):
        self.assert_code(build().replace('release: "0.1.0"', 'release: "v1"'), "N006")

    def test_long_name(self):
        self.assert_code(build(name="很" * 101), "N007")

    def test_missing_author(self):
        self.assert_code(build().replace('author:\n  name: "Neo"', "author: {}"), "N008")

    def test_empty_outcomes(self):
        self.assert_code(build().replace("outcomes:\n  - \"把一件事做完。\"", "outcomes: []"), "N009")

    def test_setup_minutes(self):
        self.assert_code(build().replace("setupMinutes: 5", "setupMinutes: 0"), "N010")

    def test_requirements_without_capabilities(self):
        self.assert_code(build().replace("  capabilities: []\n", ""), "N011")

    def test_bad_color(self):
        self.assert_code(build().replace("      color: teal", "      color: rainbow"), "N013")

    def test_soul_too_large(self):
        self.assert_code(build(job="做" * 24001), "N014")

    def test_bad_cron(self):
        text = build(cron="30 8 * * 1-5").replace('expression: "30 8 * * 1-5"', 'expression: "30 8"')
        self.assert_code(text, "N015")

    def test_missing_heading(self):
        self.assert_code(build().replace("## Team", "## Squad"), "N016")


class DesignRules(unittest.TestCase):
    def assert_code(self, text, code, level=ERROR):
        findings = check_text(text)
        self.assertIn(code, [f.code for f in findings if f.level == level], [f.code for f in findings])

    def test_missing_job_section(self):
        self.assert_code(build().replace("## 工作", "## 任务"), "D001")

    def test_missing_anti_jobs(self):
        self.assert_code(build().replace("## 绝不", "## 边界"), "D002")

    def test_one_anti_job_is_not_enough(self):
        text = build().replace(
            "      - 不接第二件事：超出上面这一句的请求，直接回「不在范围内」。\n"
            "      - 不替你做决定，只摆事实和选项。",
            "      - 不接第二件事。",
        )
        self.assert_code(text, "D003")

    def test_missing_done_test(self):
        self.assert_code(build().replace("## 完成标准", "## 收尾"), "D004")

    def test_vague_done_test(self):
        text = build().replace(
            "一条消息，不超过 5 行；没有内容时只回一句「今天没有」。发完就停。",
            "差不多就收，看情况。",
        )
        self.assert_code(text, "D005")

    def test_readonly_with_write_capability(self):
        text = build().replace("## 工作", "## 工作\n      只读。")
        text = text.replace("  capabilities: []", "  capabilities:\n    - 打标签")
        self.assert_code(text, "D006")

    def test_routine_breaks_anti_jobs(self):
        text = build(cron="30 8 * * 1-5").replace("## 工作", "## 工作\n      只读。")
        text = text.replace("      只做这一件事；做完发一条消息", "      回复每一条消息")
        self.assert_code(text, "D007")

    def test_too_many_routines(self):
        extra = ""
        for index, name in enumerate(("第二件", "第三件", "第四件"), start=2):
            extra += (
                f"  - key: task{index}\n"
                f"    name: {name}\n"
                "    agent: main\n"
                "    prompt: |\n"
                "      再来一次。\n"
                "    runOn: maus\n"
                '    schedule:\n      type: daily\n      time: "09:00"\n      weekdays: [1]\n'
                "    durationMinutes: 15\n"
                "    enabledAfterInstall: false\n"
            )
        text = build(cron="30 8 * * 1-5").replace(
            "    enabledAfterInstall: false\n---", "    enabledAfterInstall: false\n" + extra + "---"
        )
        self.assert_code(text, "D008", WARN)

    def test_missing_voice_is_a_warning(self):
        self.assert_code(build().replace("## 声音", "## 语气"), "D009", WARN)

    def test_no_soul_at_all(self):
        text = build()
        start = text.index("    soul: |")
        end = text.index("routines:", start) if "routines:" in text[start:] else text.index("\n---\n", start)
        self.assert_code(text[:start] + text[end:], "D010", WARN)


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        return subprocess.run(
            [sys.executable, "-m", "neo", *args],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

    def test_good_examples_exit_zero(self):
        result = self.run_cli("check", "examples/good")
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn("0 个没通过", result.stdout)

    def test_bad_examples_exit_one(self):
        result = self.run_cli("check", "examples/bad")
        self.assertEqual(1, result.returncode)
        self.assertIn("D002", result.stdout)

    def test_json_output(self):
        result = self.run_cli("check", "examples/bad", "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any(item["findings"] for item in payload))

    def test_new_then_check(self):
        target = ROOT / "tests" / "_tmp"
        result = self.run_cli("new", "tmp-bot", "--name", "临时", "--job", "只做一件小事。", "--out", str(target))
        try:
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertTrue((target / "tmp-bot.md").exists())
            check = self.run_cli("check", str(target / "tmp-bot.md"))
            self.assertEqual(0, check.returncode, check.stdout)
        finally:
            path = target / "tmp-bot.md"
            if path.exists():
                path.unlink()
            if target.exists():
                target.rmdir()

    def test_missing_path_fails(self):
        result = self.run_cli("check", "nope")
        self.assertNotEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main()
