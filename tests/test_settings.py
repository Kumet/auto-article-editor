import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.default_template import DEFAULT_TEMPLATE
from app.settings import load_settings


class DefaultTemplateTest(unittest.TestCase):
    def test_uses_built_in_seo_aio_template_when_not_overridden(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.json"
            environment = {
                "APP_SETTINGS_PATH": str(settings_path),
                "DEFAULT_ARTICLE_TEMPLATE": "",
                "WP_URL": "",
            }

            with patch.dict(os.environ, environment, clear=False):
                settings = load_settings()

        self.assertEqual(settings["default_template"], DEFAULT_TEMPLATE)
        self.assertIn("【SEO・AIOの基本ルール】", settings["default_template"])
        self.assertIn("<h2>よくある質問</h2>", settings["default_template"])
        self.assertIn("WordPress本文へ保存できるHTML断片", settings["default_template"])
        self.assertIn(
            "記事内容を具体的に表す自然な日本語の見出しへ必ず変更",
            settings["default_template"],
        )
        self.assertNotIn("<h2>テーマの結論</h2>", settings["default_template"])
        self.assertNotIn("<h2>テーマの基本情報</h2>", settings["default_template"])
        self.assertNotIn("<h3>項目名</h3>", settings["default_template"])
        self.assertNotIn("<h3>質問文</h3>", settings["default_template"])

    def test_environment_template_still_takes_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.json"
            environment = {
                "APP_SETTINGS_PATH": str(settings_path),
                "DEFAULT_ARTICLE_TEMPLATE": "環境変数の記事テンプレート",
                "WP_URL": "",
            }

            with patch.dict(os.environ, environment, clear=False):
                settings = load_settings()

        self.assertEqual(
            settings["default_template"],
            "環境変数の記事テンプレート",
        )


if __name__ == "__main__":
    unittest.main()
