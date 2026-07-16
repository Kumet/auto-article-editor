import os
import unittest
from unittest.mock import Mock, patch

from app.wordpress import WordPressConnectionError, test_wordpress_connection


class WordPressConnectionTest(unittest.TestCase):
    def test_connection_succeeds_with_edit_posts_permission(self):
        response = Mock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "name": "編集者",
            "username": "editor",
            "capabilities": {"edit_posts": True},
        }

        environment = {
            "WP_USERNAME": "editor",
            "WP_APP_PASSWORD": "application password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response) as request:
                connection = test_wordpress_connection("https://example.com/")

        self.assertEqual(connection["display_name"], "編集者")
        self.assertEqual(connection["username"], "editor")
        self.assertEqual(connection["site_url"], "https://example.com")
        request.assert_called_once()
        self.assertEqual(
            request.call_args.args[0],
            "https://example.com/wp-json/wp/v2/users/me",
        )
        self.assertEqual(request.call_args.kwargs["params"], {"context": "edit"})

    def test_connection_rejects_invalid_credentials(self):
        response = Mock()
        response.status_code = 401

        environment = {
            "WP_USERNAME": "editor",
            "WP_APP_PASSWORD": "wrong password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaisesRegex(
                    WordPressConnectionError,
                    "認証に失敗しました",
                ):
                    test_wordpress_connection("https://example.com")

    def test_connection_requires_draft_permission(self):
        response = Mock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "name": "購読者",
            "username": "subscriber",
            "capabilities": {"read": True},
        }

        environment = {
            "WP_USERNAME": "subscriber",
            "WP_APP_PASSWORD": "application password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaisesRegex(
                    WordPressConnectionError,
                    "下書きを作成する権限がありません",
                ):
                    test_wordpress_connection("https://example.com")

    def test_connection_reports_missing_rest_api(self):
        response = Mock()
        response.status_code = 404

        environment = {
            "WP_USERNAME": "editor",
            "WP_APP_PASSWORD": "application password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaisesRegex(
                    WordPressConnectionError,
                    "REST APIが見つかりません",
                ):
                    test_wordpress_connection("https://example.com")

    def test_connection_requires_environment_credentials(self):
        environment = {
            "WP_USERNAME": "",
            "WP_APP_PASSWORD": "",
        }
        with patch.dict(os.environ, environment, clear=False):
            with self.assertRaisesRegex(
                WordPressConnectionError,
                "WP_USERNAMEまたはWP_APP_PASSWORD",
            ):
                test_wordpress_connection("https://example.com")


if __name__ == "__main__":
    unittest.main()
