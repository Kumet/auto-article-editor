import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class ClipboardUiTest(unittest.TestCase):
    def setUp(self):
        self.environment = {
            "APP_USERNAME": "",
            "APP_PASSWORD": "",
            "RENDER": "",
        }

    def test_preview_uses_copy_actions_instead_of_wordpress_save(self):
        with patch.dict(os.environ, self.environment, clear=False):
            client = TestClient(app)
            with patch(
                "app.main.extract_article",
                return_value={"title": "生成タイトル", "content": "元記事"},
            ):
                with patch(
                    "app.main.rewrite_article",
                    return_value="<h2>見出し</h2><p>生成本文</p>",
                ):
                    response = client.post(
                        "/generate",
                        data={
                            "url": "https://example.com/article",
                            "template": "記事の型",
                        },
                    )

        self.assertEqual(response.status_code, 200)
        self.assertIn("タイトルをコピー", response.text)
        self.assertIn("記事本文をコピー", response.text)
        self.assertIn('data-copy-target="#article-preview"', response.text)
        self.assertIn('id="copy-status"', response.text)
        self.assertNotIn('hx-post="/save"', response.text)
        self.assertNotIn("WordPressへ下書き保存", response.text)

    def test_settings_page_does_not_request_wordpress_credentials(self):
        with patch.dict(os.environ, self.environment, clear=False):
            response = TestClient(app).get("/settings")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("WordPress URL", response.text)
        self.assertNotIn("接続テスト", response.text)
        self.assertIn("デフォルトの記事の型", response.text)

    def test_removed_save_and_connection_routes_are_not_available(self):
        with patch.dict(os.environ, self.environment, clear=False):
            client = TestClient(app)
            save_response = client.post("/save")
            connection_response = client.post("/settings/test-wordpress")

        self.assertEqual(save_response.status_code, 404)
        self.assertEqual(connection_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
