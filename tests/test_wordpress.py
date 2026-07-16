import os
import unittest
from unittest.mock import Mock, patch

import requests

from app.wordpress import WordPressConnectionError, test_wordpress_connection


class WordPressConnectionTest(unittest.TestCase):
    @staticmethod
    def response(
        status_code=200,
        payload=None,
        *,
        content_type="application/json",
        url="https://example.com/wp-json/wp/v2/users/me?context=edit",
        history=None,
        server="nginx",
    ):
        response = Mock()
        response.status_code = status_code
        response.headers = {
            "content-type": content_type,
            "server": server,
        }
        response.url = url
        response.history = history or []
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        return response

    def test_connection_succeeds_with_edit_posts_permission(self):
        response = self.response(
            payload={
                "name": "編集者",
                "username": "editor",
                "capabilities": {"edit_posts": True},
            }
        )

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
        self.assertIn("問題は見つかりませんでした", connection["cause"])
        self.assertEqual(connection["details"]["HTTPステータス"], "200")
        self.assertEqual(connection["details"]["応答形式"], "application/json")
        self.assertEqual(connection["details"]["WP_USERNAME"], "設定済み")
        self.assertEqual(connection["details"]["パスワード内の空白"], "あり")
        self.assertEqual(connection["details"]["値に含まれる引用符"], "なし")
        request.assert_called_once()
        self.assertEqual(
            request.call_args.args[0],
            "https://example.com/wp-json/wp/v2/users/me",
        )
        self.assertEqual(request.call_args.kwargs["params"], {"context": "edit"})

    def test_connection_rejects_invalid_credentials(self):
        response = self.response(
            status_code=401,
            payload={
                "code": "rest_cannot_view",
                "message": "Sorry, you are not allowed.",
            },
        )

        environment = {
            "WP_USERNAME": "editor",
            "WP_APP_PASSWORD": "wrong password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaises(WordPressConnectionError) as raised:
                    test_wordpress_connection("https://example.com")

        self.assertIn("認証に失敗しました", str(raised.exception))
        self.assertIn("Authorizationヘッダー", raised.exception.cause)
        self.assertIn(
            "WordPressエラーコード: rest_cannot_view",
            raised.exception.evidence,
        )
        self.assertEqual(raised.exception.details["HTTPステータス"], "401")

    def test_connection_requires_draft_permission(self):
        response = self.response(
            payload={
                "name": "購読者",
                "username": "subscriber",
                "capabilities": {"read": True},
            }
        )

        environment = {
            "WP_USERNAME": "subscriber",
            "WP_APP_PASSWORD": "application password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaises(WordPressConnectionError) as raised:
                    test_wordpress_connection("https://example.com")

        self.assertIn("下書きを作成する権限がありません", str(raised.exception))
        self.assertEqual(
            raised.exception.cause,
            "認証ユーザーのedit_posts権限が無効です。",
        )
        self.assertIn("edit_posts: false", raised.exception.evidence)

    def test_connection_reports_missing_rest_api(self):
        response = self.response(
            status_code=404,
            payload={
                "code": "rest_no_route",
                "message": "No route was found.",
            },
        )

        environment = {
            "WP_USERNAME": "editor",
            "WP_APP_PASSWORD": "application password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaises(WordPressConnectionError) as raised:
                    test_wordpress_connection("https://example.com")

        self.assertIn("REST APIが見つかりません", str(raised.exception))
        self.assertIn("WordPressエラーコード: rest_no_route", raised.exception.evidence)

    def test_connection_identifies_html_403_as_waf_or_ip_restriction(self):
        response = self.response(
            status_code=403,
            payload=None,
            content_type="text/html",
            server="cloudflare",
        )
        response.json.side_effect = requests.JSONDecodeError("invalid", "", 0)

        environment = {
            "WP_USERNAME": "editor",
            "WP_APP_PASSWORD": "application password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaises(WordPressConnectionError) as raised:
                    test_wordpress_connection("https://example.com")

        self.assertIn("アクセスが拒否されました", str(raised.exception))
        self.assertIn("WAF", raised.exception.cause)
        self.assertIn("IP制限", raised.exception.cause)
        self.assertEqual(raised.exception.details["応答サーバー"], "cloudflare")

    def test_connection_identifies_login_redirect(self):
        redirect = Mock()
        redirect.headers = {"location": "https://example.com/wp-login.php"}
        response = self.response(
            payload=None,
            content_type="text/html",
            url="https://example.com/wp-login.php",
            history=[redirect],
        )
        response.json.side_effect = requests.JSONDecodeError("invalid", "", 0)

        environment = {
            "WP_USERNAME": "editor",
            "WP_APP_PASSWORD": "application password",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch("app.wordpress.requests.get", return_value=response):
                with self.assertRaises(WordPressConnectionError) as raised:
                    test_wordpress_connection("https://example.com")

        self.assertIn("ログイン画面へ転送", str(raised.exception))
        self.assertIn("REST APIを遮断", raised.exception.cause)
        self.assertEqual(raised.exception.details["リダイレクト回数"], "1")

    def test_connection_requires_environment_credentials(self):
        environment = {
            "WP_USERNAME": "",
            "WP_APP_PASSWORD": "",
        }
        with patch.dict(os.environ, environment, clear=False):
            with self.assertRaises(WordPressConnectionError) as raised:
                test_wordpress_connection("https://example.com")

        self.assertIn("WP_USERNAMEまたはWP_APP_PASSWORD", str(raised.exception))
        self.assertIn("必要な認証情報", raised.exception.cause)


if __name__ == "__main__":
    unittest.main()
